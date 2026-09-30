"""
Carga ConsumoTeoricoKg y ConsumoRealKg desde la Minuta a Azure (RendimientoTabaco).

Lee B83 y H83 de la hoja "Datos crudos". Una fila por minuta (fecha = lunes de la semana).

Uso: python src/minutas/rendimiento_tabaco/carga_azure.py [ruta_minuta.xlsx] [hoja]
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

from config import AZURE_TABLA_RENDIMIENTO_TABACO, AZURE_MINUTA_IF_EXISTS
from minutas.parse_minuta import parse_minuta_filename
from minutas.rendimiento_tabaco.parser import parse_rendimiento_tabaco
from db import build_engine, smoke_test, load_dataframe, load_dataframe_skip_duplicates


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent.parent
    if len(sys.argv) > 1:
        minuta_path = sys.argv[1]
    else:
        minutas = sorted(f for f in root.glob("*.xlsx") if "minuta" in f.name.lower() and not f.name.startswith("~$"))
        if not minutas:
            print("No hay Minuta en la raíz.", file=sys.stderr)
            return 1
        minuta_path = str(minutas[0])
        if len(minutas) > 1:
            _log(f"Varias Minutas; se usa: {minutas[0].name}")
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None

    _log("Inicio carga RendimientoTabaco (B83, H83) → Azure")
    _log(f"Archivo: {Path(minuta_path).name}")

    try:
        minuta_info = parse_minuta_filename(minuta_path)
        if not minuta_info.fecha:
            print("Error: falta fecha en el nombre del archivo.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error parse nombre: {e}", file=sys.stderr)
        return 1

    _log("Procesando Excel (Datos crudos, fila 83)...")
    try:
        result = parse_rendimiento_tabaco(minuta_path, minuta_info, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error parse: {e}", file=sys.stderr)
        return 1

    if result.errors:
        for e in result.errors:
            _log(f"  Aviso: {e}")

    if not result.fila:
        _log("No hay datos para insertar (B83 y H83 vacíos o no numéricos).")
        return 0

    r = result.fila
    _log(f"  Fecha (lunes semana): {r.fecha}")
    _log(f"  ConsumoTeoricoKg: {r.consumo_teorico_kg}")
    _log(f"  ConsumoRealKg: {r.consumo_real_kg}")

    try:
        engine = build_engine()
        if not smoke_test(engine):
            raise RuntimeError("Conexión a Azure SQL falló.")
        _log("Conexión a Azure OK")
    except Exception as e:
        print(f"Error conexión: {e}", file=sys.stderr)
        return 1

    df = pd.DataFrame([{
        "Fecha": r.fecha,
        "ConsumoTeoricoKg": r.consumo_teorico_kg,
        "ConsumoRealKg": r.consumo_real_kg,
    }])
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    dtype_fecha = {"Fecha": Date()}

    _log(f"Insertando en {AZURE_TABLA_RENDIMIENTO_TABACO}...")
    try:
        n = load_dataframe(engine, df, AZURE_TABLA_RENDIMIENTO_TABACO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"OK: {n} fila(s) insertada(s)")
    except IntegrityError:
        inserted, skipped = load_dataframe_skip_duplicates(engine, df, AZURE_TABLA_RENDIMIENTO_TABACO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"Insertadas: {inserted}, omitidas (duplicadas): {skipped}")
    except OperationalError:
        import time
        _log("Fallo de conexión, reintentando en 2s...")
        time.sleep(2)
        engine = build_engine()
        n = load_dataframe(engine, df, AZURE_TABLA_RENDIMIENTO_TABACO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"OK: {n} fila(s) insertada(s) (reintento)")

    _log("Fin")
    return 0


if __name__ == "__main__":
    sys.exit(main())
