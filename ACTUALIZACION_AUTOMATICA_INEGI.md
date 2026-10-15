# Actualización automática INEGI · VAB, ICC e INPP

## Series incorporadas el 28/09/2026

### VAB construcción · PIB trimestral base 2018
Fuente oficial: INEGI, Producto Interno Bruto Trimestral, año base 2018, series originales, millones de pesos a precios de 2018.
Ruta de consulta: Cuentas nacionales > Producto interno bruto trimestral, base 2018 > Valores a precios de 2018 > Actividades secundarias > 23 Construcción.
Series: Total sector 23; 236 Edificación; 237 Construcción de obras de ingeniería civil; 238 Trabajos especializados para la construcción.
Consulta web verificable: https://www.inegi.org.mx/app/tabulados/default.aspx?cno=1&idrt=3257&in=2&opc=p&pr=20&tp=20&vr=1&wr=1
Archivo que consume el dashboard: `vab_construccion_subsectores_trimestral.csv`.
Transformación: conservar periodicidad trimestral; convertir millones de pesos a billones únicamente en la visualización (`valor / 1,000,000`); calcular variación anual como `(nivel_t / nivel_t-4 - 1) * 100`.

### ICC / construcción residencial por ciudad (antes INCEVIS)
Fuente oficial: INEGI, Índice Nacional de Precios Productor, base julio 2025=100 (SCIAN 2018), Construcción > Construcción residencial por ciudad (antes INCEVIS) > Nacional.
Claves: 1660002 General; 1660003 Materiales de construcción; 1660004 Alquiler de maquinaria; 1660005 Mano de obra.
Archivo del dashboard: `icc_incevis_base2025_mensual.csv`.
Transformación: conservar el índice mensual; calcular variación anual `(indice_t / indice_t-12 - 1) * 100`. No interpolar meses.

### INPP construcción y edificación
Fuente oficial: INEGI, Índice Nacional de Precios Productor, base julio 2025=100 (SCIAN 2018), Producción total según actividad económica.
Claves: 1700226 = 23 Construcción; 1700227 = 236 Edificación; 1700228 = 2361 Edificación residencial; 1700232 = 2362 Edificación no residencial; 1700239 = 237 Construcción de obras de ingeniería civil.
Archivo del dashboard: `inpp_construccion_edificacion_base2025_mensual.csv`.
Transformación: conservar niveles mensuales y calcular variación anual contra el mismo mes del año anterior. No mezclar estas series con el ICC/INCEVIS.

## Automatización en GitHub
INEGI ofrece una API para consultar indicadores en cuanto se actualizan. La API requiere token. Documentación oficial: https://www.inegi.org.mx/servicios/api_indicadores.html

1. Registrar un token de la API de Indicadores de INEGI.
2. En GitHub > Settings > Secrets and variables > Actions, crear el secreto `INEGI_API_TOKEN`.
3. El workflow `.github/workflows/update-inegi.yml` ejecuta `scripts/update_inegi_series.py` y, si cambian las series, actualiza los CSV y `local-data.js`.
4. La actualización de precios se identifica por clave, no por posición de columna, para resistir cambios de orden.
5. Para VAB queda documentada la ruta oficial y los nombres exactos de las cuatro series. La versión incluida conserva la descarga validada del 28/09/2026. Para automatizarla con la API, se deben obtener una sola vez las claves de indicador mediante el Constructor de consultas de INEGI y añadirlas al script; no se debe intentar inferirlas por posición. Alternativamente puede automatizarse la descarga del tabulado oficial por etiqueta SCIAN 23/236/237/238 con validación previa.
6. Validaciones mínimas antes de escribir: frecuencia esperada, periodo no decreciente, valores numéricos, presencia de las cuatro series y ausencia de duplicados.

## Regla de actualización
Nunca sustituir una base válida por una descarga vacía o incompleta. Primero descargar a memoria/archivo temporal, validar, recalcular tasas y sólo entonces reemplazar el CSV del repositorio. La fecha de consulta y el último periodo deben registrarse en `auto_update_status.json`.
