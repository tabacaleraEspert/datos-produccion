"""
Diagnóstico: qué hay realmente en el Excel del Plan.
Ejecutar: python src/planes/diagnostico_plan.py [ruta_al_plan.xlsx]
"""
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent.parent
    default = root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    sheet_name = "Plan - Semanal"

    import pandas as pd

    print("=" * 60)
    print("DIAGNÓSTICO PLAN EXCEL")
    print("=" * 60)
    print(f"Archivo: {path}")
    print()

    xl = pd.ExcelFile(path, engine="openpyxl")
    print("Hojas en el archivo:", xl.sheet_names)
    print()

    if sheet_name not in xl.sheet_names:
        print(f"  ⚠ La hoja '{sheet_name}' NO existe.")
        print("  Hojas disponibles:", [s for s in xl.sheet_names])
        sheet_name = xl.sheet_names[0]
        print(f"  Usando primera hoja: {sheet_name}")
    print()

    df = pd.read_excel(path, sheet_name=sheet_name, header=None, engine="openpyxl")
    print(f"Dimensiones: {len(df)} filas, {len(df.columns)} columnas")
    print()

    # Fila 107 (Excel 108) - header de fechas
    print("--- Fila 108 (índice 107) - debería ser header de fechas ---")
    row107 = df.iloc[107].tolist() if len(df) > 107 else []
    for j in range(min(12, len(row107))):
        cell = row107[j] if j < len(row107) else None
        print(f"  Col {j} ({'ABCDEFGHIJ'[j] if j < 10 else '?'}): {repr(cell)}")
    print()

    # Buscar filas con TABES en columna A
    print("--- Filas donde columna A contiene 'TABES' (primeras 30) ---")
    count = 0
    for i in range(min(350, len(df))):
        if count >= 30:
            break
        cell = df.iloc[i].iloc[0] if len(df.columns) > 0 else None
        if pd.isna(cell):
            continue
        s = str(cell).strip()
        if "TABES" not in s.upper():
            continue
        count += 1
        print(f"  Fila Excel {i+1} (índice {i}): {repr(s[:70])}...")
    if count == 0:
        print("  (ninguna encontrada)")
    print()

    # Primeras 25 celdas no vacías de columna A
    print("--- Primeras 25 celdas NO VACÍAS de columna A ---")
    count = 0
    for i in range(min(400, len(df))):
        if count >= 25:
            break
        cell = df.iloc[i].iloc[0] if len(df.columns) > 0 else None
        if cell is None or (pd.isna(cell)) or str(cell).strip() == "":
            continue
        count += 1
        s = str(cell).strip()
        print(f"  Fila {i+1}: {repr(s[:80])}")
    if count == 0:
        print("  (columna A vacía en las primeras 400 filas)")
    print()

    # Valores en columnas C-I para fila 108 (primera fila de datos según spec)
    print("--- Fila 109 (índice 108) - columnas C a I (índices 2-8) ---")
    if len(df) > 108:
        row108 = df.iloc[108].tolist()
        for j in range(2, 9):
            cell = row108[j] if j < len(row108) else None
            print(f"  Col {j}: {repr(cell)}")
    print()
    print("--- Fin diagnóstico ---")

if __name__ == "__main__":
    main()
