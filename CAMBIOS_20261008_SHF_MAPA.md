# Ajustes del 8 de octubre de 2026

## Producción de vivienda
- PIB de vivienda por componentes: ancho completo.
- Participación PIB y actividad productiva ENEC: izquierda/derecha.
- Avance PVB y producción anual de vivienda RUV: izquierda/derecha.
- La gráfica de flujo RUV conserva su ubicación posterior.

## Precios de vivienda
- Se agrega el panel **Índice SHF de Precios de la Vivienda (base 2017=100)** a la izquierda de su variación anual. El nivel se carga desde `shf_indice_nivel_trimestral.csv` cuando el archivo de datos abiertos SHF se identifica y valida. **No se incluye un histórico del nivel oficial en esta entrega**: el CSV inicial está vacío; en tal caso el panel indica pendiente, sin inventar cifras. El flujo de actualización SHF intenta extraer niveles y exige validación cruzada contra al menos tres variaciones anuales publicadas. La tasa anual existente se conserva.
- INPP: se elige el registro más reciente que tenga variación anual válida entre las bases mensuales cargadas; el proceso GitHub existente consulta los indicadores por API INEGI y actualiza CSV y respaldo local. En este ZIP el corte es agosto de 2026.
- Mapa: se ajusta proyección geográfica longitudinal por coseno de la latitud, se conserva escala uniforme y se adapta la relación ancho-alto de la vista SVG. Se conserva la selección de entidades y los precios.

## Nota operativa SHF
Para llenar el índice **ahora**, se necesita un archivo oficial SHF con niveles nacionales trimestrales base 2017=100. Las variaciones anuales sin niveles originales no determinan matemáticamente una única serie de índices. No debe etiquetarse una reconstrucción como índice oficial.
