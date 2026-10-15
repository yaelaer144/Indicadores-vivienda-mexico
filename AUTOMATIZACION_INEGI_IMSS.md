# Automatización INEGI + IMSS · Dashboard de vivienda

## 1. Qué queda automatizado

### INEGI
El workflow `.github/workflows/update-inegi.yml` se ejecuta semanalmente y también puede iniciarse manualmente desde **Actions**.

Actualiza mediante la API del Banco de Indicadores:

- ICC / construcción residencial por ciudad y sus subíndices.
- INPP construcción, edificación, edificación residencial, no residencial y obra civil.
- IGAE construcción.
- IMAI construcción.
- IFB construcción residencial.
- VAB/PIB trimestral: Construcción, Edificación, Obras de ingeniería civil y Trabajos especializados.
- ENEC: índices de personal, horas y remuneraciones para Construcción y Edificación.
- Cuenta Satélite de Vivienda: PIB, participación y componentes cuando el catálogo de la API expone las series correspondientes.

Las claves que ya estaban verificadas se consultan directamente. Para las demás, el script `scripts/update_inegi_series.py` busca candidatos en el catálogo de indicadores y **sólo acepta una clave cuando la serie descargada coincide con el histórico validado del dashboard**. Una serie que no supera la validación conserva su CSV anterior.

El archivo `inegi_resolved_ids.json` guarda las claves aceptadas para no volver a resolverlas en cada ejecución.

### IMSS
El workflow `.github/workflows/update-imss.yml` consulta los archivos mensuales de **Datos Abiertos IMSS · Asegurados** y actualiza:

- `imss_construccion_mensual.csv`: puestos de trabajo en construcción.
- `imss_sbc_construccion_mensual.csv`: salario base de cotización diario en construcción.
- `imss_total_mensual.csv`: puestos de trabajo totales nacionales.

Reglas de cálculo:

- Construcción: `sector_economico_1 = 4`.
- Puestos de trabajo: suma de `ta`.
- SBC diario: `sum(masa_sal_ta) / sum(ta_sal)`.

El script busca los archivos mensuales faltantes desde el último periodo ya almacenado. Si un mes aún no está publicado, lo omite y vuelve a intentarlo en la siguiente ejecución.

## 2. Configuración necesaria en GitHub

INEGI requiere token.

1. Obtener un token de la API del Banco de Indicadores de INEGI.
2. En el repositorio: **Settings → Secrets and variables → Actions**.
3. Crear el secret `INEGI_API_TOKEN`.
4. Subir esta versión completa del dashboard, incluida la carpeta `.github/workflows` y `scripts`.

IMSS no requiere token.

## 3. Protección contra datos incorrectos

Los scripts aplican estas reglas antes de reemplazar un archivo:

- no aceptar series vacías;
- no aceptar archivos IMSS sin las columnas esperadas;
- validar magnitudes mínimas y plausibilidad del SBC;
- validar las series INEGI nuevas contra observaciones históricas ya verificadas;
- escribir primero a un archivo temporal y reemplazar el CSV sólo después de superar las validaciones;
- mantener archivos de estado: `auto_update_status.json` e `imss_update_status.json`.

Después de cada actualización se ejecuta `scripts/rebuild_local_data.py`, que regenera `local-data.js`. Esto permite que la versión local del dashboard y la versión publicada en GitHub consuman los mismos datos.

## 4. Frecuencia

- INEGI: martes 12:20 UTC, semanal.
- IMSS: miércoles 12:40 UTC, semanal.

La frecuencia semanal permite captar publicaciones con calendarios distintos sin asumir que todas las fuentes actualizan el mismo día. Si no hay un dato nuevo, GitHub no genera un commit.

## 5. Series que no deben automatizarse con estos scripts

Este bloque no sustituye la extracción de microdatos ENIGH/ENOE ni fuentes de CONAVI, SHF, RUV/SNIIV o PVB. Esas fuentes mantienen sus propios procesos y deben automatizarse por separado.
