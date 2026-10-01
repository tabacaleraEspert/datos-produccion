"""Sync automático Drive → Azure SQL del formato UNIFICADO (job cron).

Baja de Drive los "Plan NNN ... (Villafranca-Ale).xlsx" modificados en los
últimos SYNC_DIAS días (de la carpeta raíz del plan y su subcarpeta anual) y
los recarga con carga_unificado (idempotente por semana).

Env del job (Container Apps Job `cj-tablero-etl-minuta`):
    GOOGLE_SA_JSON      contenido del JSON de la service account (secreto)
    AZURE_SQL_SERVER / AZURE_SQL_DB / AZURE_SQL_USER / AZURE_SQL_PASSWORD
                        (usuario `etl_tablero`: SELECT/INSERT/DELETE en las 5 tablas)
    SYNC_DIAS           ventana de modifiedTime (default 45)
    DRIVE_FOLDER_IDS    coma-separado (default: carpeta plan + subcarpeta 2026)

Corre local igual: GOOGLE_SA_JSON puede ser una ruta a archivo.
Salida: resumen por archivo + código 1 si TODO falló (para la alerta del job).
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

sys.path.insert(0, str(Path(__file__).parent))
from carga_unificado import cargar_archivo, conectar  # noqa: E402

CARPETAS_DEFAULT = "1CszRKCArk5OTgjyuGuWY4IMd3G0vsaJY,1lTSXAQQ1EFAbijaWQZGS-NdhbmK5nBso"


def _drive():
    raw = os.environ["GOOGLE_SA_JSON"]
    if raw.strip().startswith("{"):
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    else:
        creds = service_account.Credentials.from_service_account_file(
            raw, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def listar(svc, carpetas: list[str], dias: int) -> list[dict]:
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%S")
    vistos: dict[str, dict] = {}
    for fid in carpetas:
        q = (f"'{fid}' in parents and name contains 'Villafranca' "
             f"and name contains 'Plan' and modifiedTime > '{desde}' and trashed = false")
        r = svc.files().list(q=q, fields="files(id, name, modifiedTime)", pageSize=100).execute()
        for f in r.get("files", []):
            vistos[f["id"]] = f
    return sorted(vistos.values(), key=lambda f: f["name"])


def bajar(svc, file_id: str, destino: Path) -> None:
    req = svc.files().get_media(fileId=file_id)
    with open(destino, "wb") as fh:
        dl = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = dl.next_chunk()


def main() -> int:
    dias = int(os.environ.get("SYNC_DIAS", "45"))
    carpetas = [c.strip() for c in os.environ.get("DRIVE_FOLDER_IDS", CARPETAS_DEFAULT).split(",") if c.strip()]
    svc = _drive()
    archivos = listar(svc, carpetas, dias)
    print(f"[sync] {len(archivos)} archivos Villafranca modificados en {dias} días")
    if not archivos:
        print("[sync] nada para cargar")
        return 0

    cn = conectar()
    cur = cn.cursor()
    ok = fallos = 0
    with tempfile.TemporaryDirectory() as tmp:
        for f in archivos:
            destino = Path(tmp) / f["name"]
            try:
                bajar(svc, f["id"], destino)
                d = cargar_archivo(cur, str(destino))
                cn.commit()
                ok += 1
                print(f"[sync] ✓ {f['name'][:40]:40} sem {d['lunes']} · plan {len(d['plan'])} "
                      f"real {len(d['real'])} rend {len(d['rendimiento'])} prod {len(d['produccion_turno'])}")
                for a in d["avisos"]:
                    print(f"[sync] ⚠ {f['name'][:28]}: {a}")
            except Exception as e:  # noqa: BLE001
                cn.rollback()
                fallos += 1
                print(f"[sync] ✗ {f['name']}: {e}")
    print(f"[sync] fin: {ok} ok · {fallos} fallos")
    return 1 if (fallos and not ok) else 0


if __name__ == "__main__":
    raise SystemExit(main())
