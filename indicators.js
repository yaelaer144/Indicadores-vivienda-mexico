(function(){
  const MXN = new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:0});
  const NUM = new Intl.NumberFormat('es-MX',{maximumFractionDigits:1});
  const ABBR = {mdp:'millones de pesos',k:'miles',ha:'hectáreas',ho:'horas'};
  window.FMT = {
    money:v=>Number.isFinite(v)?MXN.format(v):'N/D',
    number:(v,d=1)=>Number.isFinite(v)?new Intl.NumberFormat('es-MX',{maximumFractionDigits:d}).format(v):'N/D',
    pct:v=>Number.isFinite(v)?`${NUM.format(v)}%`:'N/D',
    millionsFromThousands:v=>Number.isFinite(v)?new Intl.NumberFormat('es-MX',{minimumFractionDigits:2,maximumFractionDigits:2}).format(v/1000):'N/D',
    mdp:v=>Number.isFinite(v)?new Intl.NumberFormat('es-MX',{maximumFractionDigits:0}).format(v):'N/D',
    billonesFromMillions:v=>Number.isFinite(v)?new Intl.NumberFormat('es-MX',{minimumFractionDigits:1,maximumFractionDigits:1}).format(v/1000000):'N/D',
    daily:v=>Number.isFinite(v)?MXN.format(v):'N/D'
  };
  function kpiValue(value,unit){
    if(!unit || value==='N/D') return {html:value,foot:''};
    const u=String(unit).trim();
    if(/^porcentaje/i.test(u)) return {html:value,foot:''};
    if(ABBR[u]) return {html:`${value} <span class="kpi-value-unit">${u}</span>`,foot:`*${u} = ${ABBR[u]}`};
    if(/^índice\s+/i.test(u)) return {html:`${value} <span class="kpi-value-unit">${u.replace(/^índice\s+/i,'')}</span>`,foot:''};
    return {html:`${value} <span class="kpi-value-unit">${u}</span>`,foot:''};
  }
  const cleanCopy=html=>String(html||'').replace(/<div class="note">[\s\S]*?<\/div>/g,'').trim();

  const CHART_SOURCE = {
    'sum-employment':'INEGI, Encuesta Nacional de Ocupación y Empleo (ENOE).',
    'sum-shf':'Sociedad Hipotecaria Federal (SHF) e INEGI, Índice de Costo de la Construcción residencial por ciudad.',
    'act-igae':'INEGI, Indicador Global de la Actividad Económica (IGAE).',
    'act-vab':'INEGI, Sistema de Cuentas Nacionales de México, PIB trimestral base 2018.',
    'act-ifb':'INEGI, Inversión Fija Bruta (IFB).',
    'act-imai':'INEGI, Indicador Mensual de la Actividad Industrial (IMAI).',
    'act-enec-production':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'lab-enoe':'INEGI, Encuesta Nacional de Ocupación y Empleo (ENOE).',
    'lab-imss':'Instituto Mexicano del Seguro Social (IMSS).',
    'lab-personal':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'lab-enec-worker-type':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'lab-hours':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'lab-rem':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'lab-salary':'Instituto Mexicano del Seguro Social (IMSS).',
    'act-pib':'INEGI, Cuenta Satélite de Vivienda de México (CSVM).',
    'act-share':'INEGI, Cuenta Satélite de Vivienda de México (CSVM).',
    'prod-enec-housing-activity':'INEGI, Encuesta Nacional de Empresas Constructoras (ENEC).',
    'prod-pvb':'Presidencia de la República / Programa de Vivienda para el Bienestar (PVB).',
    'prod-flow':'Registro Único de Vivienda (RUV) / SNIIV.',
    'prod-ruv-total':'SEDATU, SNIIV / Registro Único de Vivienda (RUV).',
    'prod-ruv-segment':'SEDATU, SNIIV / Registro Único de Vivienda (RUV).',
    'price-shf':'Sociedad Hipotecaria Federal (SHF).',
    'price-shf-index':'Sociedad Hipotecaria Federal (SHF), datos abiertos del Índice SHF, base 2017=100.',
    'price-costs':'INEGI, Índice de Costo de la Construcción residencial por ciudad (antes INCEVIS).',
    'price-inpp-components':'INEGI, Índice de Costo de la Construcción residencial por ciudad (antes INCEVIS).',
    'price-housing-components':'INEGI, Índice Nacional de Precios Productor (INPP).',
    'price-inpp-edification':'INEGI, Índice Nacional de Precios Productor (INPP).',
    'price-financing':'CNBV, Series Históricas de Banca Múltiple.',
    'cond-history':'CONEVAL, con información de INEGI.',
    'cond-needs-history':'CONAVI.',
    'cond-tenure-compare':'INEGI, Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH).',
    'cond-tenure':'INEGI, Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH), último levantamiento disponible.',
    'cond-tenure-rural-urban':'INEGI, Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH), último levantamiento disponible.',
    'cond-deprivation':'CONEVAL, con información de INEGI.',
    'cond-materials':'CONAVI.'
  };
  const sourceHtml=id=>CHART_SOURCE[id]?`<div class="chart-source"><strong>Fuente:</strong> ${CHART_SOURCE[id]}</div>`:'';
  window.UI = {
    kpi:(label,value,context,unit,note)=>{const v=kpiValue(value,unit);return `<article class="kpi"><div class="kpi-label">${label}</div><div class="kpi-value">${v.html}</div>${context?`<div class="kpi-context">${context}</div>`:''}${v.foot?`<div class="kpi-unit">${v.foot}</div>`:''}${note?`<div class="kpi-explain"><strong>Qué mide:</strong> ${note}</div>`:''}</article>`;},
    pageHead:(title,copy,meta='')=>`<div class="page-head"><div><div class="eyebrow">Sistema de indicadores</div><h2>${title}</h2>${copy?`<p>${copy}</p>`:''}</div>${meta?`<span class="pill">${meta}</span>`:''}</div>`,
    card:(id,title,sub,copy,wide=false)=>`<article class="card ${wide?'wide':''}"><div class="card-head"><h3>${title}</h3><p>${sub}</p></div><div class="chart-wrap"><canvas id="${id}"></canvas></div><div class="card-copy">${cleanCopy(copy)}${sourceHtml(id)}</div></article>`,
    dualCard:(id,varId,title,sub,copy,varTitle='Variación anual porcentual',varSub='Porcentaje respecto al año anterior',levelCopy='',varCopy='')=>`<article class="card wide dual-card"><div class="card-head"><h3>${title}</h3><p>${sub}</p></div><div class="dual-chart-grid"><div class="chart-panel"><div class="chart-panel-title">Nivel del indicador</div><div class="chart-wrap"><canvas id="${id}"></canvas></div>${levelCopy?`<div class="panel-copy">${levelCopy}</div>`:''}</div><div class="chart-panel variation-panel"><div class="chart-panel-title">${varTitle}</div><div class="chart-panel-sub">${varSub}</div><div class="chart-wrap"><canvas id="${varId}"></canvas></div>${varCopy?`<div class="panel-copy">${varCopy}</div>`:''}</div></div>${copy?`<div class="card-copy">${cleanCopy(copy)}${sourceHtml(id)}</div>`:sourceHtml(id)}</article>`
  };
})();
