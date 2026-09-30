"""
Carga producción diaria por turno desde la Minuta Excel a Azure SQL (ProduccionDiariaPorTurno).

Uso: python src/minutas/produccion_diaria/carga_azure.py [ruta_minuta.xlsx] [hoja]
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

from config import AZURE_TABLA_PRODUCCION_DIARIA_TURNO, AZURE_MINUTA_IF_EXISTS
from minutas.parse_minuta import parse_minuta_filename
from minutas.produccion_diaria.parser import parse_produccion_diaria, ProduccionDiariaRow
from db import build_engine, smoke_test, load_dataframe, load_dataframe_skip_duplicates
from run_summary import RunSummary


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _rows_to_dataframe(rows: list[ProduccionDiariaRow]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    data = [{"Id_Maquina": r.id_maquina, "Fecha": r.fecha, "Turno": r.turno, "CantidadProducida": r.cantidad_producida} for r in rows]
    df = pd.DataFrame(data)
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    return df


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
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None

    summary = RunSummary(title=Path(minuta_path).name)
    _log("Inicio carga ProduccionDiariaPorTurno → Azure")

    try:
        minuta_info = parse_minuta_filename(minuta_path)
        if not minuta_info.fecha:
            print("Error: falta fecha en el nombre del archivo.", file=sys.stderr)
            return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    try:
        result = parse_produccion_diaria(minuta_path, minuta_info, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error parse: {e}", file=sys.stderr)
        return 1

    if not result.filas:
        _log("No hay filas para insertar.")
        return 0

    try:
        engine = build_engine()
        if not smoke_test(engine):
            raise RuntimeError("Conexión a Azure SQL falló.")
    except Exception as e:
        print(f"Error conexión: {e}", file=sys.stderr)
        return 1

    df = _rows_to_dataframe(result.filas)
    dtype_fecha = {"Fecha": Date()}
    try:
        n = load_dataframe(engine, df, AZURE_TABLA_PRODUCCION_DIARIA_TURNO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"Insertadas {n} filas en {AZURE_TABLA_PRODUCCION_DIARIA_TURNO}")
    except IntegrityError:
        inserted, skipped = load_dataframe_skip_duplicates(engine, df, AZURE_TABLA_PRODUCCION_DIARIA_TURNO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"Insertadas: {inserted}, omitidas: {skipped}")
    except OperationalError:
        import time
        time.sleep(2)
        engine = build_engine()
        n = load_dataframe(engine, df, AZURE_TABLA_PRODUCCION_DIARIA_TURNO, schema="dbo", if_exists=AZURE_MINUTA_IF_EXISTS, dtype=dtype_fecha)
        _log(f"Insertadas {n} filas (reintento OK)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
