"""
Genera el reporte de Minuta para enviar por correo: escribe en un archivo de texto
el resumen de eficiencias y el resultado de la carga (si se ejecutó).

Uso:
  python src/minutas/reporte_minuta_para_mail.py [ruta_minuta.xlsx] [archivo_salida]

  - ruta_minuta.xlsx: archivo Minuta Excel (por defecto: Minuta en la raíz).
  - archivo_salida: opcional; donde guardar (por defecto: reporte_minuta_email.txt).
"""
import sys
import traceback
from pathlib import Path

_src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_src_dir))

from run_summary import RunSummary
from minutas.parse_minuta import parse_minuta_filename
from minutas.eficiencia.resumen_para_email import resumen_para_email


def _error_descriptivo(exc: BaseException) -> str:
    tipo = type(exc).__name__
    msg = str(exc) if str(exc) else "(sin mensaje)"
    return f"{tipo}: {msg}"


def _to_email_text_minuta(summary: RunSummary, cuerpo_extra: str) -> str:
    """Texto para email, adaptado a Minuta."""
    lines = [
        "Hola,",
        "",
        "Te envío el resumen de la Minuta (eficiencias de máquinas).",
        "",
        f"  {summary.title}",
        f"  Fecha de ejecución: {summary.started_at.strftime('%d/%m/%Y %H:%M')}",
        "",
        "RESUMEN DE PASOS",
        "-----------------",
    ]
    for i, step in enumerate(summary.steps, 1):
        icon = "✓ OK" if step.success else "✗ ERROR"
        lines.append(f"  {i}. {step.name}: {icon}")
        for msg in step.messages:
            lines.append(f"     {msg}")
        if step.data:
            for k, v in step.data.items():
                lines.append(f"     {k}: {v}")
        lines.append("")
    if cuerpo_extra:
        lines.append("DETALLE POR MÁQUINA (Eficiencias)")
        lines.append("-------------------------------")
        lines.append("")
        lines.append(cuerpo_extra.strip())
        lines.append("")
    all_errors = []
    for step in summary.steps:
        for err in step.errors:
            all_errors.append(f"  • [{step.name}] {err}")
    if all_errors:
        lines.append("ERRORES DETECTADOS")
        lines.append("------------------")
        lines.append("")
        for err in all_errors:
            lines.append(err)
        lines.append("")
    lines.append("-----------------")
    lines.append("Saludos.")
    return "\n".join(lines)


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent
    minutas = sorted(
        f for f in root.glob("*.xlsx")
        if "minuta" in f.name.lower() and not f.name.startswith("~$")
    )
    default_minuta = str(minutas[0]) if minutas else str(root / "Minuta.xlsx")
    default_salida = root / "reporte_minuta_email.txt"

    minuta_path = sys.argv[1] if len(sys.argv) > 1 else default_minuta
    out_path = sys.argv[2] if len(sys.argv) > 2 else str(default_salida)

    titulo = Path(minuta_path).name if minuta_path else "Minuta"
    summary = RunSummary(title=titulo)

    # ----- Paso 1: Parse del nombre -----
    try:
        info = parse_minuta_filename(minuta_path)
        if info.errors:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=False,
                errors=info.errors,
                data={"archivo": minuta_path},
            )
        else:
            summary.add_step(
                "Lectura del nombre del archivo",
                success=True,
                messages=[f"Fecha: {info.fecha}", f"Versión: {info.version}"],
                data={"archivo": minuta_path},
            )
    except Exception as e:
        summary.add_step(
            "Lectura del nombre del archivo",
            success=False,
            errors=[_error_descriptivo(e), traceback.format_exc()],
            data={"archivo": minuta_path},
        )

    # ----- Paso 2: Resumen de eficiencias -----
    cuerpo_extra = ""
    try:
        if not Path(minuta_path).exists():
            raise FileNotFoundError(f"No se encontró el archivo: {minuta_path}")
        cuerpo_extra = resumen_para_email(minuta_path)
        summary.add_step(
            "Procesamiento de eficiencias (Datos crudos)",
            success=True,
            messages=["Resumen generado correctamente."],
            data={"hoja": "Datos crudos"},
        )
    except FileNotFoundError as e:
        summary.add_step(
            "Procesamiento de eficiencias",
            success=False,
            errors=[_error_descriptivo(e)],
            data={"archivo": minuta_path},
        )
    except Exception as e:
        summary.add_step(
            "Procesamiento de eficiencias",
            success=False,
            errors=[
                _error_descriptivo(e),
                "Detalle: " + traceback.format_exc().replace("\n", " | ")[:500],
            ],
            data={"archivo": minuta_path},
        )
        cuerpo_extra = "(No se pudo generar el resumen debido a un error.)"

    # ----- Paso 3: Escribir archivo -----
    try:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        summary.add_step(
            "Escritura del archivo de reporte",
            success=True,
            messages=[f"Archivo generado: {out_path}"],
            data={"archivo_salida": out_path},
        )
        texto = _to_email_text_minuta(summary, cuerpo_extra)
        Path(out_path).write_text(texto, encoding="utf-8")
        print(f"Reporte escrito en: {out_path}")
    except Exception as e:
        print(f"Error al escribir {out_path}: {e}", file=sys.stderr)
        summary.add_step(
            "Escritura del archivo de reporte",
            success=False,
            errors=[_error_descriptivo(e)],
            data={"archivo_salida": out_path},
        )
        texto = _to_email_text_minuta(summary, cuerpo_extra)
        try:
            Path(out_path).write_text(texto, encoding="utf-8")
            print(f"Se guardó (con error anotado) en: {out_path}")
        except Exception:
            pass
        return 1

    return 0 if summary.success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"Error inesperado: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
