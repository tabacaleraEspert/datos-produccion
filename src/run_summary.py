"""
Resumen de la ejecución: recoge lo que pasó en cada paso para poder
generar un reporte descriptivo (ej. para enviar por email).
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StepEntry:
    """Una entrada del resumen: un paso de la ejecución."""
    name: str
    success: bool
    messages: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    data: Optional[Dict[str, Any]] = None  # datos extra (ej. fecha, versión, filas cargadas)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class RunSummary:
    """
    Resumen de una ejecución: título, pasos y método para generar texto/email.

    Uso:
        summary = RunSummary(title="Minuta 2026-01-28 v16")
        summary.add_step("parse_filename", success=True, data={"fecha": "2026-01-28", "version": "v16"})
        summary.add_step("carga_hoja_X", success=False, errors=["Timeout"])
        print(summary.to_text())
    """

    def __init__(self, title: str = ""):
        self.title = title or f"Ejecución {datetime.now().isoformat(timespec='seconds')}"
        self.steps: List[StepEntry] = []
        self.started_at = datetime.now()

    def add_step(
        self,
        name: str,
        success: bool,
        messages: Optional[List[str]] = None,
        errors: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
    ) -> None:
        """Añade un paso al resumen."""
        self.steps.append(
            StepEntry(
                name=name,
                success=success,
                messages=messages or [],
                errors=errors or [],
                data=data,
                started_at=started_at,
                ended_at=ended_at,
            )
        )

    def to_text(self) -> str:
        """Genera un texto plano para el cuerpo del email (o log)."""
        lines = [
            f"=== {self.title} ===",
            f"Inicio: {self.started_at.isoformat(timespec='seconds')}",
            "",
        ]
        for step in self.steps:
            icon = "✓" if step.success else "✗"
            lines.append(f"  {icon} {step.name}")
            for msg in step.messages:
                lines.append(f"      {msg}")
            for err in step.errors:
                lines.append(f"      ERROR: {err}")
            if step.data:
                for k, v in step.data.items():
                    lines.append(f"      {k}: {v}")
            lines.append("")
        lines.append("--- Fin del resumen ---")
        return "\n".join(lines)

    def to_html(self) -> str:
        """Genera HTML básico para email (opcional, para más adelante)."""
        parts = [
            f"<h2>{self.title}</h2>",
            f"<p>Inicio: {self.started_at.isoformat(timespec='seconds')}</p>",
            "<ul>",
        ]
        for step in self.steps:
            status = "OK" if step.success else "ERROR"
            parts.append(f"<li><strong>{step.name}</strong> [{status}]</li>")
            if step.errors:
                parts.append("<ul>")
                for err in step.errors:
                    parts.append(f"<li>{err}</li>")
                parts.append("</ul>")
            if step.data:
                parts.append("<ul>")
                for k, v in step.data.items():
                    parts.append(f"<li>{k}: {v}</li>")
                parts.append("</ul>")
        parts.append("</ul>")
        parts.append("<p>--- Fin del resumen ---</p>")
        return "\n".join(parts)

    @property
    def success(self) -> bool:
        """True si todos los pasos fueron exitosos."""
        return all(s.success for s in self.steps)

    def to_email_text(self, cuerpo_extra: Optional[str] = None) -> str:
        """
        Genera un texto amigable para el cuerpo del email: saludo, resumen de pasos,
        cuerpo extra (ej. resumen por marca), errores si los hay, y cierre.
        """
        lines = [
            "Hola,",
            "",
            "Te envío el resumen de la ejecución del Plan de Producción.",
            "",
            f"  {self.title}",
            f"  Fecha de ejecución: {self.started_at.strftime('%d/%m/%Y %H:%M')}",
            "",
            "RESUMEN DE PASOS",
            "-----------------",
        ]
        for i, step in enumerate(self.steps, 1):
            icon = "✓ OK" if step.success else "✗ ERROR"
            lines.append(f"  {i}. {step.name}: {icon}")
            for msg in step.messages:
                lines.append(f"     {msg}")
            if step.data:
                for k, v in step.data.items():
                    lines.append(f"     {k}: {v}")
            lines.append("")
        if cuerpo_extra:
            lines.append("DETALLE POR MARCA (Plan / Real)")
            lines.append("-------------------------------")
            lines.append("")
            lines.append(cuerpo_extra.strip())
            lines.append("")
        all_errors = []
        for step in self.steps:
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
