"""
Parser del Excel Plan (layout V22).
Columna B = Nombre (marca + Plan/Real); columnas C-I = 7 días.
Lee los bloques de filas configurados y extrae Plan y Real por marca/día.
Si el Plan cambia de versión, ver plan_v22 / config PLAN_VERSION.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd

from marcas import id_from_descripcion, id_from_descripcion_fuzzy

from .parse_plan import PlanFileInfo

# Columnas: A=0, B=1, C=2 ... Nombre/marca en B; 7 días en C-I
COL_NOMBRE = 1
COL_C, COL_I = 2, 8
COLS_DIAS = list(range(COL_C, COL_I + 1))

HEADER_DAY_PATTERN = re.compile(
    r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[-\s]*(\d{1,2})$", re.IGNORECASE
)


@dataclass
class PlanParseResult:
    """Resultado del parse: listas de filas para cada tabla y errores."""
    planificaciones: List[dict] = field(default_factory=list)
    real: List[dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _normalize_text(s: str) -> str:
    """Normaliza texto: minúsculas, espacios colapsados."""
    return " ".join((s or "").strip().lower().split())


def _extraer_marca(texto: str) -> str:
    """Quita sufijos 'Plan', 'Real', 'Real Total' y devuelve el nombre de marca."""
    t = _normalize_text(texto)
    for sufijo in (" real total", " real", " plan"):
        if t.endswith(sufijo):
            return t[: -len(sufijo)].strip()
    return t.strip()


def _tipo_fila(texto: str) -> Optional[str]:
    """Devuelve 'plan', 'real', 'real_total' o None."""
    t = _normalize_text(texto)
    if t.endswith(" real total"):
        return "real_total"
    if t.endswith(" real"):
        return "real"
    if t.endswith(" plan"):
        return "plan"
    return None


def _cell_to_day(cell, plan_info: PlanFileInfo) -> Optional[int]:
    """Extrae el día (1-31) de una celda del header."""
    if cell is None or pd.isna(cell):
        return None
    if isinstance(cell, (pd.Timestamp, datetime)):
        return cell.day
    s = str(cell).strip()
    if not s:
        return None
    m = HEADER_DAY_PATTERN.match(s)
    if m:
        return int(m.group(1))
    if s.isdigit():
        return int(s)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            d = datetime.strptime(s[:10], fmt)
            return d.day
        except (ValueError, TypeError):
            continue
    return None


def _parse_header_dates(row, plan_info: PlanFileInfo) -> List[str]:
    """Convierte la fila de header en lista de 7 fechas YYYY-MM-DD."""
    if not plan_info.fecha_desde:
        return []
    from datetime import datetime as dt
    parts = plan_info.fecha_desde.split("-")
    if len(parts) != 3:
        return []
    anio, mes = int(parts[0]), int(parts[1])
    fechas = []
    for j in COLS_DIAS:
        if j >= len(row):
            fechas.append(plan_info.fecha_desde)
            continue
        cell = row.iloc[j] if hasattr(row, "iloc") else row[j]
        dia = _cell_to_day(cell, plan_info)
        if dia is None:
            fechas.append(plan_info.fecha_desde)
            continue
        try:
            d = dt(anio, mes, dia)
            fechas.append(d.strftime("%Y-%m-%d"))
        except ValueError:
            if mes == 12 and dia > 28:
                d = dt(anio + 1, 1, min(dia, 31))
            else:
                d = dt(anio, min(mes + 1, 12), min(dia, 28))
            fechas.append(d.strftime("%Y-%m-%d"))
    return fechas[:7]


def _cell_int(val) -> int:
    """Convierte celda a int (0 si no es número)."""
    if val is None or pd.isna(val):
        return 0
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _is_espacio(row: list) -> bool:
    """True si la fila está vacía o solo tiene espacios."""
    for c in row:
        if c is not None and not (pd.isna(c) if hasattr(pd, "isna") else c != c):
            if str(c).strip():
                return False
    return True


def parse_plan_produccion(
    xlsx_path: str,
    sheet_name: str,
    plan_info: PlanFileInfo,
    fila_header_excel: Optional[int] = None,
    filas_datos_excel: Optional[List[Tuple[int, int]]] = None,
) -> PlanParseResult:
    """
    Lee el Excel del Plan y extrae filas para ProduccionPlanificaciones y ProduccionReal.
    """
    result = PlanParseResult()
    if not plan_info.fecha_desde:
        result.errors.append("Falta fecha_desde en plan_info.")
        return result

    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, engine="openpyxl")
    nrows = len(df)

    fila_h = (fila_header_excel or 108) - 1
    if fila_h >= nrows:
        fila_h = 0
    if fila_h < 0:
        fila_h = 0

    row_header = df.iloc[fila_h]
    fechas = _parse_header_dates(row_header, plan_info)
    if len(fechas) < 7:
        result.errors.append("No se pudieron parsear 7 fechas en el header.")
        fechas = [plan_info.fecha_desde] * 7

    if filas_datos_excel:
        bloques = [(max(0, a - 1), min(nrows - 1, b - 1)) for a, b in filas_datos_excel]
    else:
        bloques = [(108, 198), (211, 301)]

    plan_por_marca = {}
    real_por_marca = {}
    real_total_por_marca = {}

    for inicio, fin in bloques:
        for i in range(inicio, fin + 1):
            row = df.iloc[i].tolist()
            if _is_espacio(row):
                continue
            texto_b = row[COL_NOMBRE] if COL_NOMBRE < len(row) else None
            texto_b = str(texto_b).strip() if texto_b is not None and not pd.isna(texto_b) else ""
            if not texto_b:
                continue
            tipo = _tipo_fila(texto_b)
            if tipo is None:
                continue
            marca_str = _extraer_marca(texto_b)
            id_marca = id_from_descripcion(marca_str)
            if id_marca is None:
                fuzzy = id_from_descripcion_fuzzy(marca_str, cutoff=0.45)
                if fuzzy is not None:
                    id_marca, _ = fuzzy
                else:
                    result.errors.append(
                        f"Marca no reconocida: «{marca_str}» (fila {i + 1})"
                    )
                    continue
            valores = [_cell_int(row[j]) if j < len(row) else 0 for j in COLS_DIAS]
            valores = (valores + [0] * 7)[:7]

            if tipo == "plan":
                if marca_str not in plan_por_marca:
                    plan_por_marca[marca_str] = [0] * 7
                for k, v in enumerate(valores):
                    if k < len(plan_por_marca[marca_str]):
                        plan_por_marca[marca_str][k] += v
            elif tipo == "real_total":
                real_total_por_marca[marca_str] = valores  # clave = nombre base (sin " Real Total")
            elif tipo == "real":
                if marca_str not in real_por_marca:
                    real_por_marca[marca_str] = [0] * 7
                for k, v in enumerate(valores):
                    if k < len(real_por_marca[marca_str]):
                        real_por_marca[marca_str][k] += v

    # Plan: una fila por Id_Marca y día
    for marca_str, vals in plan_por_marca.items():
        id_marca = id_from_descripcion(marca_str)
        if id_marca is None:
            fuzzy = id_from_descripcion_fuzzy(marca_str, cutoff=0.45)
            id_marca = fuzzy[0] if fuzzy else None
        if id_marca is None:
            continue
        for k, fecha in enumerate(fechas):
            if k < len(vals):
                result.planificaciones.append({
                    "Id_Proceso": 1,
                    "Id_Producto": 0,
                    "Id_Marca": id_marca,
                    "Id_TipoTabaco": 0,
                    "Id_TipoCajetilla": 0,
                    "Id_VariedadProducto": 0,
                    "Fecha": fecha,
                    "CantidadAProducir": vals[k],
                    "Estado": None,
                    "cantidadProducida": None,
                })

    # Real: agrupar por Id_Marca para evitar duplicar marcas con nombres distintos.
    # Regla: si existe algún \"Real Total\" para la marca, se usan SOLO esos valores;
    # si no, se suman todas las filas \"Real\" (por Id_Marca).

    # 1) Mapear Real Total por Id_Marca
    real_total_by_id: dict[int, List[int]] = {}
    for marca_str, vals in real_total_por_marca.items():
        id_marca = id_from_descripcion(marca_str)
        if id_marca is None:
            fuzzy = id_from_descripcion_fuzzy(marca_str, cutoff=0.45)
            id_marca = fuzzy[0] if fuzzy else None
        if id_marca is None:
            continue
        dest = real_total_by_id.setdefault(id_marca, [0] * len(vals))
        for k, v in enumerate(vals):
            if k < len(dest):
                dest[k] += v

    # 2) Mapear Real (solo se usará si NO hay Real Total para ese Id_Marca)
    real_by_id: dict[int, List[int]] = {}
    for marca_str, vals in real_por_marca.items():
        id_marca = id_from_descripcion(marca_str)
        if id_marca is None:
            fuzzy = id_from_descripcion_fuzzy(marca_str, cutoff=0.45)
            id_marca = fuzzy[0] if fuzzy else None
        if id_marca is None:
            continue
        dest = real_by_id.setdefault(id_marca, [0] * len(vals))
        for k, v in enumerate(vals):
            if k < len(dest):
                dest[k] += v

    # 3) Construir filas reales por Id_Marca
    for id_marca in sorted(set(real_by_id) | set(real_total_by_id)):
        if id_marca in real_total_by_id:
            vals = real_total_by_id[id_marca]
        else:
            vals = real_by_id.get(id_marca, [0] * len(fechas))
        for k, fecha in enumerate(fechas):
            if k < len(vals):
                result.real.append({
                    "Id_Proceso": 1,
                    "Id_Producto": 0,
                    "Id_Marca": id_marca,
                    "Id_TipoTabaco": 0,
                    "Id_TipoCajetilla": 0,
                    "Id_VariedadProducto": 0,
                    "Fecha": fecha,
                    "CantidadProducida": vals[k],
                    "Estado": None,
                })

    return result
