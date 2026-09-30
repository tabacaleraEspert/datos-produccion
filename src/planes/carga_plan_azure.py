"""
Carga el Plan de Producción (Excel) a Azure SQL.

Flujo: parse nombre → parse Plan (V22) → DataFrames → insert en
ProduccionPlanificaciones y ProduccionReal.

Uso (desde la raíz del repo):
  python src/planes/carga_plan_azure.py [ruta_plan.xlsx] [hoja]

  - Sin argumentos: busca en la raíz del repo archivos .xlsx con "Plan" en el nombre
    y usa el único (o el primero por orden alfabético si hay varios).
  - ruta_plan.xlsx: archivo Plan Excel (si lo pasás, usa ese).
  - hoja: opcional; nombre de la hoja a leer.

Requisitos:
  - .env con AZURE_SQL_SERVER, AZURE_SQL_DB, AZURE_SQL_USER, AZURE_SQL_PASSWORD.
  - Tablas creadas en Azure (ejecutar sql/create_tables_plan.sql si no existen).
  - pip install -r requirements-azure.txt  (pyodbc) si usas Python 3.11/3.12.
"""
import sys
from pathlib import Path

# Poner src en el path para config, db, marcas, run_summary
_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

import time
import traceback
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(_src_dir.parent / ".env")

import pandas as pd
from sqlalchemy import Date
from sqlalchemy.exc import IntegrityError, OperationalError

from config import (
    PLAN_VERSION,
    PLAN_PRODUCCION,
    AZURE_TABLA_PLANIFICACIONES,
    AZURE_TABLA_REAL,
    AZURE_PLAN_IF_EXISTS,
)
from planes.parse_plan import parse_plan_filename
from db import build_engine, smoke_test, load_dataframe, load_dataframe_skip_duplicates
from run_summary import RunSummary


def _log(msg: str) -> None:
    """Log con hora para seguir el progreso."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_plan_or_real(engine, df, table_name: str) -> tuple[int, str | None]:
    """
    Inserta el DataFrame; si falla por UNIQUE, inserta fila a fila omitiendo duplicados.
    Devuelve (filas_insertadas, mensaje_omitidas o None).
    """
    if df.empty:
        return 0, None
    _log(f"Insertando {table_name} ({len(df)} filas)...")
    dtype_fecha = {"Fecha": Date()}
    try:
        n = load_dataframe(
            engine,
            df,
            table_name,
            schema="dbo",
            if_exists=AZURE_PLAN_IF_EXISTS,
            dtype=dtype_fecha,
        )
        _log(f"  {table_name}: insert masivo OK ({n} filas)")
        return n, None
    except IntegrityError:
        _log(f"  {table_name}: hay duplicados, insertando fila a fila...")
        inserted, skipped = load_dataframe_skip_duplicates(
            engine,
            df,
            table_name,
            schema="dbo",
            if_exists=AZURE_PLAN_IF_EXISTS,
            dtype=dtype_fecha,
        )
        msg = f"{skipped} filas omitidas (clave duplicada)" if skipped else None
        _log(f"  {table_name}: listo (insertadas {inserted}, omitidas {skipped})")
        return inserted, msg


def _load_with_connection_retry(engine, df, table_name: str):
    """
    Igual que _load_plan_or_real pero si falla por Communication link failure (OperationalError),
    reconecta y reintenta una vez.
    """
    try:
        return _load_plan_or_real(engine, df, table_name)
    except OperationalError:
        _log(f"  {table_name}: fallo de conexión, reconectando en 2s y reintentando...")
        time.sleep(2)
        engine = build_engine()
        return _load_plan_or_real(engine, df, table_name)


def _result_to_dataframe(rows: list) -> pd.DataFrame:
    """Convierte filas del parser en DataFrame. Id_Producto = Id_Marca para respetar UQ (Fecha, Id_Producto)."""
    if not rows:
        return pd.DataFrame()
    out = [dict(r) for r in rows]
    df = pd.DataFrame(out)
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    # Azure tiene UNIQUE (Fecha, Id_Producto): una fila por fecha y "producto" (marca)
    df["Id_Producto"] = df["Id_Marca"]
    return df


def process_one_plan_file(plan_path: str, sheet_name: str | None, engine) -> tuple:
    """
    Procesa un solo archivo Plan: parsea nombre, parsea Excel y sube a Azure.
    Devuelve (éxito: bool, n_plan: int, n_real: int, errores: list[str]).
    """
    errors = []
    plan_info = parse_plan_filename(plan_path)
    if plan_info.errors or not plan_info.fecha_desde or not plan_info.plan_id:
        errors.extend(plan_info.errors or ["Falta plan_id o fecha en el nombre del archivo"])
        return False, 0, 0, errors
    try:
        if PLAN_VERSION == "v22":
            from planes.plan_v22 import parse_plan_produccion_v22
            result = parse_plan_produccion_v22(plan_path, plan_info, sheet_name=sheet_name)
        else:
            from planes.plan_parser import parse_plan_produccion
            sheet = sheet_name or PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")
            result = parse_plan_produccion(
                plan_path,
                sheet,
                plan_info,
                fila_header_excel=PLAN_PRODUCCION.get("fila_header_excel", 108),
                filas_datos_excel=PLAN_PRODUCCION.get("filas_datos"),
            )
        n_plan, n_real = 0, 0
        try:
            plan_ok = [r for r in result.planificaciones if (r.get("CantidadAProducir") or 0) != 0]
            real_ok = [r for r in result.real if (r.get("CantidadProducida") or 0) != 0]
            df_plan = _result_to_dataframe(plan_ok)
            n_plan, msg_plan = _load_with_connection_retry(engine, df_plan, AZURE_TABLA_PLANIFICACIONES)
            if msg_plan:
                errors.append(f"Planificaciones: {msg_plan}")
        except Exception as e:
            errors.append(f"Planificaciones: {type(e).__name__}: {e}")
        try:
            df_real = _result_to_dataframe(real_ok)
            n_real, msg_real = _load_with_connection_retry(engine, df_real, AZURE_TABLA_REAL)
            if msg_real:
                errors.append(f"Real: {msg_real}")
        except Exception as e:
            errors.append(f"Real: {type(e).__name__}: {e}")
        return len(errors) == 0, n_plan, n_real, errors
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
        return False, 0, 0, errors


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    if len(sys.argv) > 1:
        plan_path = sys.argv[1]
    else:
        # Sin argumentos: usar el único Plan .xlsx en la raíz (o el primero si hay varios)
        planes_en_raiz = sorted(
            f for f in root.glob("*.xlsx")
            if "plan" in f.name.lower() and not f.name.startswith("~$")
        )
        if not planes_en_raiz:
            print("No hay ningún archivo Plan (.xlsx con 'Plan' en el nombre) en la raíz del repo.", file=sys.stderr)
            print("Uso: python src/planes/carga_plan_azure.py [ruta_plan.xlsx] [hoja]", file=sys.stderr)
            return 1
        plan_path = str(planes_en_raiz[0])
        if len(planes_en_raiz) > 1:
            print(f"Varios Plan en la raíz; se usa el primero: {planes_en_raiz[0].name}\n", file=sys.stderr)
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None

    title = Path(plan_path).name if plan_path else "Plan de Producción"
    summary = RunSummary(title=title)
    _log("Inicio carga Plan → Azure")
    _log(f"Archivo: {Path(plan_path).name}")

    # ----- Paso 1: Parse del nombre del archivo -----
    _log("Paso 1: Leyendo nombre del archivo...")
    try:
        plan_info = parse_plan_filename(plan_path)
        if plan_info.errors:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=False,
                errors=plan_info.errors,
                data={"archivo": plan_path},
            )
        else:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=True,
                data={
                    "archivo": plan_path,
                    "Plan ID": plan_info.plan_id,
                    "Versión": plan_info.version,
                    "Período": f"{plan_info.fecha_desde} a {plan_info.fecha_hasta}",
                },
            )
    except Exception as e:
        summary.add_step(
            "Lectura del nombre del archivo",
            success=False,
            errors=[f"{type(e).__name__}: {e}"],
            data={"archivo": plan_path},
        )
        print(summary.to_text(), file=sys.stderr)
        return 1

    if not plan_info.fecha_desde or not plan_info.plan_id:
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 1: OK")

    # ----- Paso 2: Parse del Plan (resumen por marca) -----
    _log("Paso 2: Procesando Excel...")
    try:
        if not Path(plan_path).exists():
            raise FileNotFoundError(f"No se encontró el archivo: {plan_path}")
        if PLAN_VERSION == "v22":
            from planes.plan_v22 import parse_plan_produccion_v22
            result = parse_plan_produccion_v22(plan_path, plan_info, sheet_name=sheet_name)
        else:
            from planes.plan_parser import parse_plan_produccion
            sheet = sheet_name or PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")
            result = parse_plan_produccion(
                plan_path,
                sheet,
                plan_info,
                fila_header_excel=PLAN_PRODUCCION.get("fila_header_excel", 108),
                filas_datos_excel=PLAN_PRODUCCION.get("filas_datos"),
            )
        n_plan = len(result.planificaciones)
        n_real = len(result.real)
        summary.add_step(
            "Procesamiento del Plan (Excel)",
            success=True,
            messages=[f"Filas planificaciones: {n_plan}", f"Filas real: {n_real}"],
            data={"hoja": sheet_name or PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")},
        )
        if result.errors:
            for e in result.errors:
                summary.steps[-1].errors.append(e)
                summary.steps[-1].success = False
    except Exception as e:
        summary.add_step(
            "Procesamiento del Plan (Excel)",
            success=False,
            errors=[f"{type(e).__name__}: {e}", traceback.format_exc()[:500]],
            data={"archivo": plan_path},
        )
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 2: OK")

    # ----- Paso 3: Conexión a Azure SQL -----
    _log("Paso 3: Conectando a Azure SQL...")
    try:
        engine = build_engine()
        if not smoke_test(engine):
            raise RuntimeError("Conexión a Azure SQL falló (smoke_test). Revisa AZURE_SQL_* en .env.")
        summary.add_step(
            "Conexión a Azure SQL",
            success=True,
            messages=["Conexión OK"],
        )
    except Exception as e:
        summary.add_step(
            "Conexión a Azure SQL",
            success=False,
            errors=[f"{type(e).__name__}: {e}"],
        )
        print(summary.to_text(), file=sys.stderr)
        return 1
    _log("Paso 3: OK")

    # ----- Paso 4: Insertar ProduccionPlanificaciones (UNIQUE: omite duplicados y sigue) -----
    _log("Paso 4: Insertando Planificaciones...")
    try:
        plan_ok = [r for r in result.planificaciones if (r.get("CantidadAProducir") or 0) != 0]
        df_plan = _result_to_dataframe(plan_ok)
        n_plan, msg_plan = _load_with_connection_retry(engine, df_plan, AZURE_TABLA_PLANIFICACIONES)
        msgs = [f"Filas insertadas: {n_plan}"]
        if msg_plan:
            msgs.append(msg_plan)
        summary.add_step(
            f"Inserción en {AZURE_TABLA_PLANIFICACIONES}",
            success=True,
            messages=msgs,
            data={"tabla": AZURE_TABLA_PLANIFICACIONES, "filas": n_plan},
        )
        _log("Paso 4: OK")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        summary.add_step(
            f"Inserción en {AZURE_TABLA_PLANIFICACIONES}",
            success=False,
            errors=[err_msg],
            data={"tabla": AZURE_TABLA_PLANIFICACIONES},
        )
        _log(f"Paso 4: ERROR - {err_msg[:60]}...")
        # No hacer return: seguir con ProduccionReal

    # ----- Paso 5: Insertar ProduccionReal (UNIQUE: omite duplicados y sigue) -----
    _log("Paso 5: Insertando Real...")
    try:
        real_ok = [r for r in result.real if (r.get("CantidadProducida") or 0) != 0]
        df_real = _result_to_dataframe(real_ok)
        n_real, msg_real = _load_with_connection_retry(engine, df_real, AZURE_TABLA_REAL)
        msgs = [f"Filas insertadas: {n_real}"]
        if msg_real:
            msgs.append(msg_real)
        summary.add_step(
            f"Inserción en {AZURE_TABLA_REAL}",
            success=True,
            messages=msgs,
            data={"tabla": AZURE_TABLA_REAL, "filas": n_real},
        )
        _log("Paso 5: OK")
    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        summary.add_step(
            f"Inserción en {AZURE_TABLA_REAL}",
            success=False,
            errors=[err_msg],
            data={"tabla": AZURE_TABLA_REAL},
        )
        _log(f"Paso 5: ERROR - {err_msg[:60]}...")

    _log("Fin del run")
    print(summary.to_text())
    if not summary.success:
        print("\n(Algunos pasos fallaron; revisa los marcados con ✗ arriba.)")
    return 0 if summary.success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
