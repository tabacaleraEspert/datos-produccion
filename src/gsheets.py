"""
Conexión a Google Sheets y lectura de hojas.
Requiere: cuenta de servicio (JSON) y compartir el Sheet con el email del cliente.
"""
import os
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Scope para solo leer/escribir en Sheets (no Drive completo)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def _get_client():
    """Crea cliente de gspread autenticado con cuenta de servicio."""
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.isfile(creds_path):
        raise FileNotFoundError(
            "Variable GOOGLE_APPLICATION_CREDENTIALS debe apuntar al JSON de la cuenta de servicio. "
            "Crea una en Google Cloud Console y comparte el Sheet con el email del cliente."
        )
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet(sheet_id: Optional[str] = None, url: Optional[str] = None):
    """
    Abre el spreadsheet por ID o por URL.
    Prioridad: sheet_id si viene, si no se extrae de url.
    """
    sid = sheet_id or os.getenv("GOOGLE_SHEET_ID")
    if url and not sid:
        # Extraer ID de URL tipo https://docs.google.com/spreadsheets/d/ID/edit
        for part in url.replace("?", "&").split("&"):
            if part.startswith("/d/") or "spreadsheets/d/" in part:
                sid = part.split("/d/")[-1].split("/")[0].strip()
                break
    if not sid:
        raise ValueError("Indica GOOGLE_SHEET_ID o url con el ID del spreadsheet.")
    client = _get_client()
    return client.open_by_key(sid)


def get_worksheet_names(spreadsheet) -> List[str]:
    """Lista los nombres de todas las hojas del spreadsheet."""
    return [ws.title for ws in spreadsheet.worksheets()]


def sheet_to_dataframe(
    spreadsheet,
    sheet_name: str,
    header_row: int = 0,
    expected_columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Lee una hoja y devuelve un DataFrame.
    - header_row: fila 0-based donde está el encabezado.
    - expected_columns: si se pasa, se usan como nombres de columnas (y se alinean por orden).
    """
    ws = spreadsheet.worksheet(sheet_name)
    all_values = ws.get_all_values()
    if not all_values:
        return pd.DataFrame()

    # Fila de cabecera y datos
    header = all_values[header_row]
    data_rows = all_values[header_row + 1 :]

    # Nombres de columnas: normalizar vacíos a "col_N"
    col_names = []
    for i, h in enumerate(header):
        name = (str(h).strip() if h else "") or f"col_{i}"
        col_names.append(name)

    df = pd.DataFrame(data_rows, columns=col_names)

    # Reemplazar "" por NaN y limpiar
    df = df.replace("", pd.NA)
    if expected_columns:
        # Usar solo las columnas esperadas que existan; reordenar si aplica
        existing = [c for c in expected_columns if c in df.columns]
        if existing:
            df = df[existing].copy()
    return df


def profile_sheet(spreadsheet, sheet_name: str, preview_rows: int = 60) -> Dict[str, Any]:
    """
    Perfila una hoja (similar a excel_profile): detecta fila de header y da resumen.
    Útil para definir SHEET_RULES sin abrir Excel.
    """
    ws = spreadsheet.worksheet(sheet_name)
    all_values = ws.get_all_values()[: preview_rows + 10]
    if not all_values:
        return {"sheet_name": sheet_name, "non_empty_rows": 0, "best_header_row": None, "best_header": None, "notes": ["Hoja vacía."]}

    from excel_profile import _score_header_row

    n_rows = len(all_values)
    header_candidates = []
    scored = []
    for i in range(n_rows):
        row = [str(c).strip() for c in all_values[i]]
        non_empty = [c for c in row if c]
        if len(non_empty) >= 2:
            header_candidates.append(i)
            scored.append((i, _score_header_row(row), row))

    best_header_row = None
    best_header = None
    notes = []
    if scored:
        scored.sort(key=lambda t: t[1], reverse=True)
        best_header_row = scored[0][0]
        best_header = [c for c in scored[0][2] if c]
        if best_header_row > 0:
            notes.append(f"Header probable no está en la primera fila (fila {best_header_row}).")
        if len(best_header) < 2:
            notes.append("Header detectado débil. Posible hoja de notas/no tabular.")
    else:
        notes.append("No se detectaron filas candidatas a header.")

    non_empty_rows = sum(1 for row in all_values if any(str(c).strip() for c in row))
    return {
        "sheet_name": sheet_name,
        "n_rows_previewed": n_rows,
        "non_empty_rows": non_empty_rows,
        "best_header_row": best_header_row,
        "best_header": best_header,
        "notes": notes,
    }
