"""
Parse del nombre del archivo PLAN para extraer:
- plan_id: número del plan (ej. 255)
- version: v22 (normalizada; en el nombre puede ser "v 22" con espacio)
- fecha_desde / fecha_hasta: YYYY-MM-DD (ej. 26 al 31 ENE 2026 → 2026-01-26, 2026-01-31)

Ejemplo: "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
         → plan_id=255, version="v22", fecha_desde="2026-01-26", fecha_hasta="2026-01-31"
Si falta algo, se añade un mensaje descriptivo en info.errors.
"""
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

# Meses en español (abrev 3 letras) → número
MES_ABREV_A_NUM: Dict[str, int] = {
    "ENE": 1, "Ene": 1, "ene": 1,
    "FEB": 2, "Feb": 2, "feb": 2,
    "MAR": 3, "Mar": 3, "mar": 3,
    "ABR": 4, "Abr": 4, "abr": 4,
    "MAY": 5, "May": 5, "may": 5,
    "JUN": 6, "Jun": 6, "jun": 6,
    "JUL": 7, "Jul": 7, "jul": 7,
    "AGO": 8, "Ago": 8, "ago": 8,
    "SEP": 9, "Sep": 9, "sep": 9,
    "OCT": 10, "Oct": 10, "oct": 10,
    "NOV": 11, "Nov": 11, "nov": 11,
    "DIC": 12, "DEC": 12, "Dic": 12, "Dec": 12, "dic": 12, "dec": 12,
}


@dataclass
class PlanFileInfo:
    """Información extraída del nombre del archivo Plan."""
    plan_id: Optional[int]   # ej. 255
    version: Optional[str]  # ej. "v22" (normalizada sin espacio)
    fecha_desde: Optional[str]  # YYYY-MM-DD
    fecha_hasta: Optional[str]  # YYYY-MM-DD
    errors: List[str]  # errores descriptivos si falta algo


def _normalize_version(s: str) -> str:
    """Quita espacio entre 'v' y el número: 'v 22' → 'v22'."""
    s = s.strip()
    return re.sub(r"v\s+(\d+)", r"v\1", s, flags=re.IGNORECASE)


def parse_plan_filename(filename: str) -> PlanFileInfo:
    """
    Parsea el nombre del archivo Plan (con o sin ruta).

    Espera formato tipo: "Plan 255 del 26 al 31 ENE 2026 v 22 ..."
    - plan_id: número tras "Plan"
    - fecha: "26 al 31 ENE 2026" → fecha_desde=2026-01-26, fecha_hasta=2026-01-31
    - version: "v 22" o "v22" → normalizada a "v22"
    """
    basename = os.path.basename(filename)
    errors: List[str] = []

    # Plan ID: "Plan 255" o "Plan255"
    plan_id = None
    plan_match = re.search(r"Plan\s*(\d+)", basename, re.IGNORECASE)
    if plan_match:
        plan_id = int(plan_match.group(1))
    else:
        errors.append(f"No se encontró ID del plan (número tras 'Plan') en: «{basename}».")

    # Versión: "v 22" o "v22" (permite espacio). La 'v' no debe ser parte de otra palabra (ej. NOV)
    version = None
    version_match = re.search(r"(?<![A-Za-z])v\s*\d+", basename, re.IGNORECASE)
    if version_match:
        version = _normalize_version(version_match.group(0))
    else:
        errors.append(f"No se encontró versión (formato 'v N' o 'vN') en: «{basename}».")

    # Fechas: "del 26 al 31 ENE 2026" (o "Ene", "ENE", etc.)
    fecha_desde = None
    fecha_hasta = None
    # Patrón: del DD al DD MMM AAAA (mes 3 letras, año 4 dígitos)
    rango_match = re.search(
        r"del\s+(\d{1,2})\s+al\s+(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})",
        basename,
        re.IGNORECASE,
    )
    if rango_match:
        d1, d2, mes_abrev, anio = rango_match.groups()
        day_from = int(d1)
        day_to = int(d2)
        mes_num = MES_ABREV_A_NUM.get(mes_abrev)
        if mes_num is not None:
            fecha_desde = f"{anio}-{mes_num:02d}-{day_from:02d}"
            fecha_hasta = f"{anio}-{mes_num:02d}-{day_to:02d}"
        else:
            errors.append(
                f"Mes no reconocido «{mes_abrev}». Esperado: ENE, FEB, MAR, ABR, MAY, JUN, "
                "JUL, AGO, SEP, OCT, NOV, DIC/DEC."
            )
    else:
        errors.append(
            f"No se encontró rango de fechas (formato 'del DD al DD MMM AAAA', ej. 'del 26 al 31 ENE 2026') en: «{basename}»."
        )

    return PlanFileInfo(
        plan_id=plan_id,
        version=version,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        errors=errors,
    )


if __name__ == "__main__":
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parent.parent.parent
    default = _root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    info = parse_plan_filename(path)
    print(f"Archivo: {path}")
    print(f"Plan ID: {info.plan_id}")
    print(f"Versión: {info.version}")
    print(f"Fecha desde: {info.fecha_desde}")
    print(f"Fecha hasta: {info.fecha_hasta}")
    if info.errors:
        print("Errores:")
        for e in info.errors:
            print(f"  - {e}")
