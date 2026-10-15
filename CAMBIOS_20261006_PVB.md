# Cambio PVB · 06/10/2026

- Se eliminan las cifras PVB hardcodeadas de `charts.js`.
- Se crea `pvb_avance.csv` como archivo estable de actualización.
- `data-loader.js` toma automáticamente el último `periodo` disponible.
- `app.js` actualiza dinámicamente fecha de corte, cifras, meta, fuente y enlace.
- Se conserva fallback en `local-data.js` para apertura local.
