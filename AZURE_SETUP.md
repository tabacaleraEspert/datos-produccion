# Inserción a Azure SQL (Plan de Producción)

## Qué tenés que pasar

### 1. Variables de entorno (`.env` en la raíz del repo)

En el archivo `.env` tenés que definir las credenciales de Azure SQL. Sin esto la carga falla.

| Variable | Descripción | Ejemplo |
|----------|-------------|--------|
| `AZURE_SQL_SERVER` | Servidor (host) de Azure SQL | `mi-server.database.windows.net` |
| `AZURE_SQL_DB` | Nombre de la base de datos | `Produccion` |
| `AZURE_SQL_USER` | Usuario de la base | `admin@mi-server` o el usuario que te den |
| `AZURE_SQL_PASSWORD` | Contraseña del usuario | `********` |
| `AZURE_SQL_DRIVER` | Driver ODBC (opcional) | `ODBC Driver 18 for SQL Server` (por defecto) |
| `AZURE_SQL_ENCRYPT` | Encriptación (opcional) | `yes` (por defecto) |
| `AZURE_SQL_TRUST_CERT` | Confiar en certificado (opcional) | `no` (por defecto) |

**Mínimo obligatorio:** `AZURE_SQL_SERVER`, `AZURE_SQL_DB`, `AZURE_SQL_USER`, `AZURE_SQL_PASSWORD`.

### 2. Driver ODBC en tu máquina

En Windows/Mac tenés que tener instalado un driver ODBC para SQL Server, por ejemplo **ODBC Driver 18 for SQL Server**. Si no lo tenés:

- **Windows:** [Descargar Microsoft ODBC Driver for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)
- **macOS:** `brew install msodbcsql18` (o la versión que corresponda)

### 3. Dependencia Python (pyodbc)

La conexión a Azure SQL usa `pyodbc`. En Python 3.13 suele dar problemas de compilación; se recomienda Python 3.11 o 3.12.

```bash
pip install -r requirements-azure.txt
```

### 4. Tablas en Azure

Las tablas `ProduccionPlanificaciones` y `ProduccionReal` tienen que existir en la base. Si todavía no las creaste, ejecutá en Azure (Azure Data Studio, SSMS o el portal) el script:

```
sql/create_tables_plan.sql
```

Ese script crea las tablas en el schema `dbo` si no existen.

---

## Cómo ejecutar la carga

Desde la raíz del repo (con el venv activado y `.env` configurado):

```bash
# Plan por defecto (archivo en la raíz) → inserta en Azure
python src/planes/carga_plan_azure.py

# Plan y hoja concretos
python src/planes/carga_plan_azure.py "ruta/al/Plan 255 del 26 al 31 ENE 2026 v 22 con marcas doble capsulas.xlsx" "Plan - Semanal"
```

El script:

1. Parsea el nombre del archivo (Plan ID, versión, período).
2. Lee el Excel y genera filas de planificaciones y real.
3. Se conecta a Azure SQL.
4. Inserta en `ProduccionPlanificaciones` y `ProduccionReal` (por defecto en modo `append`).

En `src/config.py` podés cambiar:

- `AZURE_TABLA_PLANIFICACIONES` / `AZURE_TABLA_REAL` si las tablas tienen otro nombre.
- `AZURE_PLAN_IF_EXISTS`: `"append"` (añadir filas) o `"replace"` (reemplazar la tabla en cada carga).

---

## Resumen: qué pasarme

1. **Datos de conexión** (en `.env`, sin subirlos al repo):
   - `AZURE_SQL_SERVER`
   - `AZURE_SQL_DB`
   - `AZURE_SQL_USER`
   - `AZURE_SQL_PASSWORD`

2. **Confirmar** que en la base están creadas las tablas (ejecutando `sql/create_tables_plan.sql` si hace falta).

3. **Driver ODBC** instalado en tu máquina y `pip install -r requirements-azure.txt` en el venv.

Con eso podés correr `python src/planes/carga_plan_azure.py` y debería insertar el Plan en Azure.
