# Automatización PVB — vigilancia semanal

La gráfica usa `pvb_avance.csv`, con histórico de cortes y fuente individual de cada etapa.

## Operación

- Workflow existente: `.github/workflows/update-weekly.yml` (viernes, 14:25 UTC; ejecución manual desde Actions disponible).
- Extractor: `scripts/update_pvb.py`.
- El extractor consulta comunicados oficiales de Presidencia y SEDATU. Usa una lista de fuentes conocidas y descubre enlaces adicionales en páginas de prensa; intenta descubrir otros mediante RSS, pero solamente acepta cifras extraídas de páginas oficiales de `gob.mx`.
- Solo incorpora **contratadas** y **en construcción** cuando están expresamente relacionadas en una declaración nacional; no suma cifras institucionales. Con mayor certeza documental, puede agregar **entregadas** si están claramente reportadas para el mismo total nacional.
- No considera `asignadas`, `colocadas`, `créditos` ni los subtotales de una entidad como sinónimos de viviendas entregadas a escala nacional.
- Si no hay información verificable, conserva el CSV anterior y escribe diagnóstico en `pvb_update_status.json`.
- El workflow reconstruye `local-data.js`; en GitHub Pages se lee el CSV directamente.

## Fechas diferentes (importante)

Cada barra utiliza el último dato validado de su etapa y muestra su fecha en la nota de la gráfica. No se atribuye una fecha común cuando las cifras provienen de publicaciones distintas.

Corte inicial actualizado:

- Contratadas: 667,000 al 14 de septiembre de 2026 (SEDATU).
- En construcción: 277,000 al 14 de septiembre de 2026 (SEDATU).
- Entregadas: 24,500 al 15 de junio de 2026 (Presidencia; último corte homogéneo validado para esta variable).
- Meta sexenal: 1,800,000 viviendas nuevas.

Fuentes:

- https://www.gob.mx/sedatu/prensa/el-programa-de-vivienda-para-el-bienestar-avanza-hay-667-mil-viviendas-contratadas-y-277-mil-en-proceso-de-obra-sedatu
- https://www.gob.mx/presidencia/prensa/vivienda-para-el-bienestar-hay-274-mil-en-construccion-en-el-pais-el-programa-atiende-a-cerca-de-7-millones-de-personas-presidenta

## Validación de GitHub Actions

1. `Actions` > `Vigilancia semanal PVB` > `Run workflow`.
2. En el log, buscar `articulos_validados`, `nuevas_filas`, `errores_consulta`.
3. Revisar `pvb_update_status.json` y confirmar si se publicaron nuevas filas. `sin_novedades_verificables` no significa fallo del dashboard.
4. En GitHub Pages confirmar que la gráfica muestra los valores y fechas correspondientes.

**Alcance de la automatización:** vigilancia y extracción conservadora. Los comunicados no constituyen una API estructurada y la publicación automática depende de que su contenido y formato permitan verificar las definiciones; un cambio en la página puede requerir revisión del extractor.
