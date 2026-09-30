from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd

@dataclass
class SheetProfile:
    sheet_name: str
    n_rows_previewed: int
    n_cols_previewed: int
    header_row_candidates: List[int]
    best_header_row: Optional[int]
    best_header: Optional[List[str]]
    non_empty_rows: int
    notes: List[str]

def _normalize_cell(x) -> str:
    if pd.isna(x):
        return ""
    s = str(x).strip()
    return " ".join(s.split())

def _score_header_row(row: List[str]) -> int:
    """
    Heurística simple:
    - puntúa por cantidad de celdas no vacías
    - penaliza repetidos/feos
    """
    non_empty = [c for c in row if c]
    if not non_empty:
        return 0
    unique = len(set(non_empty))
    score = len(non_empty) * 2 + unique
    # penaliza si parece una fila de datos (muchos números)
    numish = sum(1 for c in non_empty if c.replace(",", "").replace(".", "").isdigit())
    score -= numish
    return score

def profile_workbook(xlsx_path: str, preview_rows: int = 60) -> Tuple[List[str], Dict[str, SheetProfile]]:
    xls = pd.ExcelFile(xlsx_path, engine="openpyxl")
    profiles: Dict[str, SheetProfile] = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(
            xlsx_path,
            sheet_name=sheet,
            header=None,
            nrows=preview_rows,
            engine="openpyxl"
        )

        # Normaliza preview a strings
        preview = df.applymap(_normalize_cell)
        n_rows, n_cols = preview.shape

        # rows no vacías
        non_empty_rows = int((preview.apply(lambda r: any(v != "" for v in r), axis=1)).sum())

        # candidatos: filas con >=2 celdas no vacías
        header_candidates = []
        scored = []
        for i in range(n_rows):
            row = preview.iloc[i].tolist()
            non_empty = sum(1 for c in row if c)
            if non_empty >= 2:
                header_candidates.append(i)
                scored.append((i, _score_header_row(row), row))

        best_header_row = None
        best_header = None
        notes = []

        if scored:
            scored.sort(key=lambda t: t[1], reverse=True)
            best_header_row = scored[0][0]
            best_header = [c for c in scored[0][2] if c]  # solo no vacíos
            if best_header_row > 0:
                notes.append(f"Header probable no está en la primera fila (fila {best_header_row}).")
            if len(best_header) < 2:
                notes.append("Header detectado débil (pocas columnas). Posible hoja de notas/no tabular.")
        else:
            notes.append("No se detectaron filas candidatas a header. Posible hoja de notas/no tabular.")

        profiles[sheet] = SheetProfile(
            sheet_name=sheet,
            n_rows_previewed=n_rows,
            n_cols_previewed=n_cols,
            header_row_candidates=header_candidates[:10],
            best_header_row=best_header_row,
            best_header=best_header,
            non_empty_rows=non_empty_rows,
            notes=notes
        )

    return xls.sheet_names, profiles
