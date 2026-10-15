# Automatización completa del dashboard — 7 de octubre de 2026

Esta versión añade la automatización de las visualizaciones que aún dependían de actualización manual o de datos embebidos.

## Nuevos procesos

### ENOE — empleo en construcción
- Script: `scripts/update_enoe_inegi.py`
- Fuente: API Banco de Indicadores INEGI.
- Valida el indicador candidato contra la serie histórica local antes de sustituir `enoe_construccion_trimestral.csv`.
- Conserva el criterio de inicio en 2018.
- Requiere `INEGI_API_TOKEN`.

### ENEC — gráficas auxiliares
- Script: `scripts/update_remaining_inegi.py`
- Actualiza:
  - `enec_actividad_historica.csv` (valor de producción / índices de edificación, público y privado),
  - `enec_personal_tipo_variacion_mensual.csv`,
  - `enec_vivienda_yoy.csv`,
  - `enec_edificacion_variacion_mensual.csv`.
- Cada indicador se valida contra el histórico existente antes de ser aceptado.
- Requiere `INEGI_API_TOKEN`.

### Programa de Vivienda para el Bienestar
- Script: `scripts/update_pvb.py`
- Revisa comunicados oficiales de SEDATU y detecta el corte más reciente que reporte, como mínimo, viviendas contratadas y en construcción.
- Sólo incorpora “Entregadas” cuando la fuente lo dice explícitamente; no sustituye entregadas por asignadas.
- `pvb_avance.csv` conserva cortes anteriores y el dashboard selecciona el más reciente.

### ENIGH / condiciones habitacionales
- Script: `scripts/update_enigh_conditions.py`
- Descarga microdatos oficiales VIVIENDAS de la ENIGH más reciente disponible y calcula con `factor`:
  - tenencia nacional,
  - tenencia rural/urbana,
  - histórico de tenencia.
- Busca la última presentación oficial de Pobreza multidimensional de INEGI y actualiza el histórico nacional de:
  - carencia por calidad y espacios,
  - carencia por servicios básicos.
- Busca el documento técnico más reciente de déficit cualitativo en CONAVI/SIESCO para actualizar materiales y componentes del déficit.
- Si una fuente cambia de formato o no pasa las validaciones, conserva los CSV anteriores.

## Workflow

`.github/workflows/update-remaining.yml`

Se ejecuta los viernes y también puede lanzarse manualmente. Los cuatro procesos usan `continue-on-error` de forma independiente: una fuente caída no impide actualizar las demás. Al final se regenera `local-data.js` y se hace commit únicamente si existen cambios.

## Correcciones de arquitectura

`data-loader.js` ahora lee explícitamente `enec_personal_tipo_variacion_mensual.csv` y `enec_vivienda_yoy.csv`; antes esos dos gráficos seguían tomando valores del respaldo embebido.

Las etiquetas de la sección Condiciones habitacionales ya no tienen 2024 fijo: el año se toma del último dato cargado, por lo que una futura ENIGH/medición 2026 cambiará automáticamente títulos, subtítulos y KPI.

## Principio de seguridad

Ningún updater está autorizado a sustituir una serie con una coincidencia no validada. Ante cambios de API, catálogos o formatos, el workflow conserva el último dato válido y deja un archivo `*_update_status.json` para diagnóstico.
