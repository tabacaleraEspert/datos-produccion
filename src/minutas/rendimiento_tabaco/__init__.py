"""
Módulo de Rendimiento Tabaco (Minuta → RendimientoTabaco).

Tabla Azure: RendimientoTabaco
Columnas: fecha, ConsumoTeoricoKg, ConsumoRealKg

Layout V22: B83 = ConsumoTeoricoTabaco, H83 = ConsumoRealTabaco
"""
from .parser import parse_rendimiento_tabaco, RendimientoTabacoRow

__all__ = ["parse_rendimiento_tabaco", "RendimientoTabacoRow"]
