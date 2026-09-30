"""Carga a Azure SQL de los Excel de formato UNIFICADO (ago-2026+).

Uso:
    python src/carga_unificado.py planes-unificados/           # carpeta entera
    python src/carga_unificado.py "planes-unificados/Plan 290 ...xlsx"

Idempotente por semana: borra las filas de esa semana (lunes..domingo) en las
5 tablas antes de insertar. Conexión: pyodbc con el .env del repo
(AZURE_SQL_*); en macOS ARM exportar DYLD_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib
si pyodbc no encuentra OpenSSL.
"""
from __future__ import annotations

import glob
import os
import sys
from datetime import timedelta
from pathlib import Path

import pyodbc
from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).parent))
from marcas import id_from_descripcion, id_from_descripcion_fuzzy  # noqa: E402
from unificado import parse_unificado  # noqa: E402


def buscar_marca(nombre: str):
    mid = id_from_descripcion(nombre)
    if mid is None:
        r = id_from_descripcion_fuzzy(nombre)
        mid = r[0] if r else None
    return mid


def conectar():
    env = dotenv_values(Path(__file__).parent.parent / ".env")
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        f"SERVER={env['AZURE_SQL_SERVER']};DATABASE={env['AZURE_SQL_DB']};"
        f"UID={env['AZURE_SQL_USER']};PWD={env['AZURE_SQL_PASSWORD']};Encrypt=yes;",
        autocommit=False,
    )


def cargar_archivo(cur, path: str) -> dict:
    d = parse_unificado(path, buscar_marca)
    lunes = d["lunes"]
    fin = lunes + timedelta(days=6)

    # limpieza de la semana (re-carga segura)
    cur.execute("DELETE FROM dbo.ProduccionPlanificaciones WHERE Fecha BETWEEN ? AND ?", lunes, fin)
    cur.execute("DELETE FROM dbo.ProduccionReal WHERE Fecha BETWEEN ? AND ?", lunes, fin)
    cur.execute("DELETE FROM dbo.RendimientoReal WHERE Fecha BETWEEN ? AND ?", lunes, fin)
    cur.execute("DELETE FROM dbo.ProduccionDiariaPorTurno WHERE Fecha BETWEEN ? AND ?", lunes, fin)
    cur.execute("DELETE FROM dbo.RendimientoTabaco WHERE fecha BETWEEN ? AND ?", lunes, fin)

    cur.executemany(
        "INSERT INTO dbo.ProduccionPlanificaciones (Fecha, Id_Marca, Id_Producto, CantidadAProducir) VALUES (?, ?, ?, ?)",
        [(f, m, m, c) for f, m, c in d["plan"]],  # Id_Producto = Id_Marca (UQ Fecha+Producto, criterio del ETL viejo)
    ) if d["plan"] else None
    cur.executemany(
        "INSERT INTO dbo.ProduccionReal (Fecha, Id_Marca, Id_Producto, CantidadProducida) VALUES (?, ?, ?, ?)",
        [(f, m, m, c) for f, m, c in d["real"]],
    ) if d["real"] else None
    cur.executemany(
        "INSERT INTO dbo.RendimientoReal (Fecha, id_maquina, Turno, Eficiencia, RendimientoDeseado, VelocidadDeseado)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        d["rendimiento"],
    ) if d["rendimiento"] else None
    cur.executemany(
        "INSERT INTO dbo.ProduccionDiariaPorTurno (Fecha, Id_Maquina, Turno, CantidadProducida) VALUES (?, ?, ?, ?)",
        [(f, m, t, c) for f, m, t, c in d["produccion_turno"]],
    ) if d["produccion_turno"] else None
    if d["tabaco"] and d["tabaco"][1] is not None and d["tabaco"][2] is not None:
        cur.execute(
            "INSERT INTO dbo.RendimientoTabaco (fecha, ConsumoTeoricoKg, ConsumoRealKg) VALUES (?, ?, ?)",
            d["tabaco"],
        )
    return d


def main() -> int:
    destino = sys.argv[1] if len(sys.argv) > 1 else "planes-unificados/"
    archivos = (
        sorted(glob.glob(os.path.join(destino, "Plan*.xlsx")))
        if os.path.isdir(destino)
        else [destino]
    )
    if not archivos:
        print(f"Sin archivos Plan*.xlsx en {destino}")
        return 1
    cn = conectar()
    cur = cn.cursor()
    total_avisos = []
    for path in archivos:
        try:
            d = cargar_archivo(cur, path)
            cn.commit()
            print(
                f"✓ {Path(path).name[:34]:34} sem {d['lunes']} · "
                f"plan {len(d['plan']):3} · real {len(d['real']):3} · "
                f"rend {len(d['rendimiento']):2} · prod {len(d['produccion_turno']):3} · "
                f"tabaco {'sí' if d['tabaco'] else 'no'}"
            )
            total_avisos += [f"{Path(path).name}: {a}" for a in d["avisos"]]
        except Exception as e:  # noqa: BLE001
            cn.rollback()
            print(f"✗ {Path(path).name}: {e}")
    for a in total_avisos:
        print("⚠", a)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
