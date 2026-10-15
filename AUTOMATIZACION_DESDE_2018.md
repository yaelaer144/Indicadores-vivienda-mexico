# Automatización histórica desde 2018

Esta versión homologa las series automatizadas de INEGI e IMSS para que su ventana histórica operativa inicie en 2018.

## INEGI

El actualizador `scripts/update_inegi_series.py` descarga la serie histórica completa disponible desde la API y conserva únicamente observaciones desde:

- Mensuales: `2018-01`.
- Trimestrales: `2018-T1`.
- Anuales automatizadas: `2018`.

Aplica a ICC/INCEVIS, INPP construcción, IGAE construcción, IMAI construcción, IFB residencial, VAB construcción y subsectores, ENEC laboral y Cuenta Satélite de Vivienda.

Las ejecuciones posteriores vuelven a consultar el histórico oficial, de modo que si INEGI revisa observaciones anteriores desde 2018, el CSV también puede incorporar la revisión.

## IMSS

El actualizador `scripts/update_imss_series.py` opera con un backfill desde `2018-01`.

En cada ejecución revisa todos los meses desde enero de 2018 hasta el mes corriente, pero sólo descarga un mes si falta en al menos uno de estos tres archivos:

- `imss_construccion_mensual.csv`.
- `imss_sbc_construccion_mensual.csv`.
- `imss_total_mensual.csv`.

Esto permite que la primera ejecución complete el histórico faltante y que después el proceso sea prácticamente incremental.

## GitHub Actions

- INEGI: `.github/workflows/update-inegi.yml`.
- IMSS: `.github/workflows/update-imss.yml`.

INEGI requiere el secret `INEGI_API_TOKEN`. IMSS no requiere token.
