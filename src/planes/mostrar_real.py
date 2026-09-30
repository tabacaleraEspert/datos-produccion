"""
Muestra exactamente qué filas se envían a ProduccionReal (y a ProduccionPlanificaciones).

Sirve para revisar si el parser está tomando bien los datos del Excel.

Uso (desde la raíz del repo):
  python src/planes/mostrar_real.py [ruta_plan.xlsx]

  Sin argumentos usa el primer Plan .xlsx que encuentre en la raíz.
"""
import sys
from pathlib import Path
from collections import defaultdict

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

from config import PLAN_VERSION, PLAN_PRODUCCION
from planes.parse_plan import parse_plan_filename
from marcas import MARCAS


def main():
    root = Path(__file__).resolve().parent.parent.parent
    if len(sys.argv) > 1:
        plan_path = sys.argv[1]
    else:
        planes = sorted(
            f for f in root.glob("*.xlsx")
            if "plan" in f.name.lower() and not f.name.startswith("~$")
        )
        if not planes:
            print("No hay archivo Plan en la raíz. Uso: python src/planes/mostrar_real.py [ruta_plan.xlsx]")
            return 1
        plan_path = str(planes[0])
        print(f"Usando: {planes[0].name}\n")

    plan_info = parse_plan_filename(plan_path)
    if plan_info.errors or not plan_info.fecha_desde:
        print("Errores en el nombre del archivo:")
        for e in plan_info.errors or []:
            print(f"  - {e}")
        return 1

    if PLAN_VERSION == "v22":
        from planes.plan_v22 import parse_plan_produccion_v22
        result = parse_plan_produccion_v22(plan_path, plan_info, sheet_name=None)
    else:
        from planes.plan_parser import parse_plan_produccion
        result = parse_plan_produccion(
            plan_path,
            PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal"),
            plan_info,
            fila_header_excel=PLAN_PRODUCCION.get("fila_header_excel", 108),
            filas_datos_excel=PLAN_PRODUCCION.get("filas_datos"),
        )

    # Mismo filtro que carga_plan_azure: no insertar 0
    real_ok = [r for r in result.real if (r.get("CantidadProducida") or 0) != 0]
    plan_ok = [r for r in result.planificaciones if (r.get("CantidadAProducir") or 0) != 0]

    print("=" * 70)
    print("PRODUCCIÓN REAL (lo que se envía a Azure → ProduccionReal)")
    print("=" * 70)
    print(f"Archivo: {plan_path}")
    print(f"Período: {plan_info.fecha_desde} a {plan_info.fecha_hasta}")
    print(f"Total filas que se insertarían: {len(real_ok)} (filas con CantidadProducida=0 no se insertan)")
    print(f"Filas descartadas (CantidadProducida=0): {len(result.real) - len(real_ok)}")
    if result.errors:
        print("Avisos del parser:")
        for e in result.errors:
            print(f"  - {e}")
    print()

    if not real_ok:
        print("(No hay filas Real con cantidad > 0)")
        print()
    else:
        # Agrupar por Id_Marca para mostrar ordenado
        por_marca = defaultdict(list)
        for r in real_ok:
            mid = r.get("Id_Marca")
            por_marca[mid].append((r.get("Fecha"), r.get("CantidadProducida", 0)))
        for mid in sorted(por_marca.keys()):
            nombre = MARCAS.get(mid, f"Id_{mid}")
            filas = por_marca[mid]
            total = sum(q for _, q in filas)
            print(f"  {nombre} (Id_Marca {mid}): total Real = {total}")
            for fecha, qty in sorted(filas):
                print(f"    {fecha}  →  CantidadProducida: {qty}")
            print()

    print("=" * 70)
    print("PLANIFICACIONES (lo que se envía a Azure → ProduccionPlanificaciones)")
    print("=" * 70)
    print(f"Total filas que se insertarían: {len(plan_ok)} (filas con CantidadAProducir=0 no se insertan)")
    print(f"Filas descartadas (CantidadAProducir=0): {len(result.planificaciones) - len(plan_ok)}")
    print()

    if not plan_ok:
        print("(No hay filas Plan con cantidad > 0)")
    else:
        por_marca_plan = defaultdict(list)
        for r in plan_ok:
            mid = r.get("Id_Marca")
            por_marca_plan[mid].append((r.get("Fecha"), r.get("CantidadAProducir", 0)))
        for mid in sorted(por_marca_plan.keys()):
            nombre = MARCAS.get(mid, f"Id_{mid}")
            filas = por_marca_plan[mid]
            total = sum(q for _, q in filas)
            print(f"  {nombre} (Id_Marca {mid}): total Plan = {total}")
            for fecha, qty in sorted(filas)[:7]:
                print(f"    {fecha}  →  CantidadAProducir: {qty}")
            if len(filas) > 7:
                print(f"    ... y {len(filas) - 7} días más")
            print()

    print("--- Fin ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
