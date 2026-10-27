(function(){
  const D=window.DASHBOARD_DATA, F=window.FMT, U=window.UI;
  const info=(title,body)=>`<div class="info"><strong>${title}</strong><p>${body}</p></div>`;
  const method=(title,body)=>`<div class="method"><strong>${title}</strong><p>${body}</p></div>`;
  const latestSalary=D.labor.salary_monthly[D.labor.salary_monthly.length-1];
  const latestIdx=D.labor.monthly_indices[D.labor.monthly_indices.length-1];
  const UP=window.DashboardUpdates||{};
  const MESES=['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
  const fmtMonth=p=>{const m=String(p||'').match(/^(20\d{2})-(\d{2})$/);return m?`${MESES[Number(m[2])-1]} ${m[1]}`:String(p||'N/D');};
  const fmtQuarter=p=>{const m=String(p||'').match(/^(20\d{2})-T([1-4])$/);return m?`${m[2]}T ${m[1]}`:String(p||'N/D');};
  const fmtDate=p=>{const m=String(p||'').match(/^(20\d{2})-(\d{2})-(\d{2})$/);return m?`${Number(m[3])} ${MESES[Number(m[2])-1]} ${m[1]}`:String(p||'N/D');};
  const fmtVerification=iso=>{if(!iso)return 'pendiente';const d=new Date(iso);return Number.isNaN(d.getTime())?iso:new Intl.DateTimeFormat('es-MX',{dateStyle:'long',timeStyle:'short'}).format(d);};
  function runtimeStatus(){
    const line=document.getElementById('update-status-line');
    if(line) line.textContent=`Última actualización: ${fmtVerification(UP.last_verification)}`;
  }

  function summary(){
    const pibVivienda=D.activity.pib_total.at(-1);
    const pibViviendaShare=D.activity.participation.at(-1);
    const enoeRows=(D.labor.enoe_quarterly||[]).filter(x=>/^20\d{2}-T[1-4]$/.test(x.period||''));
    const enoeLast=enoeRows.at(-1)||{period:'2026-T2',total:4841.023};
    document.getElementById('page-summary').innerHTML=U.pageHead('Resumen ejecutivo','Lectura rápida de los principales indicadores. Cada recuadro explica qué mide y muestra su unidad.','Cortes dinámicos según última observación disponible')+
    `<div class="kpis">
      ${U.kpi(`PIB de vivienda · ${D.activity.years?.at(-1)||'N/D'}`,F.mdp(pibVivienda),`${F.pct(pibViviendaShare)} del PIB nacional`,'mdp','El PIB (Producto Interno Bruto) de vivienda, estimado en la Cuenta Satélite de Vivienda de México, representa el valor económico generado por las actividades vinculadas con la vivienda.')}
      ${U.kpi(`Empleos en construcción · ENOE · ${fmtQuarter(enoeLast.period)}`,F.millionsFromThousands(enoeLast.total),'','millones de empleos en construcción','La ENOE (Encuesta Nacional de Ocupación y Empleo) aproxima el número de personas ocupadas cuya actividad principal es la construcción.')}
      ${U.kpi(`Índice SHF · ${fmtQuarter(D.prices.current?.yoy_period)||D.prices.current?.yoy_period||'N/D'}`,F.pct(D.prices.current?.yoy),'variación anual','porcentaje','El Índice SHF de Precios de la Vivienda, elaborado por la Sociedad Hipotecaria Federal (SHF), mide la apreciación o depreciación de viviendas adquiridas mediante crédito hipotecario con características comparables. El dato mostrado corresponde a su variación anual.')}
      ${U.kpi(`Vivienda propia + pagándose · ${D.conditions.tenure?.year||'N/D'}`,F.pct(D.conditions.tenure?.own_plus_paying),'del total de viviendas','porcentaje de viviendas','La ENIGH (Encuesta Nacional de Ingresos y Gastos de los Hogares) permite identificar la proporción de viviendas propias —incluidas las que aún se están pagando— respecto del total de viviendas habitadas.')}
    </div>
    <div class="grid">
      ${U.card('sum-employment','Empleo en construcción y ocupación total',`ENOE · millones de personas · trimestral · hasta ${fmtQuarter(enoeLast.period)}`,`<strong>Qué mide:</strong> compara la población ocupada en construcción (eje izquierdo) con la población ocupada total del país (eje derecho). <div class="note">Ambas series son observaciones trimestrales ENOE; no se mensualizan ni se interpolan.</div>`)}
      ${U.card('sum-shf','Precios de vivienda y costos de construcción','Variación anual (%) · SHF trimestral e ICC residencial mensual','<strong>Qué mide:</strong> compara la variación anual del Índice SHF de Precios de la Vivienda con el ICC residencial. <div class="note">El Índice SHF se publica trimestralmente; cada trimestre se ubica en su mes de cierre (marzo, junio, septiembre y diciembre), sin replicar valores en otros meses. El ICC conserva su frecuencia mensual.</div>')}
    </div>`;
  }
  function activity(){
    const s=D.summary;
    const pibQ=(D.activity.pib_construction_quarterly||[]).at(-1)||{period:'2026-T2',value_mdp:s.vab_construction_2q26_mdp,yoy:s.vab_construction_yoy_2q26,share:s.pib_construction_share_2q26};
    const igae=(D.activity.igae_monthly||[]).at(-1)||{period:'2026-06',index:s.igae_construction_jun26,yoy:s.igae_construction_yoy_jun26};
    const ifb=(D.activity.ifb_monthly||[]).at(-1)||{period:'2026-05',yoy:-5.4,mom:-7.9};
    const enecLast=(D.activity.enec_production||[]).at(-1);
    document.getElementById('page-activity').innerHTML=U.pageHead('Sector de construcción','Indicadores de construcción e inversión residencial respetando la frecuencia de publicación de cada fuente.','INEGI · mensual y trimestral')+
    `<div class="kpis">
      ${U.kpi(`VAB de construcción · ${fmtQuarter(pibQ.period)}`,F.billonesFromMillions(pibQ.value_mdp),`${F.pct(pibQ.share??s.pib_construction_share_2q26)} del PIB nacional`,'billones de pesos','El Valor Agregado Bruto (VAB) de la construcción aproxima el valor económico generado por el sector. La cifra se presenta en billones de pesos corrientes.')}
      ${U.kpi(`PIB de construcción · ${fmtQuarter(pibQ.period)} · variación anual real`,F.pct(pibQ.yoy),'respecto al mismo trimestre del año anterior','porcentaje','El PIB real de la construcción permite observar la evolución del volumen de actividad del sector descontando el efecto de los precios.')}
      ${U.kpi(`IGAE construcción · ${fmtMonth(igae.period)}`,F.pct(igae.yoy),'variación anual','porcentaje','El IGAE (Indicador Global de la Actividad Económica) permite seguir mensualmente la actividad de la construcción. ')}
      ${U.kpi(`IFB · construcción residencial · ${fmtMonth(ifb.period)}`,F.pct(ifb.yoy),'variación anual · dato mensual','porcentaje','La IFB (Inversión Fija Bruta) permite seguir mensualmente la inversión asociada con la construcción residencial. La cifra corresponde a la variación respecto al mismo mes del año anterior.')}
    </div>
    <div class="grid">
      ${U.dualCard('act-igae','act-igae-var','IGAE · construcción','Base 2018=100 · periodicidad mensual','<strong>Qué mide:</strong> seguimiento mensual de la actividad económica del sector construcción. <div class="note">La gráfica muestra exclusivamente la serie mensual del IGAE disponible en el dashboard, sin añadir una referencia anual de otra serie.</div>','Variación anual porcentual','Periodicidad mensual','Índice mensual con referencia 2018=100.','Variación porcentual respecto al mismo mes del año anterior.')}
      ${U.dualCard('act-vab','act-vab-var','VAB de construcción y subsectores','INEGI · PIB trimestral base 2018 · precios de 2018','<strong>Qué mide:</strong> VAB trimestral de Construcción y sus subsectores Edificación, Obras de ingeniería civil y Trabajos especializados. La gráfica de nivel usa dos ejes por la diferencia de escala.','Variación anual real','Porcentaje · mismo trimestre del año anterior','Eje izquierdo: Construcción y Edificación, en billones de pesos de 2018. Eje derecho: Obras de ingeniería civil y Trabajos especializados, también en billones.','Variación real de cada serie respecto al mismo trimestre del año anterior.')}
      ${U.card('act-ifb','IFB · construcción residencial','Índice 2019=100 · serie mensual ajustada estacionalmente','<strong>Qué mide:</strong> la IFB (Inversión Fija Bruta) residencial permite seguir mensualmente el volumen de inversión en construcción residencial. <div class="note">La gráfica presenta una aproximación de <b>ciclo-tendencia</b> mediante un suavizado centrado de 5 meses sobre la serie ajustada estacionalmente. Se utiliza para reducir la volatilidad mensual y hacer más visible el movimiento subyacente; no sustituye la serie oficial.</div>',true)}
      ${U.card('act-imai','IMAI · construcción','Índice 2021=100 · serie mensual ajustada estacionalmente','<strong>Qué mide:</strong> el IMAI (Indicador Mensual de la Actividad Industrial) permite observar mensualmente la evolución real de la actividad del sector construcción. <div class="note">La gráfica presenta una aproximación de <b>ciclo-tendencia</b> mediante un suavizado centrado de 5 meses sobre la serie ajustada estacionalmente. Se utiliza para atenuar variaciones mensuales de corto plazo y visualizar mejor la trayectoria subyacente; no sustituye la serie oficial.</div>',true)}
    </div>
    <div class="section-title"><h3>Actividad de las empresas constructoras · ENEC</h3></div>
    <div class="grid">
      ${U.card('act-enec-production','Valor de producción: edificación, obra pública y obra privada · tendencia-ciclo',`ENEC · índice 2018=100 · hasta ${fmtMonth(enecLast?.period)} · suavizado centrado de 5 meses`,'<strong>Cómo se clasifican las series:</strong> <b>edificación</b> identifica un <b>tipo de obra</b> (construcción de edificios residenciales y no residenciales). En cambio, <b>obra pública</b> y <b>obra privada</b> clasifican el valor de producción según el <b>sector contratante</b> que demanda o contrata la obra. Son dos criterios distintos aplicados a la actividad de las empresas constructoras.',true)}
    </div>`;
  }
  function labor(){
    const latestSalary=D.labor.salary_monthly[D.labor.salary_monthly.length-1];
    const firstSalary=D.labor.salary_monthly[0];
    const enoeQ=(D.labor.enoe_quarterly||[]).at(-1);
    const latestEdRow=D.labor.monthly_indices.at(-1);
    document.getElementById('page-labor').innerHTML=U.pageHead('Mercado laboral sector de construcción','Empleo, personal ocupado, horas trabajadas y remuneraciones, con distinción de fuentes y universos. La ENOE se consulta en su frecuencia trimestral.','ENOE trimestral · ENEC e IMSS mensuales')+
    `<div class="kpis">
      ${U.kpi(`ENOE · ${fmtQuarter(enoeQ?.period||'2026-T2')}`,F.millionsFromThousands(enoeQ?.total??4841.023),'millones de empleos en construcción','','La ENOE (Encuesta Nacional de Ocupación y Empleo) aproxima la población ocupada cuya actividad principal es la construcción.')}
      ${(()=>{const g=(D.labor.imss_monthly||[]).at(-1); return U.kpi(`IMSS · construcción · ${fmtMonth(g?.period)}`,g?F.millionsFromThousands(g.construction):'N/D','millones de trabajadores afiliados al IMSS en construcción','','Número de puestos de trabajo afiliados al IMSS correspondientes al sector construcción en el último corte sectorial disponible.');})()}
      ${U.kpi(`SBC mensual promedio · construcción · ${fmtMonth(latestSalary?.period)}`,F.daily(latestSalary.daily*30.4),'salario registrado ante el IMSS','pesos corrientes por mes','El SBC (Salario Base de Cotización) es el salario diario registrado ante el IMSS para calcular cuotas y prestaciones; no equivale al ingreso laboral promedio de toda la población ocupada. El cálculo mensualiza el SBC diario multiplicando por 30.4 días.')}
      ${U.kpi(`Personal ocupado ENEC · edificación · ${fmtMonth(latestEdRow?.period)}`,(()=>{const a=D.labor.monthly_indices||[];const c=latestEdRow?.empl_edif;const y=latestEdRow?a.find(x=>x.period===`${Number(latestEdRow.period.slice(0,4))-1}${latestEdRow.period.slice(4)}`)?.empl_edif:null;return (c!=null&&y)?F.pct((c/y-1)*100):'N/D';})(),'variación anual','porcentaje respecto al mismo mes del año anterior','La ENEC (Encuesta Nacional de Empresas Constructoras) permite observar cómo cambia el personal ocupado en las empresas dedicadas a edificación; sus índices toman 2018=100 como referencia.')}
    </div>
    <div class="grid">
      ${U.dualCard('lab-enoe','lab-enoe-var','Empleos en construcción','Miles de empleos · ENOE · periodicidad trimestral','<strong>Qué mide:</strong> la ENOE aproxima las personas ocupadas cuya actividad principal es la construcción.','Variación anual porcentual','Porcentaje · mismo trimestre del año anterior','Se muestran únicamente trimestres observados; el nivel se expresa en miles de empleos.','Variación porcentual respecto al mismo trimestre del año anterior.')}
      ${U.dualCard('lab-imss','lab-imss-var','Trabajadores afiliados al IMSS',D.labor.imss_monthly?.some(x=>x.edification!=null)?'Millones de trabajadores afiliados · construcción y edificación · periodicidad mensual':'Millones de trabajadores afiliados · construcción · periodicidad mensual','<strong>Qué mide:</strong> número de trabajadores afiliados al Instituto Mexicano del Seguro Social (IMSS) dentro del sector construcción.','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Muestra los trabajadores afiliados cada mes, expresados en millones.','Muestra la variación porcentual respecto al mismo mes del año anterior.')}
      ${U.dualCard('lab-personal','lab-personal-var','Índice de personal ocupado','Construcción vs. edificación · ENEC · Base 2018=100 · periodicidad mensual','<strong>Qué mide:</strong> la ENEC permite observar <b>mensualmente</b> cómo cambia el personal ocupado en el total de empresas constructoras y específicamente en edificación. Los índices toman <b>2018=100</b> como periodo de referencia.','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Nivel mensual del índice con referencia 2018=100.','Variación porcentual respecto al mismo mes del año anterior.')}
      ${U.dualCard('lab-enec-worker-type','lab-enec-worker-type-var','Índice de personal ocupado por tipo de trabajador','ENEC · índices oficiales · base 2018=100 · periodicidad mensual','<strong>Qué mide:</strong> muestra la trayectoria del personal ocupado por tipo de trabajador en las empresas constructoras e identifica si el movimiento se concentra en el <b>personal total</b>, los <b>obreros</b> o los <b>empleados administrativos, contables y de dirección</b>. <div class="note">Se utilizan los índices oficiales de ENEC, con referencia <b>2018=100</b>, y sus variaciones anuales respecto al mismo mes del año anterior.</div>','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Nivel mensual del índice oficial para cada tipo de trabajador.','Variación porcentual respecto al mismo mes del año anterior, calculada a partir del índice oficial.') }
    
      ${U.dualCard(
        'lab-hours',
        'lab-hours-var',
        'Índice de horas trabajadas · tendencia suavizada',
        'Construcción vs. edificación · ENEC · Base 2018=100 · suavizado centrado de 5 meses',
        '<strong>Qué mide:</strong> la evolución mensual del índice de horas trabajadas en construcción y edificación. Se aplica un suavizado centrado de cinco meses a las series originales de ENEC.',
        'Variación anual porcentual',
        'Porcentaje · mismo mes del año anterior',
        'Índices base 2018=100, con suavizado centrado de cinco meses.',
        'Variación porcentual anual calculada sobre los índices suavizados.'
      )}

      ${U.dualCard(
        'lab-rem',
        'lab-rem-var',
        'Índice de remuneraciones medias por persona ocupada · tendencia suavizada',
        'Construcción vs. edificación · ENEC · Base 2018=100 · suavizado centrado de 5 meses',
        '<strong>Qué mide:</strong> la evolución mensual de las remuneraciones en construcción y edificación, según los índices ENEC disponibles. Se aplica un suavizado centrado de cinco meses.',
        'Variación anual porcentual',
        'Porcentaje · mismo mes del año anterior',
        'Índices base 2018=100, con suavizado centrado de cinco meses.',
        'Variación porcentual anual calculada sobre los índices suavizados.'
      )}

      ${U.dualCard('lab-salary','lab-salary-var','Salario promedio en construcción',`SBC mensual equivalente · IMSS · ${fmtMonth(firstSalary?.period)}–${fmtMonth(latestSalary?.period)}`,'<strong>Qué mide:</strong> el Salario Base de Cotización promedio registrado ante el IMSS, expresado como equivalente mensual (SBC diario × 30.4).','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Muestra el SBC mensual equivalente en pesos corrientes; no es un salario contractual mensual.','Muestra la variación porcentual respecto al mismo mes del año anterior.')}
    </div>`;
  }
  function production(){
    const c=D.production.current;
    const enecMM=(D.activity.enec_edification_mm||[]);
    const enecMMLast=enecMM.at(-1);
    const pvb=D.production.pvb||{period:null,rows:[],source:null,url:null};
    const pvbMap=new Map((pvb.rows||[]).map(x=>[x.stage,x]));
    const pvbContracted=pvbMap.get('Contratadas')?.housing;
    const pvbConstruction=pvbMap.get('En construcción')?.housing;
    const pvbDelivered=pvbMap.get('Entregadas')?.housing;
    const pvbTarget=pvbMap.get('Meta sexenal')?.housing;
    const pvbSource=pvb.source||'Fuente oficial del Programa de Vivienda para el Bienestar';
    const pvbSourceHtml=pvb.url?`<a href="${pvb.url}" target="_blank" rel="noopener">${pvbSource}</a>`:pvbSource;
    const ruvCutoff=c.periods?.ruv_inventory||c.ruv_inventory_period||null;
    const financingCutoff=c.periods?.financing||c.financing_period||null;
    const pvbConaviCutoff=c.periods?.pvb||c.pvb_conavi_period||pvb.period||null;
    const flowYears=(D.production.years||[]).filter(Number.isFinite);
    const flowRange=flowYears.length?`${flowYears[0]}–${flowYears.at(-1)}`:'histórico disponible';
    document.getElementById('page-production').innerHTML=U.pageHead('Producción de vivienda','Indicadores para seguir el flujo de producción de vivienda, desde el registro hasta el inicio y la terminación de obra. Aquí se concentra también la lectura del PIB de vivienda.','Cuenta Satélite de Vivienda · ENEC · RUV · SNIIV · CONAVI · PVB')+
    `<div class="kpis">
      ${U.kpi(`Inventario activo RUV · ${fmtDate(ruvCutoff)}`,F.number(c.ruv_inventory_jun26,0),'viviendas activas al último corte','viviendas',`El SNIIV reporta el inventario de vivienda del RUV con corte al <b>${fmtDate(ruvCutoff)}</b>. Es un saldo de viviendas vigentes dentro de su ciclo de vida y no debe interpretarse como viviendas registradas únicamente durante junio.`)}
      ${U.kpi(`Financiamientos registrados · ${fmtDate(financingCutoff)}`,F.number(c.financing_total_jun26,0),'acciones al corte','acciones',`El SNIIV (Sistema Nacional de Información e Indicadores de Vivienda) reúne las acciones de financiamiento reportadas con corte al <b>${fmtDate(financingCutoff)}</b>; una acción no necesariamente equivale a una vivienda nueva terminada.`)}
      ${U.kpi(`Viviendas CONAVI vinculadas al PVB · ${fmtDate(pvbConaviCutoff)}`,F.number(c.pvb_housing_jun15_26,0),'programadas/en proceso al último corte','viviendas',`Corresponde a la vertiente CONAVI del PVB al último corte disponible: viviendas distribuidas en predios que se encontraban en contratación, trabajos preliminares, obra o elaboración de proyectos al corte. Se mantiene separada del avance agregado nacional del PVB mostrado en la gráfica inferior.`)}
      ${U.kpi(`Suelo CONAVI asociado al PVB · ${fmtDate(pvbConaviCutoff)}`,F.number(c.pvb_hectares_jun15_26,0),`${F.number(c.pvb_predios_jun15_26,0)} predios`,'hectáreas',`Superficie asociada a los predios incorporados por CONAVI al PVB, con corte al ${fmtDate(pvbConaviCutoff)}.`)}
    </div>
    <div class="grid">
      ${U.card('act-pib','PIB de vivienda por componentes','Billones de pesos corrientes · periodo dinámico','<strong>Qué mide:</strong> el PIB (Producto Interno Bruto) de vivienda integra el valor económico generado por edificación, adquisición, uso y actividades de regulación y fomento asociadas con la vivienda. <div class="note">Eje Y: billones de pesos corrientes.</div>',true)}
    </div>
    <div class="grid">
      ${U.card('act-share','Participación del PIB de vivienda',`Porcentaje del PIB nacional · ${D.activity.years?.[0]||'N/D'}–${D.activity.years?.at(-1)||'N/D'}`,'<strong>Qué mide:</strong> muestra qué proporción del PIB nacional corresponde a las actividades de vivienda incluidas en la Cuenta Satélite de Vivienda de México (CSVM).',false)}
      ${U.card('prod-enec-housing-activity','Actividad productiva de vivienda',`Variación mensual real · ENEC · periodicidad mensual · ${fmtMonth(enecMMLast?.period)}`,'<strong>Qué permite ver:</strong> muestra el cambio mensual real de la producción de edificación de las empresas constructoras, con cifras desestacionalizadas. <div class="note">La serie llega al último mes realmente disponible en el archivo ENEC y no usa una etiqueta fija si el corte cambia.</div>',false)}
      ${U.card('prod-pvb','Avance del Programa de Vivienda para el Bienestar (PVB)',`Avance acumulado del programa al ${fmtDate(pvb.period)} · referencia: meta sexenal`,`<strong>Qué muestra:</strong> las cifras corresponden al <b>avance acumulado del PVB al ${fmtDate(pvb.period)}</b>; no son viviendas producidas exclusivamente durante el año. ${Number.isFinite(pvbContracted)?`A ese corte se reportan <b>${F.number(pvbContracted,0)}</b> viviendas contratadas`:''}${Number.isFinite(pvbConstruction)?`, <b>${F.number(pvbConstruction,0)}</b> en construcción`:''}${Number.isFinite(pvbDelivered)?` y <b>${F.number(pvbDelivered,0)}</b> entregadas`:''}. <div class="note"><b>Importante:</b> las etapas están relacionadas y no deben sumarse entre sí.${Number.isFinite(pvbTarget)?` La meta sexenal registrada en el archivo es de <b>${F.number(pvbTarget,0)} viviendas</b>.`:''} Fuente: ${pvbSourceHtml}. <br><b>Actualización:</b> la gráfica lee <code>pvb_avance.csv</code> y selecciona automáticamente el periodo más reciente.</div>`,false)}
      ${U.card('prod-ruv-total','Producción anual de vivienda','Viviendas terminadas con DTU · RUV · histórico disponible','<strong>Qué mide:</strong> número de viviendas que obtuvieron el <b>Dictamen Técnico Único (DTU)</b>, confirmando su habitabilidad. <div class="note">RUV = Registro Único de Vivienda; SNIIV = Sistema Nacional de Información e Indicadores de Vivienda. Eje Y: miles de viviendas producidas.</div>')}
      ${U.dualCard('prod-flow','prod-flow-var','Registro, inicio y terminación de vivienda',`Miles de viviendas · ${flowRange}`,'<strong>Qué mide:</strong> el RUV (Registro Único de Vivienda) permite seguir distintas etapas del flujo de producción: registro, inicio de obra y terminación/producción.','Variación anual porcentual','Porcentaje respecto al año anterior','Muestra el número de viviendas en cada etapa, expresado en miles.','Muestra la variación porcentual respecto al año anterior para cada etapa.')}
    </div>
    <div class="section-title"><h3>Características de la vivienda producida</h3><p id="ruv-characteristics-status">RUV/SNIIV · cargando histórico disponible…</p></div>
    <div class="grid">
      ${U.card('prod-ruv-segment','Composición de la vivienda producida por segmento','Participación porcentual · RUV · clasificación por valor en UMA','<strong>Qué mide:</strong> muestra la composición de la producción por rango de valor de la vivienda. <b>Económica:</b> hasta 118 UMA; <b>Popular B1:</b> más de 118 y hasta 128 UMA; <b>Popular B2:</b> más de 128 y hasta 158 UMA; <b>Popular B3:</b> más de 158 y hasta 200 UMA; <b>Tradicional:</b> más de 200 y hasta 350 UMA; <b>Media-residencial:</b> agrupa en este histórico las viviendas de mayor valor, por encima del rango Tradicional. Los montos equivalentes en pesos cambian con la UMA vigente.',true)}
    </div>`;
  }
  function prices(){
    const p=D.prices.current;
    const iccMonthly=D.prices.icc_monthly||[];
    const inppMonthly=D.prices.inpp_construction_monthly||[];
    const inppConstruction=[...inppMonthly,...(D.prices.inpp_construction_latest||[])].filter(x=>x.period&&Number.isFinite(x.yoy)).sort((a,b)=>String(a.period).localeCompare(String(b.period))).at(-1)||null;
    const iccLevelMap=new Map(iccMonthly.map(x=>[x.period,x.general]));
    const iccDerived=iccMonthly.map(x=>{const [y,m]=String(x.period).split('-');const prev=iccLevelMap.get(`${Number(y)-1}-${m}`);return Number.isFinite(x.general)&&Number.isFinite(prev)&&prev!==0?{period:x.period,yoy:(x.general/prev-1)*100}:null;}).filter(Boolean);
    const iccMergedMap=new Map(iccDerived.map(x=>[x.period,x]));
    (D.prices.icc_yoy_monthly||[]).forEach(x=>iccMergedMap.set(x.period,x));
    const iccDisplay=[...iccMergedMap.values()].sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    const iccFirst=iccDisplay[0], iccLast=iccDisplay.at(-1);
    const iccLevelFirst=iccMonthly[0], iccLevelLast=iccMonthly.at(-1);
    const inppFirst=inppMonthly[0], inppLast=inppMonthly.at(-1);
    document.getElementById('page-prices').innerHTML=U.pageHead('Precios y costos de vivienda','Precios de vivienda con crédito hipotecario, dinámica del Índice SHF, costos de construcción y diferencias territoriales.','SHF · INEGI · Banco de México')+
    `<div class="kpis">
      ${U.kpi(`Precio promedio de vivienda · ${p.period||D.prices.shf_state_price_period||'N/D'}`,F.money(p.avg_price),'valor promedio de avalúo','pesos corrientes','La Sociedad Hipotecaria Federal (SHF) reporta el valor promedio de avalúo de viviendas adquiridas mediante crédito hipotecario; no representa el precio de todas las viviendas del país.')}
      ${U.kpi(`Precio mediano de vivienda · ${p.period||D.prices.shf_state_price_period||'N/D'}`,F.money(p.median_price),'50% de las operaciones se ubicó por debajo','pesos corrientes','La Sociedad Hipotecaria Federal (SHF) utiliza la mediana para identificar el valor que divide las operaciones en dos mitades; es menos sensible a valores extremos que el promedio.')}
      ${U.kpi(`Índice SHF · ${fmtQuarter(D.prices.current?.yoy_period)||D.prices.current?.yoy_period||'N/D'}`,F.pct(p.yoy),'variación respecto al mismo trimestre del año anterior','porcentaje','El Índice SHF de Precios de la Vivienda mide la apreciación o depreciación de viviendas adquiridas mediante crédito hipotecario con características comparables. El dato mostrado es la variación anual del índice.')}
      ${U.kpi(`INPP construcción · ${fmtMonth(inppConstruction?.period)}`,F.pct(inppConstruction?.yoy),'variación respecto al mismo mes del año anterior','porcentaje','El INPP (Índice Nacional de Precios Productor) permite seguir la evolución de los precios productor de la actividad de construcción. El recuadro muestra la variación anual de la última observación mensual disponible.')}
    </div>
    <div class="grid">
      ${U.dualCard('price-shf-index','price-shf','Índice SHF de Precios de la Vivienda','SHF · índice trimestral · base 2017=100','<strong>Qué mide:</strong> evolución del Índice SHF nacional de precios de la vivienda adquirida mediante crédito hipotecario. <div class="note">Se muestra únicamente el <b>nivel oficial</b> publicado por SHF; no se inventan niveles a partir de variaciones porcentuales.</div>','Variación anual porcentual del Índice SHF','Porcentaje · respecto al mismo trimestre del año anterior','Nivel trimestral original publicado por SHF, base 2017=100.','Tasa anual publicada por SHF; cortes trimestrales sin mensualizar.') }
      ${U.dualCard('price-costs','price-costs-var','Índice de Costo de la Construcción (ICC)',iccMonthly.length?`Construcción residencial por ciudad (antes INCEVIS) · Nacional · base julio 2025=100 · ${fmtMonth(iccLevelFirst?.period)}–${fmtMonth(iccLevelLast?.period)}`:'Sin serie mensual oficial de nivel cargada','<strong>Qué mide:</strong> evolución mensual del índice nacional de construcción residencial por ciudad (antes INCEVIS).','Variación anual porcentual',iccDisplay.length?`Porcentaje · mismo mes del año anterior · ${fmtMonth(iccFirst?.period)}–${fmtMonth(iccLast?.period)}`:'Sin variación anual mensual disponible','Nivel del índice, base julio 2025=100.','')}
      ${U.dualCard('price-inpp-components','price-inpp-components-var','Subíndices que integran el ICC','Materiales · alquiler de maquinaria · mano de obra · base julio 2025=100','<strong>Qué mide:</strong> componentes nacionales del índice de construcción residencial por ciudad (antes INCEVIS).','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Nivel mensual de los tres subíndices.','Variación anual respecto al mismo mes del año anterior.')}
      ${U.dualCard('price-housing-components','price-housing-components-var','INPP · construcción','Producción total según actividad económica · Construcción · base julio 2025=100','<strong>Qué mide:</strong> evolución mensual de los precios productor de la Construcción.','Variación anual porcentual','Porcentaje · mismo mes del año anterior','Nivel mensual del INPP de construcción.','Variación anual respecto al mismo mes del año anterior.')}
      ${U.card('price-inpp-edification','INPP · edificación','Edificación total, residencial y no residencial · base julio 2025=100','<strong>Qué mide:</strong> compara los índices de Edificación, Edificación residencial y Edificación no residencial.')}
      ${U.card('price-financing','Costo de financiamiento / crédito puente',D.prices.inpp_years?.length?'Serie anual automatizada desde 2018':'Sin histórico de financiamiento cargado','<strong>Qué mide:</strong> referencia histórica del costo financiero asociado al desarrollo de vivienda. <div class="note"><strong>Fuente:</strong> CNBV, Series Históricas de Banca Múltiple. La automatización conserva el histórico validado y actualiza la tasa de crédito puente cuando el libro oficial permite identificarla de forma segura.</div>')}
    </div>
    <div class="section-title"><h3>Precio por entidad federativa</h3></div>
    <div class="info-strip two">
      ${info('SHF · distribución del precio estatal',`Precio de avalúo por entidad para viviendas adquiridas mediante crédito hipotecario. El detalle corresponde a <b>${D.prices.shf_state_price_period||'N/D'}</b> y muestra promedio, cuantil 25, mediana y cuantil 75. Unidad: <b>pesos corrientes por vivienda</b>.`)}
      ${info('Cómo leerlo','Sin una entidad seleccionada se muestra la distribución nacional. Haz clic en un círculo o en una fila para seleccionar un estado. La selección sólo actualiza y centra visualmente el estado; la página no se desplaza hacia el listado y la distribución permanece visible.')}
    </div>
    <div class="map-grid">
      <section class="map-box"><div class="card-head"><h3>Mapa SHF · precio promedio por estado</h3><p>Pesos corrientes por vivienda · ${D.prices.shf_state_price_period||'N/D'} · haz clic en una entidad</p></div><div id="mx-map" class="map-container"><div class="map-loading">El mapa se carga al abrir esta sección.</div></div></section>
      <section class="state-detail-box"><div class="card-head"><h3>Distribución del precio</h3><p>Promedio y cuantiles del valor de avalúo SHF</p></div><div id="state-detail" class="state-detail"></div></section>
    </div>
    <section class="table-box state-price-table-box">
      <div class="card-head state-table-head"><div><h3>Precio promedio por entidad</h3><p>Sociedad Hipotecaria Federal (SHF) · pesos corrientes por vivienda · ${D.prices.shf_state_price_period||'N/D'}</p></div><label class="sort-control">Ordenar<select id="state-price-sort"><option value="alpha">Entidad · A–Z</option><option value="price-asc">Precio · menor a mayor</option><option value="price-desc">Precio · mayor a menor</option></select></label></div>
      <div class="state-table-wrap"><table class="state-table"><thead><tr><th>Entidad</th><th>Precio promedio</th></tr></thead><tbody id="state-price-table-body"></tbody></table></div>
    </section>`;
  }
  function conditions(){
    const t=D.conditions.tenure;
    const histYears=D.conditions.history_years||[];
    const condYear=histYears.length?histYears.at(-1):(D.conditions.summary_year||t?.year||'N/D');
    const tenureYear=t?.year||condYear;
    const firstYear=(D.conditions.tenure_history?.years||histYears||[])[0]||2016;
    document.getElementById('page-conditions').innerHTML=U.pageHead('Condiciones habitacionales','Indicadores para entender la tenencia de la vivienda y las carencias habitacionales.',`INEGI · ENIGH · CONAVI · ${firstYear}–${Math.max(Number(condYear)||0,Number(tenureYear)||0)||'N/D'}`)+
    `<div class="kpis">
      ${U.kpi(`Vivienda propia + pagándose · ${D.conditions.tenure?.year||'N/D'}`,F.pct(t.own_plus_paying),'del total de viviendas habitadas','porcentaje de viviendas','La ENIGH (Encuesta Nacional de Ingresos y Gastos de los Hogares) permite identificar la proporción de viviendas propias —incluidas las que aún se están pagando— respecto del total de viviendas habitadas.')}
      ${U.kpi(`Vivienda rentada · ${tenureYear}`,F.pct(t.rented),'del total de viviendas habitadas','porcentaje de viviendas','La ENIGH permite identificar la proporción de viviendas cuyos ocupantes pagan una renta por habitarlas.')}
      ${U.kpi(`Carencia por calidad y espacios · ${condYear}`,F.pct(D.conditions.deprivation.quality_space_2024),'de la población presenta esta carencia','porcentaje de la población','La carencia por calidad y espacios identifica población que habita viviendas con materiales, hacinamiento u otras condiciones insuficientes conforme a la medición de pobreza multidimensional.')}
      ${U.kpi(`Carencia por servicios básicos · ${condYear}`,F.pct(D.conditions.deprivation.basic_services_2024),'de la población presenta esta carencia','porcentaje de la población','La carencia por acceso a servicios básicos identifica población que habita viviendas sin acceso suficiente a servicios considerados en la medición de pobreza multidimensional.')}
    </div>
    <div class="grid">
      ${U.card('cond-history','Histórico de carencias habitacionales',`Porcentaje de la población · ${histYears.join(', ')}`,'<strong>Qué mide:</strong> evolución de la carencia por calidad y espacios y de la carencia por acceso a servicios básicos. <div class="note">Los levantamientos son bienales; se muestran únicamente los años observados, sin interpolación.</div>')}
      ${U.card('cond-needs-history',`Déficit cualitativo · ${D.conditions.summary_year||condYear}`,'Componentes del déficit · porcentaje de viviendas','<strong>Qué mide:</strong> porcentaje de viviendas que presentan necesidades de mejoramiento por <b>materiales</b>, <b>espacios</b> o <b>servicios</b>. <div class="note">Una misma vivienda puede presentar más de un tipo de necesidad; por ello las barras no deben sumarse. Esta gráfica se mantiene separada de las carencias de población.</div>')}
      ${U.card('cond-tenure-compare','Evolución de la tenencia de la vivienda',`Porcentaje de viviendas · ENIGH · ${(D.conditions.tenure_history?.years||[]).join(', ')}`,'<strong>Qué mide:</strong> composición histórica de la tenencia en cuatro grupos comparables: propia totalmente pagada, propia pagándose, rentada y otros. <div class="note"><b>Otros</b> agrupa prestada, intestada o en litigio y otra situación. Las barras suman 100% en cada levantamiento.</div>')}
      ${U.card('cond-tenure','Tenencia de la vivienda',`Porcentaje de viviendas · ENIGH ${tenureYear}`,'<strong>Qué mide:</strong> distribución de viviendas en cuatro grupos. <b>Otros</b> agrupa viviendas prestadas, intestadas o en litigio y otras situaciones reportadas por la ENIGH.')}
      ${U.card('cond-tenure-rural-urban','Tenencia por ámbito rural y urbano',`Porcentaje de viviendas ocupadas · ENIGH ${tenureYear}`,'<strong>Qué mide:</strong> compara la composición de la tenencia por ámbito rural y urbano en cuatro categorías: propia totalmente pagada, propia pagándose, rentada y otros. <div class="note">Rural: menos de 2,500 habitantes; urbano: 2,500 o más. Se presentan cuatro categorías: propia totalmente pagada, propia pagándose, rentada y otros.</div>')}
      <div class="conditions-last-pair">
        ${U.card('cond-deprivation',`Carencias habitacionales · ${condYear}`,`Porcentaje de la población · ${condYear}`,'<strong>Cómo leerlo:</strong> las dos barras muestran exclusivamente el porcentaje de <b>personas</b> con carencia por calidad y espacios de la vivienda y con carencia por acceso a servicios básicos.')}
        ${U.card('cond-materials',`Materiales inadecuados · ${D.conditions.summary_year||condYear}`,`Porcentaje de viviendas · CONAVI ${D.conditions.summary_year||condYear}`,'<strong>Qué mide:</strong> porcentaje de viviendas que presentan materiales inadecuados en <b>muros</b>, <b>techos</b> o <b>pisos</b>. Cada barra corresponde a un componente distinto y no representa una parte del total de la barra vecina.',true)}
      </div>
    </div>`;
  }
  function methodology(){
    document.getElementById('page-methodology').innerHTML=U.pageHead('Metodología','Definiciones operativas, unidades, reglas de comparabilidad y criterios de actualización.','Sin interpolaciones')+
    `<div class="method-grid">
      ${method('PIB y VAB','El PIB (Producto Interno Bruto) y el VAB (Valor Agregado Bruto) miden valor económico. El PIB incorpora además impuestos netos sobre productos al agregado de los VAB. Las unidades se indican en cada visualización.')}
      ${method('IGAE, IFB e IMAI','El IGAE (Indicador Global de la Actividad Económica), la IFB (Inversión Fija Bruta) y el IMAI (Indicador Mensual de la Actividad Industrial) son conceptos diferentes y se muestran por separado. En IFB e IMAI la visualización aplica un promedio móvil centrado de cinco meses como aproximación de ciclo-tendencia para reducir la volatilidad de corto plazo y facilitar la lectura del movimiento subyacente; en los extremos se utilizan las observaciones disponibles.')}
      ${method('Población ocupada ENOE','La ENOE (Encuesta Nacional de Ocupación y Empleo) Universo: personas ocupadas cuya rama de actividad es construcción. Unidad principal: millones o miles de personas según la visualización.')}
      ${method('Índices ENEC','La ENEC (Encuesta Nacional de Empresas Constructoras) Personal ocupado, horas trabajadas y remuneraciones medias se muestran como índices Base 2018=100 para construcción y edificación.')}
      ${method('Empleo y salario IMSS','IMSS = Instituto Mexicano del Seguro Social. El tablero denomina empleos registrados a los puestos afiliados del sector construcción; administrativamente son registros de puestos y no personas únicas de la ENOE. SBC = Salario Base de Cotización; se expresa en pesos corrientes por mes.')}
      ${method('Producción de vivienda','RUV = Registro Único de Vivienda; SNIIV = Sistema Nacional de Información e Indicadores de Vivienda; CONAVI = Comisión Nacional de Vivienda; PVB = Programa de Vivienda para el Bienestar. En la API de Producción, una vivienda producida es la que obtuvo el Dictamen Técnico Único (DTU) en el periodo de referencia, confirmando habitabilidad. Las distribuciones por tipo y superficie conservan la clasificación de SNIIV/RUV; el último año puede ser parcial.')}
      ${method('Precios SHF','La SHF (Sociedad Hipotecaria Federal) El Índice SHF mide la apreciación de vivienda con crédito hipotecario. Los precios promedio estatales corresponden a avalúos y se expresan en pesos corrientes por vivienda.')}
      ${method('Tenencia y carencias','ENIGH = Encuesta Nacional de Ingresos y Gastos de los Hogares. Tenencia se expresa como porcentaje de viviendas. Las carencias habitacionales se expresan como porcentaje de la población.')}
      ${method('Variaciones anuales','En series anuales se compara con el año anterior. En series mensuales se compara el mismo mes del año previo. En levantamientos bienales de condiciones habitacionales se muestra el cambio promedio anual en puntos porcentuales entre observaciones.')}
      ${method('Comparabilidad','No se suman ni homologan universos diferentes: ENOE = personas ocupadas; IMSS = empleos/puestos registrados; ENEC = índices; SHF = avalúos hipotecarios. Cada visualización conserva su universo y unidad.')}
    </div>`;
  }

  function sources(){
    document.getElementById('page-sources').innerHTML=U.pageHead('Fuentes','Fuentes primarias y uso dentro del tablero.','Consulta y validación documental')+
    `<table class="source-table"><thead><tr><th>Bloque</th><th>Fuente principal</th><th>Uso</th></tr></thead><tbody>
      <tr><td>Actividad económica</td><td>Instituto Nacional de Estadística y Geografía (INEGI)</td><td>Cuenta Satélite de Vivienda, Producto Interno Bruto (PIB), Valor Agregado Bruto (VAB), Indicador Global de la Actividad Económica (IGAE), Inversión Fija Bruta (IFB) e Indicador Mensual de la Actividad Industrial (IMAI).</td></tr>
      <tr><td>Mercado laboral</td><td>INEGI: Encuesta Nacional de Ocupación y Empleo (ENOE) y Encuesta Nacional de Empresas Constructoras (ENEC); Instituto Mexicano del Seguro Social (IMSS)</td><td>Población ocupada, formalidad, índices de personal/horas/remuneraciones y Salario Base de Cotización (SBC) mensual equivalente (SBC diario × 30.4).</td></tr>
      <tr><td>Producción</td><td>Registro Único de Vivienda (RUV) / Sistema Nacional de Información e Indicadores de Vivienda (SNIIV) / Comisión Nacional de Vivienda (CONAVI)</td><td>Registro, inicio, producción, inventario, tipo de vivienda (horizontal/vertical), superficie construida y avances del Programa de Vivienda para el Bienestar (PVB).</td></tr>
      <tr><td>Precios y costos de vivienda</td><td>Sociedad Hipotecaria Federal (SHF) / Instituto Nacional de Estadística y Geografía (INEGI) / Banco de México</td><td>Variación y nivel de precios de vivienda, costos de construcción, series mensuales del ICC e INPP y precio promedio estatal de avalúo.</td></tr>
      <tr><td>Condiciones habitacionales</td><td>INEGI: Encuesta Nacional de Ingresos y Gastos de los Hogares (ENIGH) / pobreza multidimensional; CONAVI</td><td>Tenencia, histórico de carencias de la población desde 2016 hasta el último levantamiento disponible y materiales de la vivienda.</td></tr>
    </tbody></table>
    <div class="footer-note"><strong>Nota:</strong> los CSV incluidos permiten revisar los valores utilizados. El detalle estatal SHF se incorpora en <code>shf_precios_entidad.csv</code> con promedio y cuantiles 25, 50 y 75; la serie del ICC residencial por ciudad se agregó en <code>icc_ciudad_historico_anual.csv</code>; y el histórico trimestral de ENOE puede completarse automáticamente desde Data México cuando el archivo local no trae toda la serie.</div>`;
  }

  function updates(){
    const sourceRows=(UP.sources||[]).map(s=>`<tr><td>${s.label}</td><td>${s.provider||''}</td><td>${s.published_latest_period||'N/D'}</td><td>${s.unit||'N/D'}</td><td>${s.status||'N/D'}</td></tr>`).join('');
    const stats=(UP.validation||{}).stats||{};
    document.getElementById('page-updates').innerHTML=U.pageHead('Cortes de información','Referencia temporal y trazabilidad de los indicadores mostrados en el tablero.','Actualización por fuente')+
    `<div class="info-strip">
      ${info('Última actualización',`<b>${fmtVerification(UP.last_verification)}</b>.`)}
      ${info('Control de publicación','Una descarga nueva no sustituye un dato aprobado hasta pasar validaciones de estructura, unidad, universo y consistencia.')}
      ${info('Validación de archivos',`Observaciones en base maestra: <b>${stats.series_rows??'N/D'}</b>. Entidades del mapa: <b>${stats.map_entities??'N/D'}</b>. Errores: <b>${stats.errors??0}</b>; advertencias: <b>${stats.warnings??0}</b>.`)}
    </div>
    <table class="source-table"><thead><tr><th>Indicador / fuente</th><th>Proveedor</th><th>Último corte publicado</th><th>Unidad</th><th>Estado técnico</th></tr></thead><tbody>${sourceRows}</tbody></table>`;
  }

  function setRuvLoading(text){const el=document.getElementById('ruv-characteristics-status');if(el)el.textContent=text;}
  function updateRuvStatus(data){
    const el=document.getElementById('ruv-characteristics-status'); if(!el)return;
    const p=data&&data.latest_period;
    const rows=data?.total?.annual||[];
    const years=rows.map(r=>Number(r.year)).filter(Number.isFinite);
    const range=years.length?`${Math.min(...years)}–${Math.max(...years)}`:'periodo no identificado';
    if(data?.fallback){el.textContent=`RUV · histórico local ${range}${p?` · último corte ${p}`:''} · verificando actualización SNIIV`;return;}
    el.textContent=`SEDATU · SNIIV/RUV · histórico cargado ${range}${p?` · último corte ${p}`:''}`;
  }
  window.DashboardApp={setRuvLoading,updateRuvStatus};

  function nav(){
    document.querySelectorAll('.nav button').forEach(btn=>btn.addEventListener('click',()=>{
      document.querySelectorAll('.nav button').forEach(b=>b.classList.remove('active')); btn.classList.add('active');
      document.querySelectorAll('.page').forEach(p=>p.classList.remove('active')); document.getElementById(`page-${btn.dataset.page}`).classList.add('active');
      document.getElementById('sidebar').classList.remove('open');
      setTimeout(()=>{
        // Chart.js puede inicializar un canvas dentro de una sección oculta
        // con ancho/alto 0. Al activar la página, volvemos a renderizar las
        // gráficas para que se calculen con las dimensiones reales.
        if(window.DashboardCharts) DashboardCharts.render();
        if(btn.dataset.page==='production' && window.DashboardCharts?.renderRuv && window.RUV_PRODUCTION) DashboardCharts.renderRuv(window.RUV_PRODUCTION);
        if(window.Chart&&Chart.instances) Object.values(Chart.instances).forEach(c=>c.resize());
        if(btn.dataset.page==='prices'&&window.DashboardMap) DashboardMap.render();
      },100);
      window.scrollTo({top:0,behavior:'smooth'});
    }));
    document.getElementById('mobileMenu').addEventListener('click',()=>document.getElementById('sidebar').classList.toggle('open'));
  }

  async function init(){
    if(window.DashboardDataLoader?.loadPeriodic) await window.DashboardDataLoader.loadPeriodic();
    summary();activity();labor();production();prices();conditions();methodology();sources();updates();nav();runtimeStatus();
    if(window.DashboardCharts)DashboardCharts.render();
    if(window.DashboardCharts?.renderRuv && window.RUV_PRODUCTION) DashboardCharts.renderRuv(window.RUV_PRODUCTION);
    if(window.DashboardApp?.updateRuvStatus && window.RUV_PRODUCTION) window.DashboardApp.updateRuvStatus(window.RUV_PRODUCTION);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init); else init();
})();