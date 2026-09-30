# Siempre trabajamos con 2 archivos:
#   - MINUTA: "Minuta de reunion semanal EE4A 2026-01-28 v16 doble capsula.xlsx"
#             → parse_minuta: fecha, version
#   - PLAN:   "Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx"
#             → parse_plan: plan_id, version, fecha_desde, fecha_hasta
#
# --- Plan Excel: versión del layout ---
# Todo el parsing actual es para Plan V22. Si el archivo pasa a v23, columnas/filas pueden cambiar:
# entonces añadir PLAN_LAYOUT_V23 y usar plan_v23 o cambiar PLAN_VERSION.
PLAN_VERSION = "v22"

# --- Producción (por marca) — Layout V22 ---
# Columna B = Nombre (Marca + tipo Plan/Real). Columnas C-I = 7 días.
# Filas Excel 1-based.
PLAN_PRODUCCION = {
    "sheet_name": "Plan - Semanal",
    # Fila Excel (1-based) donde está el encabezado de fechas (Mon-26, Tue-27, ...)
    "fila_header_excel": 108,
    # Filas Excel (1-based) a parsear para Plan y Real. Cada tupla = (inicio, fin) inclusive.
    "filas_datos": [(109, 199), (212, 302)],
    # Referencia opcional: filas donde aparece cada marca (Excel 1-based). Solo documentación.
    "marca_filas": {
        "Mill Mint": (161, 169),
    },
}

# --- Azure SQL: tablas del Plan de Producción ---
# Nombres de tablas donde se insertan planificaciones y real.
AZURE_TABLA_PLANIFICACIONES = "ProduccionPlanificaciones"
AZURE_TABLA_REAL = "ProduccionReal"
# Comportamiento al cargar: "append" (añadir filas, mantener historial) o "replace" (reemplazar todo).
AZURE_PLAN_IF_EXISTS = "append"

# --- Minuta Excel: versión del layout (eficiencias) ---
# Layout V22: filas 68-84, velocidad 90-105, orden de máquinas fijo.
# En otras versiones pueden agregarse/quitarse máquinas o cambiar filas.
MINUTA_EFICIENCIA_VERSION = "v22"

# --- Azure SQL: tablas de Minuta (eficiencias) ---
AZURE_TABLA_RENDIMIENTO_REAL = "RendimientoReal"
AZURE_MINUTA_IF_EXISTS = "append"

# --- Azure SQL: tablas de Minuta (producción diaria por turno) ---
AZURE_TABLA_PRODUCCION_DIARIA_TURNO = "ProduccionDiariaPorTurno"

# --- Azure SQL: tablas de Minuta (rendimiento tabaco) ---
AZURE_TABLA_RENDIMIENTO_TABACO = "RendimientoTabaco"

# --- Minuta: celdas de tabaco por versión (alias → celda Excel) ---
# Cada minuta puede tener el tabaco en distintas celdas/hojas. Se usa la versión del nombre del archivo.
# Aliases: tabaco_consumo_teorico, tabaco_consumo_real
#
# use_excel_names: True = leer desde los nombres definidos en Excel (Name Manager).
#   Así, si agregan/quitan filas arriba, Excel actualiza la referencia y el script sigue funcionando.
#   Los nombres deben coincidir: tabaco_consumo_teorico, tabaco_consumo_real
#
# use_excel_names: False = usar celdas fijas (ej. B82, H82). sheet: opcional.
RENDIMIENTO_TABACO_CELLS = {
    "v22": {
        "sheet": "Datos crudos",
        "tabaco_consumo_teorico": "B83",
        "tabaco_consumo_real": "H83",
    },
    "v16": {
        "use_excel_names": True,
        # Fallback si no hay nombres en Excel (para compatibilidad):
        "sheet": "Minuta",
        "tabaco_consumo_teorico": "B82",
        "tabaco_consumo_real": "H82",
    },
    # Añadir más versiones según haga falta:
    # "v17": {"use_excel_names": True, "sheet": "Minuta", ...},
}

#
# Mapeo hoja de Excel/Sheet → tabla en Azure SQL (genérico).
# Por cada hoja que quieras cargar, define:
#   - header_row: fila 0-based donde está el encabezado
#   - expected_columns: (opcional) nombres de columnas en orden; si no, se usan las del sheet
#   - target_table: nombre de la tabla staging en Azure (ej. stg_minuta_ventas)
SHEET_RULES = {
    # Ejemplo:
    # "Ventas": {
    #     "header_row": 0,
    #     "expected_columns": ["Fecha", "Producto", "Cantidad", "Monto"],
    #     "target_table": "stg_ventas",
    # },
    # "Clientes": {
    #     "header_row": 0,
    #     "target_table": "stg_clientes",
    # },
}
