"""
Genera el reporte para enviar por correo: escribe en un archivo de texto
todos los resultados de forma amigable y captura errores para incluirlos en el mail.

Uso:
  python src/planes/reporte_para_mail.py [ruta_plan.xlsx] [hoja] [archivo_salida]

  - ruta_plan.xlsx: archivo Plan Excel (por defecto: Plan en la raíz del repo).
  - hoja: opcional; nombre de la hoja a leer.
  - archivo_salida: opcional; donde guardar el texto (por defecto: reporte_email.txt en la raíz).
"""
import sys
import traceback
from pathlib import Path
from datetime import datetime

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

from run_summary import RunSummary
from planes.parse_plan import parse_plan_filename
from planes.resumen_plan_semanal import resumen_para_email


def _error_descriptivo(exc: BaseException) -> str:
    """Genera un mensaje de error descriptivo a partir de una excepción."""
    tipo = type(exc).__name__
    msg = str(exc) if str(exc) else "(sin mensaje)"
    return f"{tipo}: {msg}"


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    default_plan = root / "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
    default_salida = root / "reporte_email.txt"

    plan_path = sys.argv[1] if len(sys.argv) > 1 else str(default_plan)
    sheet_name = sys.argv[2] if len(sys.argv) > 2 else None
    out_path = sys.argv[3] if len(sys.argv) > 3 else str(default_salida)

    # Título del reporte (nombre del archivo o "Plan de Producción")
    titulo = Path(plan_path).name if plan_path else "Plan de Producción"
    summary = RunSummary(title=titulo)

    # ----- Paso 1: Parse del nombre del archivo -----
    try:
        plan_info = parse_plan_filename(plan_path)
        if plan_info.errors:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=False,
                errors=plan_info.errors,
                data={
                    "archivo": plan_path,
                    "plan_id": plan_info.plan_id,
                    "versión": plan_info.version,
                    "período": f"{plan_info.fecha_desde} a {plan_info.fecha_hasta}" if plan_info.fecha_desde else None,
                },
            )
        else:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=True,
                messages=[f"Plan ID: {plan_info.plan_id}", f"Versión: {plan_info.version}", f"Período: {plan_info.fecha_desde} a {plan_info.fecha_hasta}"],
                data={"archivo": plan_path},
            )
    except Exception as e:
        summary.add_step(
            "Lectura del nombre del archivo",
            success=False,
            errors=[_error_descriptivo(e), traceback.format_exc()],
            data={"archivo": plan_path},
        )

    # ----- Paso 2: Parse del Plan y resumen por marca -----
    cuerpo_extra = ""
    try:
        if not Path(plan_path).exists():
            raise FileNotFoundError(f"No se encontró el archivo: {plan_path}")
        cuerpo_extra = resumen_para_email(plan_path, sheet_name)
        summary.add_step(
            "Procesamiento del Plan (resumen por marca)",
            success=True,
            messages=["Resumen generado correctamente."],
            data={"hoja": sheet_name or "Plan - Semanal"},
        )
    except FileNotFoundError as e:
        summary.add_step(
            "Procesamiento del Plan (resumen por marca)",
            success=False,
            errors=[_error_descriptivo(e)],
            data={"archivo": plan_path},
        )
    except Exception as e:
        summary.add_step(
            "Procesamiento del Plan (resumen por marca)",
            success=False,
            errors=[
                _error_descriptivo(e),
                "Detalle técnico: " + traceback.format_exc().replace("\n", " | ")[:500],
            ],
            data={"archivo": plan_path, "hoja": sheet_name or "(por defecto)"},
        )
        cuerpo_extra = "(No se pudo generar el resumen por marca debido a un error. Revisa la sección de errores más abajo.)"

    # ----- Paso 3: Escribir archivo para el mail -----
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        summary.add_step(
            "Escritura del archivo de reporte",
            success=True,
            messages=[f"Archivo generado: {out_path}"],
            data={"archivo_salida": out_path},
        )
        texto_email = summary.to_email_text(cuerpo_extra=cuerpo_extra)
        Path(out_path).write_text(texto_email, encoding="utf-8")
        print(f"Reporte escrito en: {out_path}")
    except Exception as e:
        print(f"Error al escribir el archivo {out_path}: {e}", file=sys.stderr)
        summary.add_step(
            "Escritura del archivo de reporte",
            success=False,
            errors=[_error_descriptivo(e)],
            data={"archivo_salida": out_path},
        )
        # Regenerar contenido incluyendo este error y volver a intentar escribir
        texto_email = summary.to_email_text(cuerpo_extra=cuerpo_extra)
        try:
            Path(out_path).write_text(texto_email, encoding="utf-8")
            print(f"Se guardó el reporte (con el error de escritura anotado) en: {out_path}")
        except Exception:
            pass
        return 1

    return 0 if summary.success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # Cualquier error no capturado: lo mostramos y salimos con error
        print(f"Error inesperado: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
