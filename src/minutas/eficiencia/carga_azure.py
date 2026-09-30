"""
Carga las eficiencias de máquinas desde la Minuta Excel a Azure SQL (RendimientoReal).

Flujo: parse nombre → parse eficiencias (Datos crudos) → DataFrame → insert en RendimientoReal.

Uso (desde la raíz del repo):
  python src/minutas/eficiencia/carga_azure.py [ruta_minuta.xlsx] [hoja]

Requisitos:
  - .env con AZURE_SQL_*
  - Tabla RendimientoReal (sql/create_tables_rendimiento.sql)
"""
import sys
from pathlib import Path
from datetime import datetime

_src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_src_dir))

from dotenv import load_dotenv
load_dotenv(_src_dir.parent / ".env")

import pandas as pd
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError, OperationalError

from config import AZURE_TABLA_RENDIMIENTO_REAL, AZURE_MINUTA_IF_EXISTS
from minutas.parse_minuta import parse_minuta_filename
from minutas.eficiencia.parser import parse_minuta_eficiencia, EficienciaRow
from db import build_engine, smoke_test, load_dataframe, load_dataframe_skip_duplicates
from run_summary import RunSummary


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _rows_to_dataframe(rows: list[EficienciaRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    data = [
        {
            "id_maquina": r.id_maquina,
            "Fecha": r.fecha,
            "Turno": r.turno,
            "Eficiencia": r.eficiencia,
            "Velocidad": r.velocidad,
            "Unidad": r.unidad,
            "RendimientoDeseado": r.rendimiento_deseado,
            "VelocidadDeseado": r.velocidad_deseado,
        }
        for r in rows
    ]
    df = pd.DataFrame(data)
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    return df


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent.parent
    if len(sys.argv) > 1:
        minuta_path = sys.argv[1]
    else:
        minutas_en_raiz = sorted(
            f for f in root.glob("*.xlsx")
            if "minuta" in f.name.lower() and not f.name.startswith("~$")
        )
        if not minutas_en_raiz:
            print("No hay archivo Minuta en la raíz.", file=sys.stderr)
            print("Uso: python src/minutas/eficiencia/carga_azure.py [ruta_minuta.xlsx] [hoja]", file=sys.stderr)
            return 1
        minuta_path = str(minutas_en_raiz[0])
        if len(minutas_en_raiz) > 1:
            print(f"Varias Minutas; se usa: {minutas_en_raiz[0].name}\n", file=sys.stderr)
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None

    title = Path(minuta_path).name if minuta_path else "Minuta (Eficiencias)"
    summary = RunSummary(title=title)
    _log("Inicio carga Eficiencias → RendimientoReal")
    _log(f"Archivo: {Path(minuta_path).name}")

    # Paso 1: Parse nombre
    _log("Paso 1: Leyendo nombre del archivo...")
    try:
        minuta_info = parse_minuta_filename(minuta_path)
        if minuta_info.errors:
            summary.add_step("Lectura del nombre", success=False, errors=minuta_info.errors, data={"archivo": minuta_path})
        else:
            summary.add_step("Lectura del nombre", success=True, data={"archivo": minuta_path, "Fecha": minuta_info.fecha, "Versión": minuta_info.version})
    except Exception as e:
        summary.add_step("Lectura del nombre", success=False, errors=[f"{type(e).__name__}: {e}"], data={"archivo": minuta_path})
        print(summary.to_text(), file=sys.stderr)
        return 1

    if not minuta_info.fecha:
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 1: OK")

    # Paso 2: Parse eficiencias
    _log("Paso 2: Procesando Excel (Datos crudos)...")
    try:
        if not Path(minuta_path).exists():
            raise FileNotFoundError(f"No se encontró: {minuta_path}")
        result = parse_minuta_eficiencia(minuta_path, minuta_info, sheet_name=sheet_name)
        n_eficiencias = len(result.filas)
        summary.add_step("Procesamiento de eficiencias", success=True, messages=[f"Filas a insertar: {n_eficiencias}"], data={"hoja": sheet_name or "Datos crudos"})
        if result.errors:
            for e in result.errors:
                summary.steps[-1].errors.append(e)
                summary.steps[-1].success = False
    except Exception as e:
        summary.add_step("Procesamiento de eficiencias", success=False, errors=[f"{type(e).__name__}: {e}"], data={"archivo": minuta_path})
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 2: OK")

    if n_eficiencias == 0:
        _log("No hay filas para insertar.")
        print(summary.to_text())
        return 0

    # Paso 3: Conexión Azure
    _log("Paso 3: Conectando a Azure SQL...")
    try:
        engine = build_engine()
        if not smoke_test(engine):
            raise RuntimeError("Conexión a Azure SQL falló.")
        summary.add_step("Conexión a Azure SQL", success=True, messages=["Conexión OK"])
    except Exception as e:
        summary.add_step("Conexión a Azure SQL", success=False, errors=[f"{type(e).__name__}: {e}"])
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 3: OK")

    # Paso 4: Insertar
    _log("Paso 4: Insertando RendimientoReal...")
    df = _rows_to_dataframe(result.filas)
    dtype_fecha = {"Fecha": Date()}
    try:
        n = load_dataframe(engine, df, AZURE_TABLA_RENDIMIENTO_REAL, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        summary.add_step(f"Inserción en {AZURE_TABLA_RENDIMIENTO_REAL}", success=True, messages=[f"Filas insertadas: {n}"], data={"tabla": AZURE_TABLA_RENDIMIENTO_REAL, "filas": n})
        _log("Paso 4: OK")
    except IntegrityError:
        _log("  Hay duplicados, insertando fila a fila...")
        inserted, skipped = load_dataframe_skip_duplicates(engine, df, AZURE_TABLA_RENDIMIENTO_REAL, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        summary.add_step(f"Inserción en {AZURE_TABLA_RENDIMIENTO_REAL}", success=True, messages=[f"Insertadas: {inserted}, omitidas: {skipped}"], data={"tabla": AZURE_TABLA_RENDIMIENTO_REAL, "filas": inserted})
        _log("Paso 4: OK")
    except OperationalError:
        _log("  Fallo de conexión, reintentando...")
        import time
        time.sleep(2)
        engine = build_engine()
        n = load_dataframe(engine, df, AZURE_TABLA_RENDIMIENTO_REAL, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        summary.add_step(f"Inserción en {AZURE_TABLA_RENDIMIENTO_REAL}", success=True, messages=[f"Filas insertadas: {n}"], data={"tabla": AZURE_TABLA_RENDIMIENTO_REAL, "filas": n})
        _log("Paso 4: OK")

    _log("Fin del run")
    print(summary.to_text())
    return 0 if summary.success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        import traceback
        print(f"Error inesperado: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
