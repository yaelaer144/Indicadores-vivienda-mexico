# Fase de cierre de automatización — 07/10/2026

## Objetivo
Cerrar los puntos detectados en la auditoría final: backfill desde 2018, eliminación de cortes fijos en la interfaz y automatización de KPIs auxiliares.

## Cambios
- INEGI: los scripts mantienen 2018-01 / 2018-T1 como piso de backfill y reescriben el histórico oficial cuando se ejecutan con `INEGI_API_TOKEN`.
- IMSS: el backfill desde 2018 se descarga en paralelo (8 trabajadores) y posteriormente opera de forma incremental sobre meses faltantes.
- SNIIV: nuevo `scripts/update_sniiv_kpis.py` actualiza inventario activo RUV y financiamientos del corte vigente.
- SHF: `update_shf_index.py` conserva la serie trimestral y ahora intenta actualizar también el archivo estable `shf_precios_entidad.csv` con promedio y cuantiles estatales. Si no reconoce al menos 30 entidades + Nacional, conserva el último archivo válido.
- PVB/CONAVI: el actualizador intenta extraer también predios, hectáreas y viviendas CONAVI cuando el comunicado los identifica de forma explícita; si no, conserva el último corte válido.
- Interfaz: se eliminaron etiquetas rígidas como “jun 2026”, “2T 2026”, “2018–2025” y “2013–2024” en las tarjetas/gráficas que deben avanzar automáticamente.
- Cobertura: nuevo `scripts/audit_coverage.py` genera `automation_coverage.json` en cada workflow, indicando qué series ya arrancan en 2018 y cuáles siguen pendientes de backfill.

## Primera ejecución en GitHub
1. Configurar `INEGI_API_TOKEN` en Settings → Secrets and variables → Actions.
2. Ejecutar manualmente `Actualizar series INEGI`, `Actualizar series IMSS`, `Actualizar series restantes` y `Actualizar RUV, SHF y crédito puente`.
3. Revisar `automation_coverage.json`: la meta es que IGAE, IMAI, ENOE, ENEC auxiliares e IMSS cambien de `pendiente_backfill` a `completo` cuando la fuente oficial permita recuperar 2018.

## Política de seguridad
Ningún script sustituye una serie válida si la nueva descarga está vacía, tiene cobertura insuficiente o no coincide razonablemente con el histórico previamente validado.
