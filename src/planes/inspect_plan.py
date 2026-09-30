"""
Inspecciona el Excel del Plan: lista hojas y muestra primeras filas/columnas.
Ejecutar desde la raíz del repo con: python src/planes/inspect_plan.py [ruta_al_plan.xlsx]
"""
import sys
from pathlib import Path


def main():
    import pandas as pd
    root = Path(__file__).resolve().parent.parent.parent
    path = sys.argv[1] if len(sys.argv) > 1 else str(
        root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    )
    xl = pd.ExcelFile(path, engine="openpyxl")
    print("Hojas:", xl.sheet_names)
    for name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=name, header=None)
        print(f"\n--- {name} --- shape {df.shape}")
        # Primeras 14 columnas, 16 filas
        print(df.iloc[:16, :14].to_string())


if __name__ == "__main__":
    main()
