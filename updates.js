window.DashboardUpdates = {
  "last_verification": "2026-09-15T09:28:00-06:00",
  "overall_status": "ok",
  "publication_policy": "Solo se publican archivos canónicos validados; las descargas nuevas quedan en data/raw hasta aprobar su mapeo.",
  "sources": [
    {
      "id": "inegi_igae_construccion",
      "label": "IGAE construcción",
      "provider": "INEGI",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice base 2018=100",
      "published_latest_period": "2026-06",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inegi_ifb_residencial",
      "label": "IFB construcción residencial",
      "provider": "INEGI",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice base 2018=100",
      "published_latest_period": "2025",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inegi_imai_construccion",
      "label": "IMAI construcción",
      "provider": "INEGI",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice base 2018=100",
      "published_latest_period": "2025",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inegi_enec_personal_construccion",
      "label": "ENEC personal ocupado construcción",
      "provider": "INEGI ENEC",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice 2018=100",
      "published_latest_period": "2026-04",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inegi_enec_horas_construccion",
      "label": "ENEC horas trabajadas construcción",
      "provider": "INEGI ENEC",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice 2018=100",
      "published_latest_period": "2026-04",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inegi_enec_rem_construccion",
      "label": "ENEC remuneraciones medias construcción",
      "provider": "INEGI ENEC",
      "frequency": "mensual",
      "mode": "inegi_api",
      "unit": "índice 2018=100",
      "published_latest_period": "2026-04",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "enoe_construccion",
      "label": "Población ocupada en construcción",
      "provider": "INEGI ENOE vía Data México",
      "frequency": "trimestral",
      "mode": "datamexico_api",
      "unit": "miles de personas",
      "published_latest_period": "2026-06",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "imss_empleo_construccion",
      "label": "Puestos IMSS construcción",
      "provider": "IMSS",
      "frequency": "mensual",
      "mode": "official_file_feed",
      "unit": "miles de puestos",
      "published_latest_period": "2025",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "imss_sbc_construccion",
      "label": "SBC diario promedio construcción",
      "provider": "IMSS",
      "frequency": "mensual",
      "mode": "manual_controlado",
      "unit": "pesos diarios",
      "published_latest_period": "2026-06",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "shf_indice_precios",
      "label": "Índice SHF de precios de la vivienda",
      "provider": "SHF",
      "frequency": "trimestral",
      "mode": "official_file_feed",
      "unit": "%",
      "published_latest_period": "2026",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "enigh_tenencia",
      "label": "Tenencia de la vivienda",
      "provider": "INEGI ENIGH",
      "frequency": "bienal",
      "mode": "manual_controlado",
      "unit": "% de viviendas",
      "published_latest_period": "2024",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "condiciones_habitacionales",
      "label": "Carencias habitacionales",
      "provider": "INEGI / ENIGH",
      "frequency": "bienal",
      "mode": "manual_controlado",
      "unit": "% de la población",
      "published_latest_period": "2024",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "ruv_sniiv_produccion",
      "label": "Producción y composición de vivienda RUV",
      "provider": "SEDATU / SNIIV / RUV",
      "frequency": "mensual",
      "mode": "sniiv_api",
      "unit": "viviendas y porcentaje",
      "published_latest_period": "2025-12",
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    },
    {
      "id": "inpp_componentes_construccion",
      "label": "INPP componentes del costo de construcción",
      "provider": "INEGI INPP",
      "frequency": "mensual",
      "mode": "official_file_feed",
      "unit": "índice / variación anual %",
      "published_latest_period": null,
      "status": "verificado_local",
      "detail": "No se consultó internet en este ciclo."
    }
  ],
  "validation": {
    "errors": [],
    "warnings": [],
    "stats": {
      "series_rows": 923,
      "unique_series_keys": 923,
      "map_entities": 32,
      "enec_activity_rows": 100,
      "enec_housing_rows": 28,
      "enec_worker_type_rows": 28,
      "ruv_characteristic_rows": 26,
      "tenure_sum": 100.0,
      "warnings": 0,
      "errors": 0
    }
  }
};
