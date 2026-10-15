# Automatización RUV, SHF y crédito puente

## 1. Flujo RUV / SNIIV

El script `scripts/update_ruv_flow.py` consulta directamente la API pública del SNIIV desde 2018:

- Registro de vivienda: `GetRegistro`
- Verificación de vivienda: `GetVerficacion`
- Producción de vivienda: `GetProduccion`

El resultado alimenta `ruv_flujo_vivienda_anual.csv`, que es la fuente de las gráficas **Registradas / Inicio de obra / Terminadas** y su variación anual.

Antes de sustituir la base, el script contrasta las observaciones comunes con el histórico actual para detectar cambios severos de definición o unidad.

## 2. Índice SHF

`scripts/update_shf_index.py` revisa la página oficial del Índice SHF y localiza el archivo de **datos abiertos** más reciente. El script intenta extraer la variación anual nacional trimestral desde 2018 y la compara con el histórico vigente antes de sobrescribir `shf_indice_trimestral.csv`.

Si SHF cambia el formato del archivo y la serie no puede identificarse con seguridad, la ejecución termina con error y conserva intacto el CSV anterior.

## 3. Costo de financiamiento / crédito puente

La gráfica ahora consume `bridge_financing_anual.csv` en vez de un arreglo incrustado en JavaScript.

`scripts/update_bridge_financing.py` descarga el libro oficial **Series Históricas de Banca Múltiple** (`SH_BM.xlsm`) de la CNBV y busca la serie de tasa de interés asociada al crédito puente para construcción de vivienda. Utiliza el dato de diciembre como cierre anual; para el año corriente puede utilizar el último mes disponible.

La extracción es conservadora: si no reconoce de forma segura la estructura o la serie difiere de manera incompatible con el histórico, no sustituye el archivo.

## GitHub Actions

`.github/workflows/update-ruv-shf-financing.yml` se ejecuta semanalmente los jueves y también puede lanzarse manualmente desde **Actions**. Las tres consultas son independientes (`continue-on-error`) para que una modificación temporal en una fuente no impida actualizar las demás.

Después de cada ejecución se regenera `local-data.js` y sólo se crea un commit cuando existen cambios.
