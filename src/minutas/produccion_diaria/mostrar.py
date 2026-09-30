"""
Muestra qué filas se enviarían a ProduccionDiariaPorTurno (sin cargar).

Uso: python src/minutas/produccion_diaria/mostrar.py [ruta_minuta.xlsx]
"""
import sys
from pathlib import Path
from collections import defaultdict

_src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_src_dir))

import pandas as pd

from minutas.parse_minuta import parse_minuta_filename
from minutas.produccion_diaria.parser import parse_produccion_diaria


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent.parent
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        minutas = sorted(f for f in root.glob("*.xlsx") if "minuta" in f.name.lower() and not f.name.startswith("~$"))
        if not minutas:
            print("No hay Minuta en la raíz.")
            return 1
        path = str(minutas[0])
        print(f"Usando: {minutas[0].name}\n")

    info = parse_minuta_filename(path)
    if info.errors or not info.fecha:
        print("Errores:", info.errors or ["Falta fecha"])
        return 1

    result = parse_produccion_diaria(path, info)
    print("=" * 70)
    print("PRODUCCION DIARIA POR TURNO (→ ProduccionDiariaPorTurno)")
    print("=" * 70)
    print(f"Archivo: {path}")
    print(f"Total filas: {len(result.filas)}")
    print()

    if not result.filas:
        print("(No hay datos. ¿Las cantidades están en otras filas/columnas?)")
        return 0

    df = pd.DataFrame([{"Id_Maquina": r.id_maquina, "Fecha": r.fecha, "Turno": r.turno, "CantidadProducida": r.cantidad_producida} for r in result.filas])
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date
    print("Primeras 20 filas:")
    print(df.head(20).to_string(index=False))
    if len(df) > 20:
        print(f"\n... y {len(df) - 20} más")
    print("\n--- Resumen por máquina ---")
    por_maq = defaultdict(int)
    for r in result.filas:
        por_maq[r.id_maquina] += r.cantidad_producida
    for id_m in sorted(por_maq.keys()):
        print(f"  Máquina {id_m}: total {por_maq[id_m]:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
