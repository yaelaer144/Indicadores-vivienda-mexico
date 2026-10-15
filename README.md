# Dashboard de vivienda — publicación y actualización automática

**Importante:** GitHub no descomprime archivos ZIP subidos desde «Add file → Upload files». Para subir el proyecto completo en una sola operación, descomprime este ZIP en tu equipo y ejecuta `SUBIR_A_GITHUB.ps1` desde PowerShell. El script hace un único `git push` y conserva `.github/workflows` y `scripts`.

## Configuración inicial

1. Instala Git para Windows e inicia sesión en GitHub (Git Credential Manager).
2. Crea un repositorio vacío en GitHub y copia su URL HTTPS.
3. Descomprime el ZIP, abre PowerShell dentro de esa carpeta y ejecuta `powershell -ExecutionPolicy Bypass -File .\SUBIR_A_GITHUB.ps1`. Pega la URL cuando se solicite.
4. En GitHub, Settings → Pages → Deploy from a branch → main → /(root).
5. En Settings → Secrets and variables → Actions, crea `INEGI_API_TOKEN` con tu token válido de INEGI.
6. En Settings → Actions → General verifica que las acciones estén habilitadas y tengan permiso de lectura/escritura (los workflows también declaran `contents: write`).
7. En Actions ejecuta manualmente cada flujo la primera vez para comprobar la descarga de fuentes.

**Alcance de la revisión:** se comprobó la estructura de los seis workflows y sus scripts referenciados; no se verificó en vivo la respuesta de cada fuente externa. La programación ejecuta consultas, pero no garantiza que la fuente haya publicado datos nuevos.

## Frecuencias

- Semanal: PVB (viernes).
- Mensual: INEGI, IMSS, RUV y SNIIV (día 15).
- Bimestral: financiamiento (día 20 de febrero, abril, junio, agosto, octubre y diciembre).
- Trimestral: PIB, ENOE y SHF (día 20 de febrero, mayo, agosto y noviembre).
- Semestral: condiciones habitacionales (20 de abril y octubre).
- Anual: Cuenta Satélite de Vivienda (20 de diciembre).

---

## Documentación histórica original

# Dashboard de vivienda — GitHub Pages (sin Actions)

Esta versión está preparada para publicarse como sitio estático directamente desde la rama `main` y la carpeta raíz del repositorio.

## Publicación

1. Sube **el contenido de esta carpeta** directamente a la raíz del repositorio. `index.html` debe quedar visible en la página principal del repositorio, no dentro de otra carpeta.
2. En GitHub abre **Settings → Pages**.
3. En **Build and deployment → Source** selecciona **Deploy from a branch**.
4. Selecciona **Branch: main** y **Folder: /(root)**.
5. Presiona **Save**.
6. Regresa a **Settings → Pages** para abrir el enlace publicado cuando GitHub indique que el sitio está activo.

No se utilizan GitHub Actions ni workflows de despliegue.

## Archivos principales

- `index.html`: entrada del dashboard.
- `styles.css`: estilos.
- `app.js`, `charts.js`, `maps.js`, etc.: lógica del dashboard.
- Archivos `.csv` y `.json`: datos locales utilizados por el sitio.
- `.nojekyll`: evita que GitHub Pages procese el contenido mediante Jekyll.

## Importante

Si el repositorio ya tenía un workflow en `.github/workflows`, elimínalo del repositorio para mantener esta configuración completamente sin Actions.


### Cambio aplicado (8 sep 2026)
- ICC: serie mensual oficial; el gráfico usa el nivel mensual del índice (base julio 2019=100).
- INPP construcción: serie mensual; cada punto muestra la variación anual correspondiente a ese mes frente al mismo mes del año previo.
- No se interpolan datos faltantes.


## Actualización 11-sep-2026
- ICC/costo de construcción residencial: se muestran variaciones anuales mensuales verificadas del índice nacional de construcción residencial por ciudad; último corte homogéneo verificado en esta versión: junio de 2026. Se eliminó el dato de 5.63% que correspondía a “Edificación residencial” por actividad económica y no al ICC nacional por ciudad.
- INPP construcción: agosto de 2026.
- IFB residencial: variación anual actualizada a junio de 2026; el nivel histórico desestacionalizado local conserva su corte previo cuando no se recuperó un nivel homogéneo.
- IGAE e IMAI construcción: junio de 2026. La publicación de IMAI julio estaba programada para el 11-sep-2026 y no se incorporó antes de estar disponible oficialmente.
- ENEC: publicación oficial hasta junio de 2026; la gráfica de variación mensual de edificación llega a junio.
- IMSS: la visualización y el KPI de mercado laboral muestran únicamente la serie sectorial de construcción; no se usa el total nacional como referencia coyuntural.
- PIB, ENOE y SHF: 2T-2026, conforme a su periodicidad trimestral. ENIGH/tenencia: 2024, último levantamiento bienal.


## Ajustes de presentación · 11 sep 2026 (v3)
- Estandarización de títulos de tasas interanuales a **Variación anual porcentual**.
- VAB de construcción expresado en billones de pesos.
- IFB e IMAI se etiquetan con el nombre de su indicador. En la explicación “Qué mide” se aclara que la gráfica usa una aproximación de ciclo-tendencia mediante promedio móvil centrado de 5 meses; ENEC conserva el tratamiento especificado en sus propias tarjetas.
- ICC ampliado con variaciones mensuales homogéneas del índice nacional de construcción residencial por ciudad desde 2025 y observaciones verificadas de 2026; sin interpolar huecos ni mezclar conceptos.
- Eliminación de notas descriptivas secundarias bajo las explicaciones principales de las gráficas.
- Definiciones de segmentos de vivienda incorporadas en la gráfica de composición RUV.

## Corrección ICC · 11 sep 2026
- El ICC se presenta ahora en dos paneles mensuales: nivel del índice (base julio 2019=100) y variación anual (%).
- Se evita mezclar niveles del índice con tasas porcentuales en una misma gráfica.
- Los meses sin observación oficial permanecen como N/D; no se interpolan.


## Ajustes solicitados · 15 sep 2026
- ENOE construcción: el histórico trimestral visible inicia en 2023.
- IGAE: la visualización llega a 2018 mediante una referencia anual real del sector 23 normalizada a base 2018=100, claramente separada de la serie mensual IGAE desde 2025.
- VAB construcción: histórico anual real 2018–2024 a precios de 2018.
- Producción de vivienda: los KPI de inventario RUV y financiamientos SNIIV usan el corte detallado disponible al 30 de junio de 2026.
- Condiciones habitacionales: sin modificación específica en esta entrega.


## Ajustes cerrados · 17 sep 2026 (v5)
- Resumen ENOE con doble eje: construcción y población ocupada total.
- Comparación SHF–ICC alineada trimestralmente sin interpolación.
- SBC de construcción expresado como equivalente mensual (SBC diario × 30.4).
- Tenencia histórica y 2024 en barras apiladas de cuatro categorías.
- Comparación rural/urbana ENIGH 2024 incorporada; el cálculo usa totales publicados con redondeo y se identifica como aproximado.


## Actualización 28/09/2026
Ver `CAMBIOS_20260928_v19.md` y `ACTUALIZACION_AUTOMATICA_INEGI.md` para las nuevas fuentes VAB/ICC/INPP y la preparación para actualización automática en GitHub.


**Periodicidades de actualización:** consultar `PLAN_ACTUALIZACION_20261013.md` y los seis flujos de `.github/workflows`.
