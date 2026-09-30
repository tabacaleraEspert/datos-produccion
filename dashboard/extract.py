"""Extrae datos de las tablas de producción de Azure SQL a JSON para el dashboard."""
import json, os, sys
from pathlib import Path

import pyodbc
from dotenv import dotenv_values

env = dotenv_values("/Users/davorvindis/Desktop/TabacaleraEspert/Produccion/datos-produccion/.env")

driver = env.get("AZURE_SQL_DRIVER") or "ODBC Driver 18 for SQL Server"
conn_str = (
    f"DRIVER={{{driver}}};SERVER={env['AZURE_SQL_SERVER']};DATABASE={env['AZURE_SQL_DB']};"
    f"UID={env['AZURE_SQL_USER']};PWD={env['AZURE_SQL_PASSWORD']};"
    f"Encrypt={env.get('AZURE_SQL_ENCRYPT','yes')};TrustServerCertificate={env.get('AZURE_SQL_TRUST_CERT','no')};"
    "Connection Timeout=30;"
)
cn = pyodbc.connect(conn_str)
cur = cn.cursor()

def q(sql):
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    out = []
    for row in cur.fetchall():
        d = {}
        for k, v in zip(cols, row):
            if hasattr(v, "isoformat"):
                v = v.isoformat()
            elif isinstance(v, (bytes, bytearray)):
                v = v.hex()
            elif hasattr(v, "__float__") and not isinstance(v, (int, float)):
                v = float(v)
            d[k] = v
        out.append(d)
    return out

data = {}
for name, sql in {
    "plan": "SELECT Id_Marca, Fecha, CantidadAProducir FROM ProduccionPlanificaciones ORDER BY Fecha",
    "real": "SELECT Id_Marca, Fecha, CantidadProducida FROM ProduccionReal ORDER BY Fecha",
    "rendimiento": "SELECT id_maquina, Fecha, Turno, Eficiencia, VelocidadDeseado, RendimientoDeseado FROM RendimientoReal ORDER BY Fecha",
    "prod_turno": "SELECT Id_Maquina, Fecha, Turno, CantidadProducida FROM ProduccionDiariaPorTurno ORDER BY Fecha",
    "tabaco": "SELECT Fecha, ConsumoTeoricoKg, ConsumoRealKg FROM RendimientoTabaco ORDER BY Fecha",
}.items():
    try:
        data[name] = q(sql)
        print(f"{name}: {len(data[name])} filas", file=sys.stderr)
    except Exception as e:
        print(f"{name}: ERROR {e}", file=sys.stderr)
        data[name] = []

out = Path(__file__).parent / "data.json"
out.write_text(json.dumps(data, ensure_ascii=False))
print(f"escrito {out} ({out.stat().st_size} bytes)", file=sys.stderr)
