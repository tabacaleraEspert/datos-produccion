"""
Muestra exactamente qué filas se enviarían a RendimientoReal (sin cargar a Azure).

Uso: python src/minutas/eficiencia/mostrar.py [ruta_minuta.xlsx]
"""
import sys
from pathlib import Path
from collections import defaultdict

_src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_src_dir))

import pandas as pd

from minutas.parse_minuta import parse_minuta_filename
from minutas.eficiencia.parser import parse_minuta_eficiencia, EficienciaRow


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
        path = sys.argv[1]
    else:
        minutas = sorted(f for f in root.glob("*.xlsx") if "minuta" in f.name.lower() and not f.name.startswith("~$"))
        if not minutas:
            print("No hay Minuta en la raíz. Uso: python src/minutas/eficiencia/mostrar.py [ruta_minuta.xlsx]")
            return 1
        path = str(minutas[0])
        print(f"Usando: {minutas[0].name}\n")

    info = parse_minuta_filename(path)
    if info.errors or not info.fecha:
        print("Errores en el nombre del archivo:")
        for e in info.errors or []:
            print(f"  - {e}")
        return 1

    result = parse_minuta_eficiencia(path, info)
    if result.errors:
        print("Avisos:")
        for e in result.errors:
            print(f"  - {e}")
        print()

    print("=" * 90)
    print("RENDIMIENTO REAL (lo que se enviaría a Azure → RendimientoReal)")
    print("=" * 90)
    print(f"Archivo: {path}")
    print(f"Fecha reunión: {info.fecha}  |  Semana de datos: lunes a domingo anterior")
    print(f"Total filas que se insertarían: {len(result.filas)}")
    print()

    if not result.filas:
        print("(No hay filas con eficiencia numérica)")
        return 0

    df = _rows_to_dataframe(result.filas)
    print("Columnas (igual que RendimientoReal):", list(df.columns))
    print()
    print("Primeras 20 filas:")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    print(df.head(20).to_string(index=False))
    print()
    if len(df) > 20:
        print(f"... y {len(df) - 20} filas más")
    print()

    print("--- Resumen por máquina ---")
    por_maquina = defaultdict(list)
    for r in result.filas:
        por_maquina[r.id_maquina].append((r.fecha, r.turno, r.eficiencia))
    for id_m in sorted(por_maquina.keys()):
        filas = por_maquina[id_m]
        r0 = next(r for r in result.filas if r.id_maquina == id_m)
        extra = []
        if r0.rendimiento_deseado is not None:
            extra.append(f"Rend.Deseado={r0.rendimiento_deseado}")
        if r0.velocidad_deseado is not None:
            extra.append(f"Vel.Deseado={r0.velocidad_deseado}")
        suf = f"  [{', '.join(extra)}]" if extra else ""
        print(f"  Máquina {id_m}: {len(filas)} registros{suf}")
    print("--- Fin ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
