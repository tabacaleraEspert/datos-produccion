"""
Módulo de Eficiencias de máquinas (Minuta → RendimientoReal).

Tabla Azure: RendimientoReal

Layout V22: filas, orden de máquinas y valores fijos son específicos de esta versión.
En otras versiones de la minuta pueden agregarse/quitarse máquinas o cambiar filas.
"""
from .parser import (
    parse_minuta_eficiencia,
    EficienciaRow,
    EficienciaParseResult,
)

__all__ = ["parse_minuta_eficiencia", "EficienciaRow", "EficienciaParseResult"]
