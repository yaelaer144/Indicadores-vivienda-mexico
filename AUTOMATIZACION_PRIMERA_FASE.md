# Primera fase de preparación para automatización — 06/10/2026

En esta versión se externalizaron las series que antes dependían de datos incrustados en JavaScript/JSON. Las cifras visibles se mantienen sin cambios.

## Archivos operativos nuevos
- `csvm_pib_vivienda_anual.csv`: PIB de vivienda, participación y componentes.
- `enec_indices_laborales_mensual.csv`: personal, horas y remuneraciones ENEC.
- `imss_sbc_construccion_mensual.csv`: SBC diario de construcción IMSS.
- `ruv_flujo_vivienda_anual.csv`: registradas, inicio de obra y terminadas.
- `condiciones_resumen_2024.csv`: materiales y déficit cualitativo.

Además se conectaron al cargador los archivos ya existentes:
- `tenencia_historica.csv`
- `tenencia_2024.csv`
- `tenencia_rural_urbano_2024.csv`
- `condiciones_historicas.csv`

`data-loader.js` carga estos archivos antes de renderizar el dashboard. `bootstrap-data.js` queda como respaldo inicial, pero los CSV externos prevalecen cuando están disponibles. `local-data.js` contiene una copia generada de los CSV para permitir abrir `index.html` directamente mediante `file:///`.

La siguiente fase será automatizar la descarga/transformación desde las fuentes oficiales y actualizar estos CSV mediante GitHub Actions.
