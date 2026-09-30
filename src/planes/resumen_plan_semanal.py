"""
Resumen Plan por marca (total semana + desglose por día).
Usa layout Plan V22; ver plan_v22 y config PLAN_VERSION.
"""
import sys
from pathlib import Path
from collections import defaultdict
from typing import Optional

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

from config import PLAN_PRODUCCION, PLAN_VERSION
from marcas import MARCAS
from planes.parse_plan import parse_plan_filename
from planes.plan_parser import PlanParseResult


def _agrupar_por_marca_y_fecha(filas: list, campo_cantidad: str) -> dict:
    """Agrupa filas por Id_Marca y Fecha. Devuelve { Id_Marca: { Fecha: cantidad, ... }, ... }."""
    por_marca = defaultdict(dict)
    for r in filas:
        mid = r.get("Id_Marca")
        f = r.get("Fecha")
        q = r.get(campo_cantidad) or 0
        if mid is not None and f:
            por_marca[mid][f] = por_marca[mid].get(f, 0) + q
    return dict(por_marca)


def resumen_texto(plan_path: str, sheet_name: Optional[str] = None) -> str:
    """Ejecuta parser (Plan V22) y devuelve texto con resumen por marca."""
    plan_info = parse_plan_filename(plan_path)
    if PLAN_VERSION == "v22":
        from planes.plan_v22 import parse_plan_produccion_v22
        result = parse_plan_produccion_v22(plan_path, plan_info, sheet_name=sheet_name)
    else:
        from planes.plan_parser import parse_plan_produccion
        cfg = PLAN_PRODUCCION
        result = parse_plan_produccion(
            plan_path,
            sheet_name or cfg.get("sheet_name", "Plan - Semanal"),
            plan_info,
            fila_header_excel=cfg.get("fila_header_excel", 108),
            filas_datos_excel=cfg.get("filas_datos"),
        )
    sheet = sheet_name or PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")
    if (len(result.planificaciones) == 0 and len(result.real) == 0) and result.errors:
        result.errors.append(
            f"Hoja: «{sheet}». Layout: Plan {PLAN_VERSION}. Revisa config.py si cambió la versión."
        )

    plan_por_marca = _agrupar_por_marca_y_fecha(result.planificaciones, "CantidadAProducir")
    real_por_marca = _agrupar_por_marca_y_fecha(result.real, "CantidadProducida")

    # Orden de fechas (todas las que aparezcan)
    todas_fechas = set()
    for d in plan_por_marca.values():
        todas_fechas.update(d.keys())
    for d in real_por_marca.values():
        todas_fechas.update(d.keys())
    fechas_ordenadas = sorted(todas_fechas)

    lineas = [
        f"# Resumen Plan Semanal — {plan_path}",
        f"  Layout: Plan {PLAN_VERSION}  |  Plan ID: {plan_info.plan_id}  |  Versión archivo: {plan_info.version}  |  {plan_info.fecha_desde} → {plan_info.fecha_hasta}",
        "",
    ]
    if result.errors:
        lineas.append("Errores:")
        for e in result.errors:
            lineas.append(f"  - {e}")
        lineas.append("")

    n_plan = len(result.planificaciones)
    n_real = len(result.real)
    lineas.append(f"Filas parseadas: Plan {n_plan}, Real {n_real}")
    lineas.append("")

    marcas_ids = sorted(set(plan_por_marca) | set(real_por_marca))
    if not marcas_ids:
        lineas.append("(No se encontraron marcas con datos. Revisa que la hoja y las filas 109-199 / 212-302 tengan texto en columna A terminado en 'Plan' o 'Real' / 'Real Total', y que la marca esté en marcas.py)")
        lineas.append("")
    for id_marca in marcas_ids:
        nombre = MARCAS.get(id_marca, f"Marca_{id_marca}")
        plan_dias = plan_por_marca.get(id_marca, {})
        real_dias = real_por_marca.get(id_marca, {})
        total_plan = sum(plan_dias.values())
        total_real = sum(real_dias.values())

        lineas.append(f"## {nombre} (Id {id_marca})")
        lineas.append(f"  Plan total semana:  {total_plan}")
        lineas.append(f"  Real total semana:  {total_real}")
        if fechas_ordenadas:
            lineas.append("  Plan por día:")
            for f in fechas_ordenadas:
                p = plan_dias.get(f, 0)
                lineas.append(f"    {f}: {p}")
            lineas.append("  Real por día:")
            for f in fechas_ordenadas:
                r = real_dias.get(f, 0)
                lineas.append(f"    {f}: {r}")
        lineas.append("")

    lineas.append("--- Fin del resumen ---")
    return "\n".join(lineas)


def resumen_para_email(plan_path: str, sheet_name: Optional[str] = None) -> str:
    """
    Igual que resumen_texto pero con formato más amigable para el cuerpo del email:
    sin markdown (##), con títulos claros y listas legibles.
    """
    plan_info = parse_plan_filename(plan_path)
    if PLAN_VERSION == "v22":
        from planes.plan_v22 import parse_plan_produccion_v22
        result = parse_plan_produccion_v22(plan_path, plan_info, sheet_name=sheet_name)
    else:
        from planes.plan_parser import parse_plan_produccion
        cfg = PLAN_PRODUCCION
        result = parse_plan_produccion(
            plan_path,
            sheet_name or cfg.get("sheet_name", "Plan - Semanal"),
            plan_info,
            fila_header_excel=cfg.get("fila_header_excel", 108),
            filas_datos_excel=cfg.get("filas_datos"),
        )
    sheet = sheet_name or PLAN_PRODUCCION.get("sheet_name", "Plan - Semanal")
    if (len(result.planificaciones) == 0 and len(result.real) == 0) and result.errors:
        result.errors.append(
            f"Hoja: «{sheet}». Layout: Plan {PLAN_VERSION}. Revisa config.py si cambió la versión."
        )

    plan_por_marca = _agrupar_por_marca_y_fecha(result.planificaciones, "CantidadAProducir")
    real_por_marca = _agrupar_por_marca_y_fecha(result.real, "CantidadProducida")
    todas_fechas = set()
    for d in plan_por_marca.values():
        todas_fechas.update(d.keys())
    for d in real_por_marca.values():
        todas_fechas.update(d.keys())
    fechas_ordenadas = sorted(todas_fechas)

    lineas = [
        f"Archivo: {plan_path}",
        f"Plan ID: {plan_info.plan_id}  |  Versión: {plan_info.version}  |  Período: {plan_info.fecha_desde} a {plan_info.fecha_hasta}",
        f"Layout: Plan {PLAN_VERSION}  |  Hoja: {sheet}",
        "",
        f"Filas procesadas: Plan {len(result.planificaciones)}, Real {len(result.real)}",
        "",
    ]
    if result.errors:
        lineas.append("Avisos del proceso:")
        for e in result.errors:
            lineas.append(f"  - {e}")
        lineas.append("")

    marcas_ids = sorted(set(plan_por_marca) | set(real_por_marca))
    if not marcas_ids:
        lineas.append("No se encontraron marcas con datos en el rango configurado.")
        lineas.append("")
    for id_marca in marcas_ids:
        nombre = MARCAS.get(id_marca, f"Marca {id_marca}")
        plan_dias = plan_por_marca.get(id_marca, {})
        real_dias = real_por_marca.get(id_marca, {})
        total_plan = sum(plan_dias.values())
        total_real = sum(real_dias.values())
        lineas.append(f"  {nombre} (Id {id_marca})")
        lineas.append(f"    Plan total semana:  {total_plan}")
        lineas.append(f"    Real total semana:  {total_real}")
        if fechas_ordenadas:
            lineas.append("    Plan por día:")
            for f in fechas_ordenadas:
                lineas.append(f"      {f}: {plan_dias.get(f, 0)}")
            lineas.append("    Real por día:")
            for f in fechas_ordenadas:
                lineas.append(f"      {f}: {real_dias.get(f, 0)}")
        lineas.append("")

    return "\n".join(lineas)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent.parent
    default_path = root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    path = sys.argv[1] if len(sys.argv) > 1 else str(default_path)
    sheet = sys.argv[2] if len(sys.argv) > 2 else None
    print(resumen_texto(path, sheet))
