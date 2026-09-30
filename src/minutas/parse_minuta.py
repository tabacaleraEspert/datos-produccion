"""
Parse del nombre del archivo de minuta para extraer fecha y versión.
Ejemplo: "Minuta de reunion semanal EE4A 2026-01-28 v16 doble capsula.xlsx"
         → fecha: 2026-01-28, version: v16
Si falta fecha o versión, se añade un mensaje descriptivo en info.errors.
"""
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


# Fecha en formato YYYY-MM-DD
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")
# Versión: v seguido de uno o más dígitos
VERSION_PATTERN = re.compile(r"v\d+", re.IGNORECASE)


@dataclass
class MinutaFileInfo:
    """Información extraída del nombre del archivo de minuta."""
    fecha: Optional[str]  # YYYY-MM-DD
    version: Optional[str]  # ej. v16
    errors: List[str] = field(default_factory=list)  # errores descriptivos si falta algo


def parse_minuta_filename(filename: str) -> MinutaFileInfo:
    """
    Parsea el nombre del archivo (con o sin ruta) y extrae fecha y versión.

    - fecha: primera ocurrencia de YYYY-MM-DD
    - version: primera ocurrencia de vN (ej. v16)
    - errors: si falta fecha o versión, se añade un mensaje descriptivo

    Ejemplo:
        parse_minuta_filename("Minuta ... EE4A 2026-01-28 v16 doble capsula.xlsx")
        → MinutaFileInfo(fecha="2026-01-28", version="v16", errors=[])
    """
    basename = os.path.basename(filename)
    fecha_match = DATE_PATTERN.search(basename)
    version_match = VERSION_PATTERN.search(basename)

    fecha = fecha_match.group(0) if fecha_match else None
    version = version_match.group(0) if version_match else None

    errors: List[str] = []
    if fecha is None:
        errors.append(
            f"No se encontró fecha (formato YYYY-MM-DD) en el nombre del archivo: «{basename}»."
        )
    if version is None:
        errors.append(
            f"No se encontró versión (formato vN, ej. v16) en el nombre del archivo: «{basename}»."
        )

    return MinutaFileInfo(fecha=fecha, version=version, errors=errors)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    _root = Path(__file__).resolve().parent.parent.parent
    default = _root / "Minuta de reunion semanal EE4A 2026-01-28 v16 doble capsula.xlsx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default)
    info = parse_minuta_filename(path)
    print(f"Archivo: {path}")
    print(f"Fecha:   {info.fecha}")
    print(f"Versión: {info.version}")
    if info.errors:
        print("Errores:")
        for e in info.errors:
            print(f"  - {e}")
