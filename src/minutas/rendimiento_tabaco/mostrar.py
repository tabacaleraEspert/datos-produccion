"""
Muestra ConsumoTeoricoKg y ConsumoRealKg que se cargarían a RendimientoTabaco (sin cargar).

Lee B83 y H83 de la hoja "Datos crudos".

Uso: python src/minutas/rendimiento_tabaco/mostrar.py [ruta_minuta.xlsx]
"""
import sys
from pathlib import Path

_src_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_src_dir))

from config import RENDIMIENTO_TABACO_CELLS
from minutas.parse_minuta import parse_minuta_filename
from minutas.rendimiento_tabaco.parser import parse_rendimiento_tabaco


def main() -> int:
    root = Path(__file__).resolve().parent.parent.parent.parent
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        minutas = sorted(f for f in root.glob("*.xlsx") if "minuta" in f.name.lower() and not f.name.startswith("~$"))
        if not minutas:
            print("No hay Minuta en la raíz.")
            return 1
        path = str(minutas[0])
        print(f"Usando: {minutas[0].name}\n")

    info = parse_minuta_filename(path)
    if info.errors or not info.fecha:
        print("Errores:", info.errors or ["Falta fecha"])
        return 1

    result = parse_rendimiento_tabaco(path, info)
    version_key = (info.version or "").lower()
    cell_map = RENDIMIENTO_TABACO_CELLS.get(version_key, {})

    print("=" * 60)
    print("RENDIMIENTO TABACO (→ RendimientoTabaco)")
    print("=" * 60)
    print(f"Archivo: {path}")
    print(f"Versión: {info.version}")
    if cell_map.get("use_excel_names"):
        print("Origen: nombres Excel (tabaco_consumo_teorico, tabaco_consumo_real)")
    else:
        print(f"Celdas: {cell_map.get('tabaco_consumo_teorico', '?')} = teórico, {cell_map.get('tabaco_consumo_real', '?')} = real")
    print()

    if result.errors:
        print("Avisos:")
        for e in result.errors:
            print(f"  - {e}")
        print()

    if not result.fila:
        print("(No hay datos. B83 y H83 vacíos o no numéricos.)")
        return 0

    r = result.fila
    print("Fila que se insertaría:")
    print(f"  Fecha:              {r.fecha} (lunes de la semana anterior a la minuta)")
    print(f"  ConsumoTeoricoKg:   {r.consumo_teorico_kg}")
    print(f"  ConsumoRealKg:      {r.consumo_real_kg}")
    print()
    print("--- Fin ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
