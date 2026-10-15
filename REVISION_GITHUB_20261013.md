# Revisión técnica del dashboard — 13 de octubre de 2026

## Corrección de la gráfica de resumen
En `charts.js`, gráfica `sum-shf` («Precios de vivienda y costos de construcción»), cada observación SHF trimestral se asigna ahora al mes de cierre: T1→marzo, T2→junio, T3→septiembre y T4→diciembre. Se construye un eje cronológico mensual común al ICC, manteniendo valores SHF nulos en los meses intermedios. No se interpolan ni replican observaciones. También se cambió la versión de recursos en `index.html` para evitar reutilizar el JavaScript anterior almacenado en caché.

## Automatización: revisión estática, no verificación operativa
Existen cuatro GitHub Actions con cron y ejecución manual: `update-inegi.yml` (martes), `update-imss.yml` (miércoles), `update-ruv-shf-financing.yml` (jueves) y `update-remaining.yml` (viernes). Los cuatro tienen permisos `contents: write` y confirman cambios mediante `git push`. Los scripts de Python pasan comprobación sintáctica y `charts.js` / `app.js` pasan `node --check`.

Esto NO certifica que las fuentes externas respondan correctamente, que la API de INEGI esté configurada, que las ramas admitan push automático, ni que GitHub Pages se haya habilitado: debe probarse desde Actions. En Settings → Secrets and variables → Actions agregar `INEGI_API_TOKEN`, en caso de necesitarlo, y en Settings → Actions → General confirmar permisos de lectura y escritura para GITHUB_TOKEN; comprobar protecciones de rama.

Algunos pasos usan `continue-on-error: true`: el workflow puede terminar en verde aunque ciertas consultas hayan fallado. Verificar los logs y fechas efectivas de los CSV. Los flujos con cron se ejecutan en UTC y pueden retrasarse. El proceso no garantiza por sí mismo que toda serie tenga datos nuevos.

## Cobertura histórica
El archivo `automation_coverage.json` entregado identifica nueve series aún sin histórico completo desde 2018. Entre ellas están IGAE, IMAI, ENEC auxiliares, IMSS, ENOE y SHF. No se ha ejecutado una carga histórica ni se ha comprobado acceso en vivo a los proveedores durante esta revisión.

## Subida
Descomprimir este ZIP y subir todos los archivos y carpetas **incluida la carpeta oculta `.github/workflows`** a la raíz del repositorio; no subir únicamente el ZIP. En GitHub, Settings → Pages, publicar rama `main` y `/ (root)`, si esa es la rama efectiva. Luego ejecutar una vez cada workflow mediante Actions → Run workflow, revisar logs y comprobar que cambien los CSV y `local-data.js` cuando haya información más reciente.
