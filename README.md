# datos-produccion

Procesa Excel (Plan de Producción, Minutas) y carga datos en Azure SQL.

---

## Tablas Azure

| Tabla | Origen | Columnas principales | Módulo |
|-------|--------|----------------------|--------|
| **ProduccionPlanificaciones** | Plan Excel | Id_Plan, Id_Marca, Fecha, CantidadAProducir | `planes/` |
| **ProduccionReal** | Plan Excel | Id_Plan, Id_Marca, Fecha, CantidadProducida | `planes/` |
| **RendimientoReal** | Minuta Excel | id_maquina, Fecha, Turno, Eficiencia, VelocidadDeseado, RendimientoDeseado | `minutas/eficiencia/` |
| **ProduccionDiariaPorTurno** | Minuta Excel | Id_Maquina, Fecha, Turno, CantidadProducida | `minutas/produccion_diaria/` |
| **RendimientoTabaco** | Minuta Excel | Fecha, ConsumoTeoricoKg, ConsumoRealKg | `minutas/rendimiento_tabaco/` |

Scripts SQL para crear tablas (si no existen): `sql/create_tables_plan.sql`, `sql/create_tables_rendimiento.sql`, `sql/create_tables_produccion_diaria.sql`, `sql/create_tables_rendimiento_tabaco.sql`.

---

## Versiones de layout

Todo el parsing actual usa **layout V22**. Si cambia el Excel (otra versión), hay que añadir el nuevo layout y elegirlo en `config.py`.

| Archivo | Versión | Dónde se define |
|---------|---------|------------------|
| Plan de Producción | **V22** | `config.PLAN_VERSION`, `planes/plan_v22.py` |
| Minuta (eficiencias) | **V22** | `config.MINUTA_EFICIENCIA_VERSION`, `minutas/eficiencia/parser.py` |
| Minuta (producción diaria) | **V22** | `minutas/produccion_diaria/parser.py` |
| Minuta (rendimiento tabaco) | **V22, V16, …** | `config.RENDIMIENTO_TABACO_CELLS` (alias: `tabaco_consumo_teorico`, `tabaco_consumo_real`) |

---

## Orden de máquinas (Minuta V22)

Las tablas **RendimientoReal** y **ProduccionDiariaPorTurno** usan **Id_Maquina**. Orden fijo en el Excel:

| Orden | Id_Maquina | Fila eficiencia (Excel) | Fila producción (Excel) |
|-------|------------|--------------------------|---------------------------|
| 1 | 1 | 68 | 5 |
| 2 | 2 | 69 | 10 |
| 3 | 13 | 70 | 15 |
| 4 | 3 | 71 | 20 |
| 5 | 4 | 72 | 22 |
| 6 | 6 | 73 | 24 |
| 7 | 15 | 74 | 26 |
| 8 | 8 | 75 | 28 |
| 9 | 7 | 76 | 30 |
| 10 | 16 | 77 | 33 |
| 11 | 9 | 78 | 35 |
| 12 | 5 | 79 | 37 |
| 13 | 17 | 80 | 40 |
| 14 | 10 | 82 | 45 |
| 15 | 14 | 83 | 51 |
| 16 | 18 | 84 | 57 |

*(Fila 81 en eficiencia está vacía.)*

Velocidad deseada (eficiencia): columna C, filas 90–105 (mismo orden).  
Rendimiento deseado (eficiencia): valores fijos por Id_Maquina (67, 67, 67, 65, 65, 70, …) en `minutas/eficiencia/parser.py`.

---

## Marcas (Plan V22)

Las tablas **ProduccionPlanificaciones** y **ProduccionReal** usan **Id_Marca**. En V22 se leen estas 14 marcas (mapeo filas en `planes/plan_v22.py`):

| Id_Marca | Marca | Filas Plan (Excel) | Filas Real (Excel) |
|----------|--------|---------------------|---------------------|
| 6 | MelbourneRed | 109, 111 | 113, 115 |
| 7 | MelbourneGold | 122, 124 | 126, 128 |
| 8 | MelbourneMint | 135, 137 | 139, 141 |
| 13 | Mill | 148, 150 | 152, 154 |
| 50 | MillMint | 161, 163 | 165, 167 |
| 14 | BoldRed | 174, 176 | 178, 180 |
| 15 | BoldMint | 187, 189 | 191, 193 |
| 9 | MilenioRed | 212, 214 | 216, 218 |
| 10 | MilenioGold | 225, 227 | 229, 231 |
| 11 | MilenioMint | 238, 240 | 242, 244 |
| 12 | MilenioClick | 251, 253 | 255, 257 |
| 20 | MilenioVid | 264, 266 | 268, 270 |
| 19 | MilenioPink | 277, 279 | 281, 283 |
| 17 | MillExplosion | 290, 292 | 294, 296 |

Lista completa Id_Marca ↔ nombre en `src/marcas.py`.

---

## Comandos (desde la raíz del repo)

### Plan de Producción

```bash
# Cargar Plan a Azure
python src/planes/carga_plan_azure.py [ruta_plan.xlsx] [hoja]

# Cargar todos los Plan de una carpeta (por defecto: planes/)
python src/planes/carga_carpeta_planes.py [carpeta]

# Vista previa (qué se enviaría a Azure)
python src/planes/mostrar_real.py [ruta_plan.xlsx]

# Resumen por marca
python src/planes/resumen_plan_semanal.py [ruta_plan.xlsx] [hoja]

# Reporte para email (reporte_email.txt)
python src/planes/reporte_para_mail.py [ruta_plan.xlsx] [hoja] [archivo_salida]

# Diagnóstico / inspección
python src/planes/report_rangos_marcas.py [ruta_plan.xlsx]
python src/planes/diagnostico_plan.py [ruta_plan.xlsx]
python src/planes/inspect_plan.py [ruta_plan.xlsx]

# Parse del nombre del archivo Plan
python src/planes/parse_plan.py [ruta_plan.xlsx]
```

### Minuta (común)

```bash
# Parse del nombre (fecha, versión)
python src/minutas/parse_minuta.py [ruta_minuta.xlsx]

# Reporte para email (reporte_minuta_email.txt)
python src/minutas/reporte_minuta_para_mail.py [ruta_minuta.xlsx] [archivo_salida]
```

### Minuta — Eficiencias (RendimientoReal)

```bash
python src/minutas/eficiencia/mostrar.py [ruta_minuta.xlsx]
python src/minutas/eficiencia/carga_azure.py [ruta_minuta.xlsx] [hoja]
```

### Minuta — Producción diaria por turno (ProduccionDiariaPorTurno)

```bash
python src/minutas/produccion_diaria/mostrar.py [ruta_minuta.xlsx]
python src/minutas/produccion_diaria/carga_azure.py [ruta_minuta.xlsx] [hoja]
```

### Minuta — Rendimiento tabaco (RendimientoTabaco)

```bash
# Vista previa (B83, H83 → ConsumoTeoricoKg, ConsumoRealKg)
python src/minutas/rendimiento_tabaco/mostrar.py [ruta_minuta.xlsx]

# Cargar a Azure
python src/minutas/rendimiento_tabaco/carga_azure.py [ruta_minuta.xlsx] [hoja]
```

---

## Estructura del repo

```
src/
├── config.py          # PLAN_VERSION, MINUTA_EFICIENCIA_VERSION, tablas Azure
├── db.py              # Conexión y carga a Azure
├── marcas.py          # Id_Marca ↔ nombre (Plan)
├── run_summary.py     # Resumen de ejecución (emails)
├── planes/            # Plan Excel → ProduccionPlanificaciones, ProduccionReal
│   ├── plan_v22.py    # Layout V22, mapeo Id_Marca → filas
│   ├── carga_plan_azure.py
│   ├── mostrar_real.py
│   └── ...
└── minutas/
    ├── parse_minuta.py
    ├── reporte_minuta_para_mail.py
    ├── eficiencia/    # → RendimientoReal
    │   ├── parser.py  # Layout V22: filas 68-84, 90-105
    │   ├── carga_azure.py
    │   └── mostrar.py
    ├── produccion_diaria/  # → ProduccionDiariaPorTurno
    │   ├── parser.py  # Layout V22: filas 5, 10, 15, …
    │   ├── carga_azure.py
    │   └── mostrar.py
    └── rendimiento_tabaco/  # → RendimientoTabaco
        ├── parser.py  # Layout V22: B83, H83
        ├── carga_azure.py
        └── mostrar.py
```

---

## Requisitos

- Python 3.11 o 3.12 (recomendado para pyodbc)
- `.env` con `AZURE_SQL_SERVER`, `AZURE_SQL_DB`, `AZURE_SQL_USER`, `AZURE_SQL_PASSWORD`
- `pip install -r requirements-azure.txt`
- Tablas creadas en Azure (scripts en `sql/`)

Ver `AZURE_SETUP.md` para más detalle.

---

## Formato UNIFICADO (ago-2026+)

Desde ~Plan 281 (27-jul-2026) el Excel es UNO solo ("Plan NNN ... (Villafranca-Ale)")
con hojas `Minuta` + `Datos crudos` + `Plan - Semanal` + `REND.TABACO` — reemplaza
al par Plan+Minuta. Parser: `src/unificado.py` · carga: `src/carga_unificado.py`
(idempotente por semana, borra y recarga lunes..domingo).

```bash
# bajar los "Plan NNN (Villafranca-Ale)" del Drive a planes-unificados/ y:
DYLD_LIBRARY_PATH=/opt/homebrew/opt/openssl@3/lib \
  python src/carga_unificado.py planes-unificados/
```

Notas del formato: bloques de 13 filas por marca en Plan-Semanal (plan +0..+3,
real +4..+7, fila Total para validar), eficiencias con "[obj% @ vel]" en el
label (fracción 0-1, solo TD/TJ), tabaco Teórico B / Real H, Datos crudos en
tríos TD/TJ/TN por día. Semanas cortas: la fecha ancla es el LUNES calendario.
Backfill feb→jul 2026 (minutas v15/v16 separadas): PENDIENTE.
