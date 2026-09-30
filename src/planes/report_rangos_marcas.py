"""
Genera una lista de rangos de filas Excel por marca para que puedas verificar
qué celdas está leyendo el parser. Ejecutar: python src/planes/report_rangos_marcas.py [ruta_plan.xlsx]
"""
import sys
from pathlib import Path
from collections import defaultdict

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

import pandas as pd
from planes.plan_parser import COL_NOMBRE, COLS_DIAS, _normalize_text, _extraer_marca, _tipo_fila


def main():
    root = Path(__file__).resolve().parent.parent.parent
    default = root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    from config import PLAN_PRODUCCION
    sheet = PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")
    filas_datos = PLAN_PRODUCCION.get("filas_datos", [(109, 199), (212, 302)])

    df = pd.read_excel(path, sheet_name=sheet, header=None, engine="openpyxl")
    nrows = len(df)

    # Recorrer cada bloque y anotar (fila_excel, marca, tipo, valores C-I como resumen)
    registros = []
    for (a, b) in filas_datos:
        inicio = max(0, a - 1)
        fin = min(nrows - 1, b - 1)
        for i in range(inicio, fin + 1):
            row = df.iloc[i]
            if COL_NOMBRE >= len(row):
                continue
            cell = row.iloc[COL_NOMBRE] if hasattr(row, "iloc") else row[COL_NOMBRE]
            if pd.isna(cell) or str(cell).strip() == "":
                continue
            texto = _normalize_text(str(cell))
            marca = _extraer_marca(texto)
            tipo = _tipo_fila(texto)
            # Valores numéricos columnas C-I (resumen: suma)
            vals = []
            for j in COLS_DIAS:
                if j < len(row):
                    try:
                        v = row.iloc[j] if hasattr(row, "iloc") else row[j]
                        vals.append(int(float(v)) if v is not None and not pd.isna(v) else 0)
                    except (ValueError, TypeError):
                        vals.append(0)
                else:
                    vals.append(0)
            suma = sum(vals)
            registros.append((i + 1, marca, tipo, vals, suma, texto[:55]))  # fila Excel 1-based

    # Agrupar por marca y mostrar rangos
    por_marca = defaultdict(list)
    for fila_excel, marca, tipo, vals, suma, texto_corto in registros:
        por_marca[marca].append((fila_excel, tipo, vals, suma, texto_corto))

    print("=" * 70)
    print("RANGOS DE FILAS EXCEL POR MARCA (columna B = nombre; columnas C-I = 7 días)")
    print("=" * 70)
    print(f"Archivo: {path}")
    print(f"Hoja: {sheet}")
    print(f"Bloques config: {filas_datos}")
    print()
    print("Cada marca: fila Excel inicial – final, y detalle de cada fila (tipo, suma 7 días).")
    print("Revisá si el rango y el tipo (Plan/Real/Real Total) son los correctos.")
    print()

    for marca in sorted(por_marca.keys(), key=lambda x: (por_marca[x][0][0] if por_marca[x] else 0)):
        filas = por_marca[marca]
        nums = [f[0] for f in filas]
        rango = f"{min(nums)}–{max(nums)}"
        print(f"--- {marca} (filas Excel {rango}) ---")
        for (fila_excel, tipo, vals, suma, texto_corto) in filas:
            tipo_str = tipo or "(ignorada)"
            print(f"  Fila {fila_excel}: {tipo_str}  |  suma 7 días = {suma}  |  {texto_corto}")
        print()

    print("--- Fin ---")


if __name__ == "__main__":
    main()
