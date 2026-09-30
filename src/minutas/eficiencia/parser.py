"""
Parser de eficiencias de máquinas desde la hoja 'Datos crudos' de la Minuta Excel.

LAYOUT V22 — En otras versiones pueden agregarse/quitarse máquinas o cambiar filas.

Estructura V22:
- Fila 66: días de la semana (Lunes..Domingo), cada día en 3 columnas
- Fila 67: turnos (T:D, T:J, T:N) por día
- Filas 68-84 (excepto 81): columna B = máquina, resto = % eficiencia
- Velocidad deseada: columna C, filas 90-105
- Valor "N" = no trabajó, no se sube

Mapeo fila Excel (1-based) → id_maquina (V22)
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ..parse_minuta import MinutaFileInfo

# Layout V22 — cambiar si la minuta pasa a otra versión
LAYOUT_VERSION = "v22"

# Hoja y filas (V22)
SHEET_EFICIENCIA = "Datos crudos"
FILA_DIAS = 65      # 0-based (Excel 66)
FILA_TURNOS = 66    # 0-based (Excel 67)
FILA_PRIMERA_MAQUINA = 67  # 0-based (Excel 68)
COL_MAQUINA = 1     # B
COL_PRIMER_DIA = 2  # C (Lunes TD)

# Días: Lunes=0..Domingo=6. Cada día tiene 3 columnas (TD, TJ, TN)
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TURNOS = ["TD", "TJ", "TN"]  # T:D→TD, T:J→TJ, T:N→TN

# Mapeo fila Excel (1-based) → id_maquina (V22). Fila 81 vacía.
MAPPING_FILA_MAQUINA_V22: Dict[int, int] = {
    68: 1,
    69: 2,
    70: 13,
    71: 3,
    72: 4,
    73: 6,   # Corregido: fila 73 = id 6
    74: 15,
    75: 8,
    76: 7,
    77: 16,
    78: 9,
    79: 5,
    80: 17,
    82: 10,
    83: 14,
    84: 18,
}

# Velocidad deseada (V22): columna C, filas 90-105. Mismo orden de máquinas.
FILA_VELOCIDAD_DESEADO_INICIO_V22 = 90  # 1-based
ORDER_ID_MAQUINA_V22 = [1, 2, 13, 3, 4, 6, 15, 8, 7, 16, 9, 5, 17, 10, 14, 18]

# Rendimiento deseado fijo por máquina (V22, en orden ORDER_ID_MAQUINA_V22).
RENDIMIENTO_DESEADO_VALUES_V22 = [67, 67, 67, 65, 65, 70, 70, 65, 70, 70, 65, 70, 70, 80, 80, 80]
RENDIMIENTO_DESEADO_POR_MAQUINA_V22: Dict[int, float] = dict(zip(ORDER_ID_MAQUINA_V22, RENDIMIENTO_DESEADO_VALUES_V22))

# Aliases para uso actual (V22)
MAPPING_FILA_MAQUINA = MAPPING_FILA_MAQUINA_V22
ORDER_ID_MAQUINA = ORDER_ID_MAQUINA_V22
RENDIMIENTO_DESEADO_POR_MAQUINA = RENDIMIENTO_DESEADO_POR_MAQUINA_V22
FILA_VELOCIDAD_DESEADO_INICIO = FILA_VELOCIDAD_DESEADO_INICIO_V22


@dataclass
class EficienciaRow:
    """Una fila para RendimientoReal."""
    id_maquina: int
    fecha: str  # YYYY-MM-DD
    turno: str  # TD, TJ, TN
    eficiencia: float
    velocidad: Optional[float] = None
    unidad: Optional[str] = None
    rendimiento_deseado: Optional[float] = None
    velocidad_deseado: Optional[float] = None


@dataclass
class EficienciaParseResult:
    """Resultado del parse de eficiencias."""
    filas: List[EficienciaRow] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _semana_anterior_lunes(fecha_str: str) -> datetime:
    """Devuelve el lunes de la semana anterior a la fecha de la minuta."""
    d = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    lunes_actual = d - timedelta(days=d.weekday())
    lunes_anterior = lunes_actual - timedelta(days=7)
    return datetime.combine(lunes_anterior, datetime.min.time())


def _columna_a_dia_turno(col_idx: int) -> Tuple[int, int]:
    """Convierte índice de columna (0-based) a (dia_semana 0-6, turno 0-2)."""
    offset = col_idx - COL_PRIMER_DIA
    if offset < 0 or offset >= 21:
        return -1, -1
    dia = offset // 3
    turno = offset % 3
    return dia, turno


def _parse_numero(cell) -> Optional[float]:
    """Convierte celda a float. None si vacío o no numérico."""
    if cell is None or (hasattr(pd, "isna") and pd.isna(cell)):
        return None
    if isinstance(cell, (int, float)):
        return float(cell)
    try:
        return float(str(cell).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_eficiencia_valor(cell) -> Optional[float]:
    """
    Convierte celda a float (eficiencia %). Devuelve None si es "N" o vacío.
    Excel suele guardar porcentajes como decimal (0.59 = 59%); si v < 1, multiplicamos por 100.
    """
    if cell is None or (hasattr(pd, "isna") and pd.isna(cell)):
        return None
    if isinstance(cell, (int, float)):
        v = float(cell)
        if v < 0:
            return None
        if 0 < v < 1:
            v = v * 100
        return v if v <= 100 else None
    s = str(cell).strip().upper()
    if s == "N" or not s:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        v = float(s)
        if 0 < v < 1:
            v = v * 100
        return v if 0 <= v <= 100 else None
    except ValueError:
        return None


def parse_minuta_eficiencia(
    xlsx_path: str,
    minuta_info: MinutaFileInfo,
    sheet_name: Optional[str] = None,
) -> EficienciaParseResult:
    """
    Lee la hoja 'Datos crudos' y extrae eficiencias por máquina, fecha y turno.
    La fecha de la minuta define la semana de datos: lunes a domingo de la semana anterior.
    """
    result = EficienciaParseResult()
    if not minuta_info.fecha:
        result.errors.append("Falta fecha en minuta_info para calcular la semana de datos.")
        return result

    sheet = sheet_name or SHEET_EFICIENCIA
    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet, header=None, engine="openpyxl")
    except Exception as e:
        result.errors.append(f"No se pudo leer la hoja '{sheet}': {e}")
        return result

    nrows = len(df)
    lunes_semana = _semana_anterior_lunes(minuta_info.fecha)
    fechas_por_dia = [
        (lunes_semana + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(7)
    ]

    # Velocidad deseada: columna C (índice 2), filas 90-105
    velocidad_deseado_por_maquina: Dict[int, Optional[float]] = {}
    col_vel = 2
    for i, id_m in enumerate(ORDER_ID_MAQUINA):
        row_idx = FILA_VELOCIDAD_DESEADO_INICIO - 1 + i
        if row_idx < nrows:
            cell = df.iloc[row_idx, col_vel] if col_vel < df.shape[1] else None
            velocidad_deseado_por_maquina[id_m] = _parse_numero(cell)

    for fila_excel, id_maquina in MAPPING_FILA_MAQUINA.items():
        idx = fila_excel - 1
        if idx >= nrows:
            continue
        row = df.iloc[idx]
        for col_idx in range(COL_PRIMER_DIA, min(COL_PRIMER_DIA + 21, len(row))):
            eficiencia = _parse_eficiencia_valor(row.iloc[col_idx] if hasattr(row, "iloc") else row[col_idx])
            if eficiencia is None:
                continue
            dia, turno_idx = _columna_a_dia_turno(col_idx)
            if dia < 0:
                continue
            fecha = fechas_por_dia[dia]
            turno = TURNOS[turno_idx]
            result.filas.append(
                EficienciaRow(
                    id_maquina=id_maquina,
                    fecha=fecha,
                    turno=turno,
                    eficiencia=round(eficiencia, 1),
                    rendimiento_deseado=RENDIMIENTO_DESEADO_POR_MAQUINA.get(id_maquina),
                    velocidad_deseado=velocidad_deseado_por_maquina.get(id_maquina),
                )
            )

    return result
