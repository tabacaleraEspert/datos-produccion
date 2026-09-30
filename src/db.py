import os
from typing import Any, List, Optional, Tuple

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()


def build_engine() -> Engine:
    server = os.getenv("AZURE_SQL_SERVER")
    db = os.getenv("AZURE_SQL_DB")
    user = os.getenv("AZURE_SQL_USER")
    pwd = os.getenv("AZURE_SQL_PASSWORD")
    driver = os.getenv("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server")
    encrypt = os.getenv("AZURE_SQL_ENCRYPT", "yes")
    trust_cert = os.getenv("AZURE_SQL_TRUST_CERT", "no")

    if not all([server, db, user, pwd]):
        raise RuntimeError("Faltan variables de entorno AZURE_SQL_* en .env")

    # SQLAlchemy + pyodbc
    conn_str = (
        f"mssql+pyodbc://{user}:{pwd}@{server}:1433/{db}"
        f"?driver={driver.replace(' ', '+')}"
        f"&Encrypt={encrypt}&TrustServerCertificate={trust_cert}"
    )
    return create_engine(conn_str, pool_pre_ping=True, fast_executemany=True)

def smoke_test(engine: Engine) -> bool:
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1 AS ok")).mappings().first()
        return res["ok"] == 1


def list_tables(engine: Engine, schema: str = "dbo") -> List[Tuple[str, str]]:
    q = text("""
        SELECT TABLE_SCHEMA, TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE='BASE TABLE' AND TABLE_SCHEMA=:schema
        ORDER BY TABLE_NAME
    """)
    with engine.connect() as conn:
        rows = conn.execute(q, {"schema": schema}).fetchall()
    return [(r[0], r[1]) for r in rows]


def load_dataframe(
    engine: Engine,
    df: pd.DataFrame,
    table_name: str,
    schema: str = "dbo",
    if_exists: str = "replace",
    dtype: Optional[Any] = None,
) -> int:
    """
    Carga un DataFrame en una tabla de Azure SQL.
    - if_exists: "replace" (trunca y escribe), "append" o "fail".
    - dtype: opcional, para forzar tipos (ej. VARCHAR en lugar de TEXT).
    Devuelve el número de filas escritas.
    """
    if df.empty:
        return 0
    n = len(df)
    df.to_sql(
        table_name,
        engine,
        schema=schema,
        if_exists=if_exists,
        index=False,
        method="multi",
        chunksize=1000,
        dtype=dtype,
    )
    return n


def load_dataframe_skip_duplicates(
    engine: Engine,
    df: pd.DataFrame,
    table_name: str,
    schema: str = "dbo",
    if_exists: str = "append",
    dtype: Optional[Any] = None,
) -> Tuple[int, int]:
    """
    Inserta filas una a una; si una falla por UNIQUE/duplicado, la omite y sigue.
    Devuelve (filas_insertadas, filas_omitidas).
    """
    if df.empty:
        return 0, 0
    total = len(df)
    inserted, skipped = 0, 0
    for idx in range(total):
        row_df = df.iloc[idx : idx + 1].copy()
        try:
            row_df.to_sql(
                table_name,
                engine,
                schema=schema,
                if_exists=if_exists,
                index=False,
                method="multi",
                chunksize=1,
                dtype=dtype,
            )
            inserted += 1
        except IntegrityError:
            skipped += 1
        # Log progreso cada 25 filas para no parecer colgado
        if (idx + 1) % 25 == 0 or idx + 1 == total:
            print(f"    [{table_name}] {idx + 1}/{total} (insertadas: {inserted}, omitidas: {skipped})", flush=True)
    return inserted, skipped
