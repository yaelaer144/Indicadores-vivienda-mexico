# Actualización de la gráfica PVB

La gráfica **Avance del Programa de Vivienda para el Bienestar (PVB)** ya no contiene cifras fijas en `charts.js`.

## Archivo que alimenta la gráfica

`pvb_avance.csv`

Columnas:
- `etapa`: Contratadas, En construcción, Entregadas o Meta sexenal.
- `viviendas`: número de viviendas.
- `periodo`: fecha de corte en formato `AAAA-MM-DD`.
- `relacion`: nota metodológica sobre la etapa.
- `fuente`: institución o publicación oficial.
- `url`: enlace al comunicado o fuente oficial.

## Cómo actualizar

Se pueden **agregar** nuevas filas para un nuevo corte sin eliminar las anteriores. El dashboard ordena los periodos y selecciona automáticamente el corte más reciente. Para que un corte esté completo, se recomienda cargar las cuatro etapas con la misma fecha.

Ejemplo:

```csv
etapa,viviendas,periodo,relacion,fuente,url
Contratadas,700000,2026-10-01,avance acumulado...,SEDATU / Presidencia,https://...
En construcción,350000,2026-10-01,subconjunto...,SEDATU / Presidencia,https://...
Entregadas,50000,2026-10-01,etapa reportada...,Presidencia,https://...
Meta sexenal,1800000,2026-10-01,meta sexenal PVB,SEDATU / Presidencia,https://...
```

Al subir el CSV actualizado a GitHub, la gráfica, el subtítulo, las cifras explicativas y la fuente cambian automáticamente al nuevo corte. No es necesario editar `charts.js` ni `app.js`.

> Nota para apertura local con `file:///`: `local-data.js` contiene un respaldo del corte vigente porque algunos navegadores bloquean la lectura de CSV locales. En GitHub Pages se usa directamente `pvb_avance.csv`.
