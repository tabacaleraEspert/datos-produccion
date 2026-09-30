"""
Procesa todos los archivos Plan de una carpeta: parsea cada Excel y sube a Azure.

Uso:
  python src/planes/carga_carpeta_planes.py [carpeta]

  - carpeta: ruta a la carpeta con los .xlsx de Plan (por defecto: planes/ en la raíz del repo).
  - Solo se procesan archivos .xlsx cuyo nombre contiene "Plan" (insensible a mayúsculas).
  - Si un archivo falla, se anota y se sigue con el siguiente.
"""
import sys
from pathlib import Path

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

from dotenv import load_dotenv
load_dotenv(_src_dir.parent / ".env")

from db import build_engine, smoke_test
from run_summary import RunSummary
from planes.carga_plan_azure import process_one_plan_file


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    default_carpeta = root / "planes"
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else default_carpeta

    if not carpeta.is_dir():
        print(f"Error: no es una carpeta o no existe: {carpeta}", file=sys.stderr)
        return 1

    # Solo .xlsx que tengan "Plan" en el nombre
    archivos = sorted(
        f for f in carpeta.glob("*.xlsx")
        if "plan" in f.name.lower() and not f.name.startswith("~$")
    )
    if not archivos:
        print(f"No se encontraron archivos Plan (.xlsx con 'Plan' en el nombre) en: {carpeta}")
        return 0

    summary = RunSummary(title=f"Carga carpeta: {carpeta.name} ({len(archivos)} archivos)")

    try:
        engine = build_engine()
        if not smoke_test(engine):
            raise RuntimeError("Conexión a Azure SQL falló. Revisa AZURE_SQL_* en .env.")
    except Exception as e:
        summary.add_step(
            "Conexión a Azure SQL",
            success=False,
            errors=[f"{type(e).__name__}: {e}"],
        )
        print(summary.to_text(), file=sys.stderr)
        return 1

    summary.add_step("Conexión a Azure SQL", success=True, messages=["Conexión OK"])

    for plan_path in archivos:
        nombre = plan_path.name
        success, n_plan, n_real, errors = process_one_plan_file(str(plan_path), None, engine)
        if success:
            summary.add_step(
                nombre,
                success=True,
                messages=[f"Plan: {n_plan} filas | Real: {n_real} filas"],
                data={"plan": n_plan, "real": n_real},
            )
        else:
            summary.add_step(
                nombre,
                success=False,
                errors=errors,
                data={"plan": n_plan, "real": n_real} if (n_plan or n_real) else None,
            )

    print(summary.to_text())
    if not summary.success:
        print("\n(Algunos archivos fallaron; revisa los marcados con ✗ arriba.)")
    return 0 if summary.success else 1


if __name__ == "__main__":
    sys.exit(main())
