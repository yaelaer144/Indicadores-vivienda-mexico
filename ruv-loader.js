// Producción RUV: consume exclusivamente el respaldo publicado por GitHub Actions.
// La API se consulta en scripts/update_ruv_produccion.py, no en el navegador.
(function () {
  function load() {
    const data = window.RUV_PRODUCTION;
    const valid = data && data.total && Array.isArray(data.total.annual) &&
      data.segment && Array.isArray(data.segment.annual) &&
      data.total.annual.length > 0 && data.segment.annual.length > 0;
    if (!valid) {
      console.warn('No se encontró el histórico RUV de producción.');
      window.DashboardApp?.setRuvLoading?.('No se encontró el histórico de producción RUV.');
      return;
    }
    window.DashboardCharts?.renderRuv?.(data);
    window.DashboardApp?.updateRuvStatus?.(data);
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', load);
  } else {
    load();
  }
})();
