"""
Referencia de marcas: Id ↔ Descripcion.
Se usa para resolver Id_Marca al leer el Plan (por marca) y cargar ProduccionReal / ProduccionPlanificaciones.
Más adelante se puede cargar desde la base de datos.
Matching por cercanía: si el nombre no coincide exacto, se busca la descripción más parecida.
"""
import difflib
from typing import Dict, Optional, Tuple

# Id -> Descripcion (tal como en la tabla Marcas en Azure)
MARCAS: Dict[int, str] = {
    6: "MelbourneRed",
    7: "MelbourneGold",
    8: "MelbourneMint",
    9: "MilenioRed",
    10: "MilenioGold",
    11: "MilenioMint",
    12: "MilenioClick",
    13: "Mill",
    14: "BoldRed",
    15: "BoldMint",
    16: "MillRed",
    17: "MillExplosion",
    18: "MilenioClickPY",
    19: "MilenioPink",
    20: "MilenioVid",
    21: "310Mint",
    22: "330Espert",
    23: "330MINT",
    24: "360Caps6",
    25: "360caps6Click",
    26: "360caps6Explosion",
    27: "360Full",
    28: "360full-Espert",
    29: "380Full-Espert",
    30: "400Light",
    31: "400-Ligth-Espert",
    32: "410Ligth-Espert",
    33: "400 PINK",
    34: "400 VID",
    35: "330Full",
    36: "375caps12PINK",
    37: "375caps12VID",
    38: "400caps12Pink",
    39: "375caps12Vid",
    40: "Mill-Flama",
    42: "MilenioIcergyPink",
    43: "MilenioIcergy",
    44: "Milenio-Gold-Flama",
    45: "MilenioClickPY-1",
    47: "MelbourneMint-Flama",
    48: "ClickFlama",
    49: "MilenioIcergyPY",
    50: "MillMint",
}

# Descripcion -> Id (para buscar Id_Marca desde el nombre en el Excel; normalizado sin espacios extra)
DESCRIPCION_TO_ID: Dict[str, int] = {v.strip(): k for k, v in MARCAS.items()}


def _normalize_for_match(name: str) -> str:
    """Quita espacios, guiones y pasa a minúsculas para matchear (ej. 'Melbourne Red' → 'melbournered')."""
    return (name or "").replace(" ", "").replace("-", "").strip().lower()


def id_from_descripcion(descripcion: str) -> Optional[int]:
    """Devuelve Id_Marca para una Descripcion, o None si no existe. Acepta con/sin espacios."""
    key = (descripcion or "").strip()
    if key in DESCRIPCION_TO_ID:
        return DESCRIPCION_TO_ID[key]
    # En el Excel puede venir "Melbourne Red" (con espacio); en la tabla "MelbourneRed"
    normal = _normalize_for_match(key)
    for desc, id_ in DESCRIPCION_TO_ID.items():
        if _normalize_for_match(desc) == normal:
            return id_
    return None


# Para matching por cercanía: lista de descripciones normalizadas
_NORMAL_TO_ID: Dict[str, int] = {_normalize_for_match(d): id_ for d, id_ in DESCRIPCION_TO_ID.items()}


def id_from_descripcion_fuzzy(descripcion: str, cutoff: float = 0.45) -> Optional[Tuple[int, str]]:
    """
    Devuelve (Id_Marca, descripcion_matched) por cercanía, o None.
    cutoff: 0-1; más bajo = más permisivo. 0.45 permite "Bold full" → BoldRed/BoldMint, "Milenio VID ICE" → MilenioVid.
    """
    key = (descripcion or "").strip()
    if not key:
        return None
    exact = id_from_descripcion(key)
    if exact is not None:
        return (exact, MARCAS[exact])
    normal = _normalize_for_match(key)
    candidatos = list(_NORMAL_TO_ID.keys())
    if not candidatos:
        return None
    matches = difflib.get_close_matches(normal, candidatos, n=1, cutoff=cutoff)
    if not matches:
        return None
    id_ = _NORMAL_TO_ID[matches[0]]
    return (id_, MARCAS[id_])
