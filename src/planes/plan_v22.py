"""
Plan Excel — Layout V22 (hardcodeado por filas).

En lugar de intentar inferir marcas/Plan/Real desde los textos, este módulo usa
un mapeo fijo de Id_Marca → filas de Plan y filas de Real, según el layout V22.

Por cada marca:
  - 2 filas de Plan (se suman por día)
  - 2 filas de Real (se suman por día)

Se produce UNA sola fila por día y por marca para ProduccionPlanificaciones
y UNA sola fila por día y por marca para ProduccionReal.

Uso:
  from planes.plan_v22 import VERSION, parse_plan_produccion_v22
  result = parse_plan_produccion_v22(path, plan_info)
"""
from typing import Optional, Dict, List

import pandas as pd

from config import PLAN_PRODUCCION

from .parse_plan import PlanFileInfo
from .plan_parser import PlanParseResult, COLS_DIAS, _parse_header_dates, _cell_int

VERSION = "v22"

# Layout V22: hoja y fila de header
LAYOUT_V22 = {
    "version": VERSION,
    "sheet_name": PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal"),
    "fila_header_excel": PLAN_PRODUCCION.get("fila_header_excel", 108),
}

# Mapeo Id_Marca → filas Excel (1-based): [plan1, plan2, real1, real2]
MAPPING_FILAS_V22: Dict[int, List[int]] = {
    6:  [109, 111, 113, 115],
    7:  [122, 124, 126, 128],
    8:  [135, 137, 139, 141],
    13: [148, 150, 152, 154],
    50: [161, 163, 165, 167],
    14: [174, 176, 178, 180],
    15: [187, 189, 191, 193],
    9:  [212, 214, 216, 218],
    10: [225, 227, 229, 231],
    11: [238, 240, 242, 244],
    12: [251, 253, 255, 257],
    20: [264, 266, 268, 270],
    19: [277, 279, 281, 283],
    17: [290, 292, 294, 296],
}


def _sumar_filas_por_dia(df: pd.DataFrame, filas_excel: List[int]) -> List[int]:
    """
    Suma, por día (columnas C–I), las filas Excel indicadas (1-based).
    Devuelve una lista de 7 enteros (uno por día).
    """
    nrows = len(df)
    sums = [0] * len(COLS_DIAS)
    for fila in filas_excel:
        idx = fila - 1  # 0-based para pandas
        if idx < 0 or idx >= nrows:
            continue
        row = df.iloc[idx]
        for k, col_idx in enumerate(COLS_DIAS):
            if col_idx < len(row):
                v = _cell_int(row.iloc[col_idx] if hasattr(row, "iloc") else row[col_idx])
                sums[k] += v
    return sums


def parse_plan_produccion_v22(
    xlsx_path: str,
    plan_info: PlanFileInfo,
    sheet_name: Optional[str] = None,
) -> PlanParseResult:
    """
    Parser específico para Plan V22 usando filas hardcodeadas por Id_Marca.
    """
    result = PlanParseResult()
    if not plan_info.fecha_desde:
        result.errors.append("Falta fecha_desde en plan_info para interpretar el header de fechas.")
        return result

    layout = LAYOUT_V22
    sheet = sheet_name or layout["sheet_name"]

    df = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, engine="openpyxl")
    nrows = len(df)

    # Header de fechas
    fila_h = layout["fila_header_excel"] - 1
    if fila_h >= nrows or fila_h < 0:
        fila_h = 0
    row_header = df.iloc[fila_h]
    fechas = _parse_header_dates(row_header, plan_info)
    if len(fechas) < len(COLS_DIAS):
        result.errors.append("No se pudieron parsear 7 fechas en el header; usando fecha_desde para completar.")
        while len(fechas) < len(COLS_DIAS):
            fechas.append(plan_info.fecha_desde)
    fechas = fechas[: len(COLS_DIAS)]

    # Por cada marca: sumar filas de Plan y de Real
    for id_marca, filas in MAPPING_FILAS_V22.items():
        if len(filas) != 4:
            continue
        filas_plan = filas[0:2]
        filas_real = filas[2:4]

        plan_vals = _sumar_filas_por_dia(df, filas_plan)
        real_vals = _sumar_filas_por_dia(df, filas_real)

        # Planificaciones: una fila por día (si cantidad > 0)
        for k, fecha in enumerate(fechas):
            if k < len(plan_vals) and plan_vals[k] != 0:
                result.planificaciones.append(
                    {
                        "Id_Proceso": 1,
                        "Id_Producto": 0,
                        "Id_Marca": id_marca,
                        "Id_TipoTabaco": 0,
                        "Id_TipoCajetilla": 0,
                        "Id_VariedadProducto": 0,
                        "Fecha": fecha,
                        "CantidadAProducir": plan_vals[k],
                        "Estado": None,
                        "cantidadProducida": None,
                    }
                )

        # Real: una fila por día (si cantidad > 0)
        for k, fecha in enumerate(fechas):
            if k < len(real_vals) and real_vals[k] != 0:
                result.real.append(
                    {
                        "Id_Proceso": 1,
                        "Id_Producto": 0,
                        "Id_Marca": id_marca,
                        "Id_TipoTabaco": 0,
                        "Id_TipoCajetilla": 0,
                        "Id_VariedadProducto": 0,
                        "Fecha": fecha,
                        "CantidadProducida": real_vals[k],
                        "Estado": None,
                    }
                )

    return result
