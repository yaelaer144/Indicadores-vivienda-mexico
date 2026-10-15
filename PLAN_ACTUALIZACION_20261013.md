# Plan de frecuencia de actualización y cobertura histórica — 13 de octubre de 2026

## Regla general
Las frecuencias siguientes son de **consulta automática**, no promesa de que cada fuente publique nuevos datos exactamente ese día. Para cada serie se prioriza la fecha real más reciente que entregue su fuente. Los datos anteriores se conservan cuando la consulta no encuentra un nuevo dato válido. No se fabrican trimestres ni meses. GitHub Actions emplea UTC.

| Consulta automatizada | Indicadores | Frecuencia de publicación de la fuente | Histórico objetivo |
|---|---|---|---|
| Semanal (viernes) | Avance PVB | Irregular, según boletines oficiales | Inicio real del programa; no inventar 2016 |
| Mensual (día 15) | ICC e INPP construcción y subíndices, IGAE, IMAI, IFB, ENEC (actividad, índices laborales, personal), IMSS empleo y SBC, RUV registro/producción, SNIIV indicadores corrientes | Mensual; RUV/SNIIV según actualización del portal | 2016 preferente; 2018 alternativo cuando la fuente/metodología lo exija |
| Bimestral (día 20 de meses pares) | Tasa de crédito puente CNBV, presentada anualmente en gráfica | CNBV puede tener datos mensuales; agregación de tablero anual | 2016 preferente; 2018 alternativo |
| Trimestral (20 febrero, mayo, agosto, noviembre) | PIB/VAB construcción y subsectores, ENOE ocupación, Índice SHF y precios por entidad | Trimestral | 2016 preferente; VAB base 2018 desde 2018 en actual configuración |
| Semestral (abril y octubre) | Revisión de ENIGH, tenencia, carencias y condiciones | ENIGH bienal; pobreza y CONAVI según publicación, no necesariamente semestral | 2016 cuando comparable; mantener 2024 hasta publicación nueva validada |
| Anual (diciembre) | Cuenta Satélite de Vivienda y participación PIB vivienda | Anual | 2016 preferente; 2018 alternativo |

**Advertencias**: La fecha de consulta no equivale a fecha de publicación. Algunas series del ZIP tienen datos faltantes o solo arrancan en 2023/2025; cambiar una constante de Python no completa la historia por sí solo. `CATALOGO_FRECUENCIAS_Y_COBERTURA_20261013.json` contiene los primeros y últimos periodos detectados en los CSV actuales. `automation_coverage.json` y `scripts/audit_coverage.py` permiten reauditar el histórico; su estado verifica el inicio pero no garantiza ausencia de huecos intermedios. La cuenta satélite y otras series pueden tener revisiones de base.

## Implementación
Seis workflows independientes en `.github/workflows`: semanal, mensual, bimestral, trimestral, semestral y anual. `workflow_dispatch` permite ejecución manual. Todos regeneran `local-data.js` y escriben estados. `scripts/run_group.py` registra fallas por script y las expone como ejecución fallida. Requiere `INEGI_API_TOKEN` en GitHub Secrets para consultas del Banco de Indicadores. Verificar GitHub Actions, permisos de escritura y Pages; la automatización no está probada contra todas las fuentes desde GitHub.

## Limitaciones concretas
Los indicadores RUV, ENIGH y SHF no pueden retroceder artificialmente al año 2016 cuando solo hay descargas parciales. La recuperación histórica efectiva depende de que cada fuente y su endpoint responda con periodos anteriores y preserve comparabilidad. El resumen del PVB debe empezar cuando existe el programa, no en 2016. La programación solo intenta extraer datos; no obliga a que se publiquen.
