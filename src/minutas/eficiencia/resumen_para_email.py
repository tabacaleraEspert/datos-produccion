"""
Resumen de eficiencias para el cuerpo del email.
"""
from collections import defaultdict
from typing import Optional

from ..parse_minuta import parse_minuta_filename
from .parser import parse_minuta_eficiencia


def resumen_para_email(minuta_path: str, sheet_name: Optional[str] = None) -> str:
    """Genera un resumen de eficiencias por máquina, formato amigable para email."""
    info = parse_minuta_filename(minuta_path)
    result = parse_minuta_eficiencia(minuta_path, info, sheet_name=sheet_name)

    lineas = [
        f"Archivo: {minuta_path}",
        f"Fecha reunión: {info.fecha}  |  Versión: {info.version}",
        f"Semana de datos: lunes a domingo anterior a la reunión",
        "",
        f"Filas a insertar en RendimientoReal: {len(result.filas)}",
        "",
    ]
    if result.errors:
        lineas.append("Avisos:")
        for e in result.errors:
            lineas.append(f"  - {e}")
        lineas.append("")

    if not result.filas:
        lineas.append("No hay filas con eficiencia numérica (solo valores 'N').")
        return "\n".join(lineas)

    por_maquina = defaultdict(list)
    for r in result.filas:
        por_maquina[r.id_maquina].append((r.fecha, r.turno, r.eficiencia))

    for id_m in sorted(por_maquina.keys()):
        filas = por_maquina[id_m]
        r0 = next(r for r in result.filas if r.id_maquina == id_m)
        lineas.append(f"  Máquina {id_m}: {len(filas)} registros")
        if r0.rendimiento_deseado is not None:
            lineas.append(f"    Rendimiento deseado: {r0.rendimiento_deseado}%")
        if r0.velocidad_deseado is not None:
            lineas.append(f"    Velocidad deseada: {r0.velocidad_deseado}")
        prom = sum(e for _, _, e in filas) / len(filas)
        lineas.append(f"    Eficiencia promedio: {prom:.1f}%")
        for fecha, turno, eff in sorted(filas)[:7]:
            lineas.append(f"      {fecha} {turno}: {eff}%")
        if len(filas) > 7:
            lineas.append(f"      ... y {len(filas) - 7} más")
        lineas.append("")

    return "\n".join(lineas)
