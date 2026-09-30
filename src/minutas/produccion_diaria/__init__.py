"""
Módulo de Producción diaria por turno (Minuta → ProduccionDiariaPorTurno).

Tabla Azure: ProduccionDiariaPorTurno
Columnas: Id_Maquina, Fecha, Turno, CantidadProducida

Layout V22: pendiente definir filas/columnas en el Excel.
"""
from .parser import (
    parse_produccion_diaria,
    ProduccionDiariaRow,
    ProduccionDiariaParseResult,
)

__all__ = ["parse_produccion_diaria", "ProduccionDiariaRow", "ProduccionDiariaParseResult"]
