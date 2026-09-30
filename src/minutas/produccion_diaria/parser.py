"""
Parser de producción diaria por máquina y turno desde la Minuta Excel.

Tabla destino: ProduccionDiariaPorTurno (Id_Maquina, Fecha, Turno, CantidadProducida)

LAYOUT V22 — Misma hoja "Datos crudos", mismo esquema días/turnos y orden de máquinas que eficiencia.
Cantidades en filas distintas (enteros grandes).
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ..parse_minuta import MinutaFileInfo

from ..eficiencia.parser import (
    SHEET_EFICIENCIA,
    COL_PRIMER_DIA,
    TURNOS,
    ORDER_ID_MAQUINA_V22,
)

# Filas Excel (1-based) donde están las cantidades. V22: mismo orden que ORDER_ID_MAQUINA_V22.
FILAS_CANTIDAD_V22 = [5, 10, 15, 20, 22, 24, 26, 28, 30, 33, 35, 37, 40, 45, 51, 57]
MAPPING_FILA_MAQUINA_PRODUCCION_V22: Dict[int, int] = dict(zip(FILAS_CANTIDAD_V22, ORDER_ID_MAQUINA_V22))


@dataclass
class ProduccionDiariaRow:
    """Una fila para ProduccionDiariaPorTurno."""
    id_maquina: int
    fecha: str  # YYYY-MM-DD
    turno: str  # TD, TJ, TN
    cantidad_producida: int


@dataclass
class ProduccionDiariaParseResult:
    """Resultado del parse."""
    filas: List[ProduccionDiariaRow] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _semana_anterior_lunes(fecha_str: str) -> datetime:
    d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    lunes_actual = d - timedelta(days=d.weekday())
    lunes_anterior = lunes_actual - timedelta(days=7)
    return datetime.combine(lunes_anterior, datetime.min.time())


def _columna_a_dia_turno(col_idx: int) -> Tuple[int, int]:
    offset = col_idx - COL_PRIMER_DIA
    if offset < 0 or offset >= 21:
        return -1, -1
    return offset // 3, offset % 3


def _parse_cantidad(cell) -> Optional[int]:
    """Convierte celda a int. None si vacío, "N" o no numérico."""
    if cell is None or (hasattr(pd, "isna") and pd.isna(cell)):
        return None
    s = str(cell).strip().upper()
    if s == "N" or not s:
        return None
    try:
        return int(float(str(cell).replace(",", ".")))
    except (ValueError, TypeError):
        return None


def parse_produccion_diaria(
    xlsx_path: str,
    minuta_info: MinutaFileInfo,
    sheet_name: Optional[str] = None,
) -> ProduccionDiariaParseResult:
    """
    Lee la hoja y extrae CantidadProducida por máquina, fecha y turno.
    Pendiente: confirmar filas/columnas exactas en el Excel.
    """
    result = ProduccionDiariaParseResult()
    if not minuta_info.fecha:
        result.errors.append("Falta fecha en minuta_info.")
        return result

    sheet = sheet_name or SHEET_EFICIENCIA
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, engine="openpyxl")
    except Exception as e:
        result.errors.append(f"No se pudo leer la hoja '{sheet}': {e}")
        return result

    nrows = len(df)
    lunes_semana = _semana_anterior_lunes(minuta_info.fecha)
    fechas_por_dia = [(lunes_semana + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    for fila_excel, id_maquina in MAPPING_FILA_MAQUINA_PRODUCCION_V22.items():
        idx = fila_excel - 1
        if idx >= nrows:
            continue
        row = df.iloc[idx]
        for col_idx in range(COL_PRIMER_DIA, min(COL_PRIMER_DIA + 21, len(row))):
            cantidad = _parse_cantidad(row.iloc[col_idx] if hasattr(row, "iloc") else row[col_idx])
            if cantidad is None or cantidad < 0:
                continue
            dia, turno_idx = _columna_a_dia_turno(col_idx)
            if dia < 0:
                continue
            fecha = fechas_por_dia[dia]
            turno = TURNOS[turno_idx]
            result.filas.append(
                ProduccionDiariaRow(
                    id_maquina=id_maquina,
                    fecha=fecha,
                    turno=turno,
                    cantidad_producida=cantidad,
                )
            )

    return result
