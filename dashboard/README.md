# Dashboard Plan y Minuta EE4A

Dashboard estático publicado como artifact de Claude:
**https://claude.ai/artifact/NADZi36xjR8ViFC9ATijMh** (privado; compartir desde el menú Share).

Muestra plan vs real por marca (ProduccionPlanificaciones/ProduccionReal), eficiencia por máquina
(RendimientoReal), producción por turno (ProduccionDiariaPorTurno) y consumo de tabaco
(RendimientoTabaco). Estética y filtros calcados de `Comercial/comercial-tableroVentas`
(sidebar dorado Espert, semáforo 100/90, chips de filtros activos, persistencia en localStorage).

## Refrescar datos

Los datos van embebidos en el HTML (snapshot al publicar). Para refrescar:

```bash
# 1. venv con pyodbc + python-dotenv (usa el .env del repo padre)
python3 -m venv .venv && .venv/bin/pip install pyodbc python-dotenv

# 2. Extraer de Azure SQL → data.json (en el mismo dir del script)
.venv/bin/python extract.py

# 3. Compactar → compact.json
.venv/bin/python build_data.py

# 4. Inyectar en el template → dashboard.html
python3 - <<'EOF'
from pathlib import Path
t = Path('dashboard2.template.html').read_text()
Path('dashboard.html').write_text(t.replace('__DATA__', Path('compact.json').read_text()))
EOF
```

Después pedirle a Claude Code que republique `dashboard.html` sobre la URL del artifact
(pasando `url`), o publicarlo donde convenga.

Nota: `extract.py` y `build_data.py` referencian rutas del scratchpad/repo — ajustar las rutas
de `.env` y de salida si se corre desde acá.

## Mapeos hardcodeados

- `build_data.py`: nombres de máquinas (tabla `Maquina`), tipo de máquina (cigarrillera/
  empaquetadora/filtrera), marcas (espejo de `src/marcas.py`). Si se agrega una marca o
  máquina nueva, actualizar ahí.
