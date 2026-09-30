"""
Flujo: Google Sheet → parseo → tablas en Azure SQL.
- Si SHEET_RULES está definido en config: lee cada hoja y carga en la tabla indicada.
- Si no hay reglas: perfila el Sheet y muestra resumen (para que definas SHEET_RULES).
"""
import os
import sys
from pathlib import Path

# Permite ejecutar desde la raíz del repo: python src/main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
from tabulate import tabulate

# .env en la raíz del repo
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from gsheets import open_spreadsheet, sheet_to_dataframe, profile_sheet, get_worksheet_names
from db import build_engine, smoke_test, list_tables, load_dataframe
from config import SHEET_RULES


def main():
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("Falta GOOGLE_SHEET_ID en .env (o URL del Sheet).")
        sys.exit(1)

    print("\n[1] Abriendo Google Sheet…")
    spreadsheet = open_spreadsheet(sheet_id=sheet_id)
    sheet_names = get_worksheet_names(spreadsheet)
    print(f"    Hojas: {', '.join(sheet_names)}")

    if SHEET_RULES:
        # Modo carga: leer cada hoja configurada y subir a Azure
        print("\n[2] Azure SQL: comprobando conexión…")
        engine = build_engine()
        if not smoke_test(engine):
            print("    SQL FAIL. Revisa AZURE_SQL_* en .env.")
            sys.exit(1)
        print("    SQL OK")

        print("\n[3] Cargando hojas → tablas")
        for sheet_name, rule in SHEET_RULES.items():
            if sheet_name not in sheet_names:
                print(f"    ⚠ Hoja '{sheet_name}' no existe en el Sheet; se omite.")
                continue
            header_row = rule.get("header_row", 0)
            expected_columns = rule.get("expected_columns")
            target_table = rule.get("target_table")
            if not target_table:
                print(f"    ⚠ {sheet_name}: falta 'target_table'; se omite.")
                continue
            try:
                df = sheet_to_dataframe(
                    spreadsheet,
                    sheet_name,
                    header_row=header_row,
                    expected_columns=expected_columns,
                )
                n = load_dataframe(engine, df, target_table, schema="dbo", if_exists="replace")
                print(f"    {sheet_name} → dbo.{target_table} ({n} filas)")
            except Exception as e:
                print(f"    ✗ {sheet_name} → {target_table}: {e}")
        print("\nListo.")
    else:
        # Modo perfil: mostrar resumen para que definas SHEET_RULES en config.py
        print("\n[2] Perfil de hojas (define SHEET_RULES en config.py para cargar a Azure)")
        rows = []
        for name in sheet_names:
            p = profile_sheet(spreadsheet, name)
            header_preview = ""
            if p.get("best_header"):
                h = p["best_header"][:6]
                header_preview = ", ".join(h) + ("..." if len(p["best_header"]) > 6 else "")
            rows.append([
                p["sheet_name"],
                p.get("non_empty_rows", 0),
                p.get("best_header_row"),
                header_preview,
                " | ".join(p.get("notes", [])),
            ])
        print(tabulate(
            rows,
            headers=["sheet", "non_empty_rows", "best_header_row", "best_header_preview", "notes"],
            tablefmt="github",
        ))
        print("\n[3] Azure SQL smoke test (opcional)")
        try:
            engine = build_engine()
            ok = smoke_test(engine)
            print("    SQL OK" if ok else "    SQL FAIL")
            tables = list_tables(engine, schema="dbo")
            print(tabulate(tables, headers=["schema", "table"], tablefmt="github"))
        except Exception as e:
            print(f"    No se pudo conectar: {e}")


if __name__ == "__main__":
    main()
