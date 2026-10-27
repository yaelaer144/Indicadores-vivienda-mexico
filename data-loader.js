(function(){
  function parseCsvText(text){
    const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/); if(lines.length<2)return [];
    const delim=(lines[0].split('|').length>lines[0].split(',').length)?'|':',';
    const parseLine=s=>{const out=[];let cur='',q=false;for(let i=0;i<s.length;i++){const c=s[i];if(c==='"'){if(q&&s[i+1]==='"'){cur+='"';i++;}else q=!q;}else if(c===delim&&!q){out.push(cur);cur='';}else cur+=c;}out.push(cur);return out;};
    const h=parseLine(lines[0]).map(x=>x.trim());
    return lines.slice(1).filter(Boolean).map(line=>{const v=parseLine(line),o={};h.forEach((k,i)=>o[k]=(v[i]??'').trim());return o;});
  }
  async function csv(path){
    try{
      const r=await fetch(path,{cache:'no-store'});
      if(r.ok) return parseCsvText(await r.text());
    }catch(e){}
    // Cuando se abre directamente con file:/// algunos navegadores bloquean fetch().
    // Para las tres series críticas de Actividad económica usamos los datos embebidos.
    return window.LOCAL_CSV_DATA?.[path] || [];
  }
  const num=v=>{if(v==null||String(v).trim()==='')return null;const n=Number(String(v).replace(/,/g,''));return Number.isFinite(n)?n:null};
  function pick(o,names){for(const n of names){if(Object.prototype.hasOwnProperty.call(o,n)&&o[n]!==''&&o[n]!=null)return o[n]}return null}
  function normalizeQuarter(v){
    const s=String(v??'').trim();
    let m=s.match(/(20\d{2})[-_/ ]?(?:T|Q)?([1-4])$/i);
    if(m)return `${m[1]}-T${m[2]}`;
    m=s.match(/^(20\d{2})([1-4])$/);
    return m?`${m[1]}-T${m[2]}`:null;
  }
  function sortQuarter(a,b){return String(a).localeCompare(String(b));}
  function parseQuarterlyRows(rows){
    return rows.map(r=>({period:normalizeQuarter(pick(r,['periodo','period'])),total:num(pick(r,['total'])),occupied_total:num(pick(r,['ocupada_total','occupied_total','poblacion_ocupada_total'])),formal:num(pick(r,['formal'])),informal:num(pick(r,['informal']))})).filter(x=>/^20\d{2}-T[1-4]$/.test(x.period||'')).sort((a,b)=>sortQuarter(a.period,b.period));
  }


  async function loadPeriodic(){
    const D=window.DASHBOARD_DATA;
    const [enoeLocal,enoeAnnual,imss,inpp,shf,iccAnnual,iccMonthly,iccComponentsMonthly,pibConstruction,vabQuarterly,vabAnnualReal,igaeMonthly,ifbMonthly,imaiMonthly,enecEdifMM,inppConstructionLatest,vabComponents,priceHistory,iccQuarterly,inppQuarterly,inppConstructionMonthly,iccYoyMonthly,imssTotalMonthly,enecActivityHistorical,vabSubsectors,iccBase2025,inppBase2025,pvbRows,csvmRows,enecLaborRows,sbcRows,ruvFlowRows,tenureHistoryRows,tenure2024Rows,tenureAreaRows,conditionsHistoryRows,conditionsSummaryRows,bridgeRows,enecWorkerTypeRows,enecHousingRows,shfStateRows,sniivKpiRows,shfLevelsRows]=await Promise.all([
      csv('enoe_construccion_trimestral.csv'),
      csv('enoe_construccion_historico_anual.csv'),
      csv('imss_construccion_mensual.csv'),
      csv('inpp_componentes_construccion_mensual.csv'),
      csv('shf_indice_trimestral.csv'),
      csv('icc_ciudad_historico_anual.csv'),
      csv('icc_residencial_mensual.csv'),
      csv('icc_subindices_mensual.csv'),
      csv('pib_construccion_trimestral.csv'),
      csv('vab_edificacion_trimestral.csv'),
      csv('vab_construccion_anual_real.csv'),
      csv('igae_construccion_mensual.csv'),
      csv('ifb_residencial_mensual.csv'),
      csv('imai_construccion_mensual.csv'),
      csv('enec_edificacion_variacion_mensual.csv'),
      csv('inpp_construccion_ultimo.csv'),
      csv('vab_edificacion_componentes_anual.csv'),
      csv('precios_historicos_2019_2024.csv'),
      csv('icc_trimestral.csv'),
      csv('inpp_construccion_trimestral.csv'),
      csv('inpp_construccion_mensual.csv'),
      csv('icc_residencial_variacion_anual_mensual.csv'),
      csv('imss_total_mensual.csv'),
      csv('enec_actividad_historica.csv'),
      csv('vab_construccion_subsectores_trimestral.csv'),
      csv('icc_incevis_base2025_mensual.csv'),
      csv('inpp_construccion_edificacion_base2025_mensual.csv'),
      csv('pvb_avance.csv'),
      csv('csvm_pib_vivienda_anual.csv'),
      csv('enec_indices_laborales_mensual.csv'),
      csv('imss_sbc_construccion_mensual.csv'),
      csv('ruv_flujo_vivienda_anual.csv'),
      csv('tenencia_historica.csv'),
      csv('tenencia_2024.csv'),
      csv('tenencia_rural_urbano_2024.csv'),
      csv('condiciones_historicas.csv'),
      csv('condiciones_resumen_2024.csv'),
      csv('bridge_financing_anual.csv'),
      csv('enec_personal_tipo_variacion_mensual.csv'),
      csv('enec_vivienda_yoy.csv'),
      csv('shf_precios_entidad.csv'),
      csv('sniiv_kpis.csv'),
      csv('shf_indice_nivel_trimestral.csv')
    ]);


    // PRIMERA FASE DE EXTERNALIZACION: estas gráficas ya no dependen de cifras
    // incrustadas en bootstrap-data.js. El CSV es la fuente operativa y puede ser
    // reemplazado posteriormente por un script/API sin modificar charts.js.
    if(csvmRows.length){
      const rows=csvmRows.map(r=>({year:num(pick(r,['anio','year'])),pib:num(pick(r,['pib_total_mdp'])),share:num(pick(r,['participacion_pib_pct'])),edif:num(pick(r,['edificacion_mdp'])),acq:num(pick(r,['adquisicion_mdp'])),use:num(pick(r,['uso_mdp'])),reg:num(pick(r,['regulacion_fomento_mdp']))})).filter(x=>Number.isFinite(x.year)).sort((a,b)=>a.year-b.year);
      D.activity.years=rows.map(x=>x.year); D.activity.pib_total=rows.map(x=>x.pib); D.activity.participation=rows.map(x=>x.share);
      D.activity.components={'Edificación':rows.map(x=>x.edif),'Adquisición':rows.map(x=>x.acq),'Uso':rows.map(x=>x.use),'Regulación y fomento':rows.map(x=>x.reg)};
    }
    if(enecLaborRows.length){
      D.labor.monthly_indices=enecLaborRows.map(r=>({period:pick(r,['periodo','period']),empl_const:num(pick(r,['personal_construccion'])),empl_edif:num(pick(r,['personal_edificacion'])),hours_const:num(pick(r,['horas_construccion'])),hours_edif:num(pick(r,['horas_edificacion'])),rem_const:num(pick(r,['remuneraciones_construccion'])),rem_edif:num(pick(r,['remuneraciones_edificacion']))})).filter(x=>x.period&&x.empl_const!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }
    
    // ENEC: indices oficiales por tipo de trabajador.
    // INEGI, serie 2018. Variaciones anuales.
    if(enecLaborRows.length){
      const rows = enecLaborRows.map(r => ({
        period: pick(r, ['periodo', 'period']),
        total: num(pick(r, ['personal_construccion'])),
        workers: num(pick(r, ['personal_obreros'])),
        admin: num(pick(r, ['personal_administrativos']))
      }))
      .filter(r =>
        r.period &&
        r.total != null &&
        r.workers != null &&
        r.admin != null
      )
      .sort((a,b) => a.period.localeCompare(b.period));

      const byPeriod = new Map(
        rows.map(r => [r.period, r])
      );

      const yoy = (current, previous) =>
        current != null &&
        previous != null &&
        previous !== 0
          ? (current / previous - 1) * 100
          : null;

      D.labor.enec_worker_type_index = rows.map(r => {
        const previousPeriod =
          `${Number(r.period.slice(0,4)) - 1}-${r.period.slice(5,7)}`;

        const previous = byPeriod.get(previousPeriod);

        return {
          ...r,
          total_yoy: yoy(r.total, previous?.total),
          workers_yoy: yoy(r.workers, previous?.workers),
          admin_yoy: yoy(r.admin, previous?.admin)
        };
      });

      D.labor.enec_worker_type_mom = [];
    }

    if(enecHousingRows.length){
      D.production.enec_housing_yoy=enecHousingRows.map(r=>({period:pick(r,['periodo','period']),edification:num(pick(r,['edificacion_yoy_pct','edificacion_yoy'])),housing:num(pick(r,['vivienda_yoy_pct','vivienda_yoy']))})).filter(x=>x.period&&(x.edification!=null||x.housing!=null)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }
    if(sbcRows.length){ D.labor.salary_monthly=sbcRows.map(r=>({period:pick(r,['periodo','period']),daily:num(pick(r,['sbc_diario_pesos','daily']))})).filter(x=>x.period&&x.daily!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period))); }
    if(ruvFlowRows.length){
      const rows=ruvFlowRows.map(r=>({year:num(pick(r,['anio','year'])),registered:num(pick(r,['registradas_miles'])),started:num(pick(r,['inicio_obra_miles'])),finished:num(pick(r,['terminadas_miles']))})).filter(x=>Number.isFinite(x.year)).sort((a,b)=>a.year-b.year);
      D.production.years=rows.map(x=>x.year); D.production.registered=rows.map(x=>x.registered); D.production.started=rows.map(x=>x.started); D.production.finished=rows.map(x=>x.finished);
    }
    if(tenureHistoryRows.length){
      const rows=tenureHistoryRows.map(r=>({year:num(pick(r,['anio'])),own:num(pick(r,['propia_pagada_pct'])),paying:num(pick(r,['propia_pagandose_pct'])),rented:num(pick(r,['rentada_pct'])),other:num(pick(r,['otros_pct']))})).filter(x=>Number.isFinite(x.year)).sort((a,b)=>a.year-b.year);
      D.conditions.tenure_history={years:rows.map(x=>x.year),own_paid_pct:rows.map(x=>x.own),paying_pct:rows.map(x=>x.paying),rented_pct:rows.map(x=>x.rented),other_pct:rows.map(x=>x.other),note:'Otros = prestada + intestada/litigio + otra situación.'};
    }
    if(tenure2024Rows.length){
      const m={}; tenure2024Rows.forEach(r=>m[String(pick(r,['categoria'])||'').toLowerCase()]=num(pick(r,['porcentaje'])));
      const own=m['propia totalmente pagada'],pay=m['propia pagándose'],rent=m['rentada'],other=m['otros'];
      if(own!=null){ const yr=num(pick(tenure2024Rows[0]||{},['anio','year']))||2024; D.conditions.tenure={year:yr,own_strict:own,paying:pay,own_plus_paying:(own||0)+(pay||0),rented:rent,other:other}; }
    }
    if(tenureAreaRows.length){
      const rows=tenureAreaRows.map(r=>({area:pick(r,['ambito']),own:num(pick(r,['propia'])),paying:num(pick(r,['pagandose'])),rented:num(pick(r,['rentada'])),other:num(pick(r,['otros']))}));
      D.conditions.tenure_rural_urban={labels:rows.map(x=>x.area),four_categories:{own_paid:rows.map(x=>x.own),paying:rows.map(x=>x.paying),rented:rows.map(x=>x.rented),other:rows.map(x=>x.other)},note:'Datos externos en tenencia_rural_urbano_2024.csv'};
    }
    if(conditionsHistoryRows.length){
      const rows=conditionsHistoryRows.map(r=>({year:num(pick(r,['anio'])),quality:num(pick(r,['carencia_calidad_espacios_pct'])),services:num(pick(r,['carencia_servicios_basicos_pct']))})).filter(x=>Number.isFinite(x.year)).sort((a,b)=>a.year-b.year);
      D.conditions.history_years=rows.map(x=>x.year); D.conditions.deprivation_history={quality_space_pct:rows.map(x=>x.quality),basic_services_pct:rows.map(x=>x.services)};
      const z=rows.at(-1); if(z) D.conditions.deprivation={quality_space_2024:z.quality,basic_services_2024:z.services};
    }

    if(bridgeRows.length){
      const rows=bridgeRows.map(r=>({year:num(pick(r,['anio','year'])),rate:num(pick(r,['tasa_credito_puente_pct','rate','tasa']))})).filter(x=>Number.isFinite(x.year)&&x.rate!=null).sort((a,b)=>a.year-b.year);
      D.prices.bridge_years=rows.map(x=>x.year);
      D.prices.bridge_rate=rows.map(x=>x.rate);
    }
    if(conditionsSummaryRows.length){
      const m={}; conditionsSummaryRows.forEach(r=>m[pick(r,['indicador'])]=num(pick(r,['valor'])));
      D.conditions.summary_year=num(pick(conditionsSummaryRows[0]||{},['anio','year']))||D.conditions.tenure?.year||2024;
      D.conditions.materials={walls_inadequate:m.materiales_muros_inadecuados_pct,roofs_inadequate:m.materiales_techos_inadecuados_pct,floor_inadequate:m.materiales_pisos_inadecuados_pct};
      D.conditions.qualitative_deficit={homes:m.deficit_cualitativo_viviendas,pct:m.deficit_cualitativo_pct,components:{materials_pct:m.deficit_materiales_pct,spaces_pct:m.deficit_espacios_pct,services_pct:m.deficit_servicios_pct},components_homes:{materials:m.deficit_materiales_viviendas,spaces:m.deficit_espacios_viviendas,services:m.deficit_servicios_viviendas}};
    }


    // PVB: archivo estable y acumulativo. Puede contener varios cortes históricos.
    // El dashboard selecciona automáticamente el periodo más reciente y evita cifras fijas en JavaScript.
    if(pvbRows.length){
      const normalized=pvbRows.map(r=>({
        stage:String(pick(r,['etapa','stage'])||'').trim(),
        housing:num(pick(r,['viviendas','housing','value'])),
        period:String(pick(r,['periodo','period','fecha_corte'])||'').trim(),
        relation:pick(r,['relacion','nota','note']),
        source:pick(r,['fuente','source']),
        url:pick(r,['url','enlace','source_url'])
      })).filter(x=>x.stage&&x.period&&x.housing!=null);
      const periods=[...new Set(normalized.map(x=>x.period))].sort();
      const latestPeriod=periods.at(-1)||null;
      const latestRows=normalized.filter(x=>x.period===latestPeriod);
      D.production.pvb={
        period:latestPeriod,
        rows:latestRows,
        history:normalized.sort((a,b)=>String(a.period).localeCompare(String(b.period))),
        source:latestRows.find(x=>x.source)?.source||null,
        url:latestRows.find(x=>x.url)?.url||null
      };
    } else {
      D.production.pvb={period:null,rows:[],history:[],source:null,url:null};
    }


    // Fuentes oficiales reemplazadas 28/09/2026.
    if(vabSubsectors.length){
      D.activity.vab_subsectors_quarterly=vabSubsectors.map(r=>({
        period:normalizeQuarter(pick(r,['periodo','period'])),
        construction:num(pick(r,['construccion_mdp_2018'])),
        edification:num(pick(r,['edificacion_mdp_2018'])),
        civil:num(pick(r,['obra_civil_mdp_2018'])),
        specialized:num(pick(r,['trabajos_especializados_mdp_2018'])),
        construction_yoy:num(pick(r,['construccion_yoy'])),
        edification_yoy:num(pick(r,['edificacion_yoy'])),
        civil_yoy:num(pick(r,['obra_civil_yoy'])),
        specialized_yoy:num(pick(r,['trabajos_especializados_yoy']))
      })).filter(x=>x.period&&x.construction!=null).sort((a,b)=>sortQuarter(a.period,b.period));
    }
    if(iccBase2025.length){
      D.prices.icc_monthly=iccBase2025.map(r=>({
        period:pick(r,['periodo']), general:num(pick(r,['general'])),
        materials:num(pick(r,['materiales'])), machinery:num(pick(r,['maquinaria'])), labor:num(pick(r,['mano_obra'])),
        yoy:num(pick(r,['general_yoy'])), materials_yoy:num(pick(r,['materiales_yoy'])),
        machinery_yoy:num(pick(r,['maquinaria_yoy'])), labor_yoy:num(pick(r,['mano_obra_yoy']))
      })).filter(x=>x.period&&x.general!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      D.prices.icc_yoy_monthly=D.prices.icc_monthly.filter(x=>x.yoy!=null).map(x=>({period:x.period,yoy:x.yoy}));
      D.prices.icc_components_monthly=D.prices.icc_monthly.map(x=>({period:x.period,materials:x.materials,machinery:x.machinery,labor:x.labor,materials_yoy:x.materials_yoy,machinery_yoy:x.machinery_yoy,labor_yoy:x.labor_yoy}));
    }
    if(inppBase2025.length){
      D.prices.inpp_construction_monthly=inppBase2025.map(r=>({
        period:pick(r,['periodo']), level:num(pick(r,['construccion'])), yoy:num(pick(r,['construccion_yoy'])),
        edification:num(pick(r,['edificacion'])), residential:num(pick(r,['edificacion_residencial'])),
        nonresidential:num(pick(r,['edificacion_no_residencial']))
      })).filter(x=>x.period&&x.level!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      D.prices.inpp_construction_latest=D.prices.inpp_construction_monthly.slice(-1);
    }


    if(pibConstruction.length){
      D.activity.pib_construction_quarterly=pibConstruction.map(r=>({period:normalizeQuarter(pick(r,['periodo','period'])),value_mdp:num(pick(r,['valor_mdp','value_mdp','nivel_mdp'])),yoy:num(pick(r,['variacion_anual_real','yoy','variacion_anual'])),share:num(pick(r,['participacion_pib','share']))})).filter(x=>x.period&&x.value_mdp!=null).sort((a,b)=>sortQuarter(a.period,b.period));
    }
    if(vabQuarterly.length){
      D.activity.vab_quarterly=vabQuarterly.map(r=>({period:normalizeQuarter(pick(r,['periodo','period'])),value_mdp:num(pick(r,['valor_mdp_2018_anualizado','valor_mdp','value_mdp','nivel_mdp'])),yoy:num(pick(r,['variacion_anual_real','yoy','variacion_anual'])),note:pick(r,['nota','note'])})).filter(x=>/^20\d{2}-T[1-4]$/.test(x.period||'')).sort((a,b)=>sortQuarter(a.period,b.period));
    } else if(D.activity.pib_construction_quarterly?.length){
      D.activity.vab_quarterly=D.activity.pib_construction_quarterly.map(x=>({period:x.period,value_mdp:x.value_mdp,yoy:x.yoy}));
    }
    if(vabAnnualReal.length){
      D.activity.vab_annual_real=vabAnnualReal.map(r=>({
        year:num(pick(r,['anio','year'])),
        value_mdp_2018:num(pick(r,['valor_mdp_2018','value_mdp_2018'])),
        index_2018:num(pick(r,['indice_2018','index_2018'])),
        yoy:num(pick(r,['variacion_anual_real','yoy'])),
        source:pick(r,['fuente','source']),
        note:pick(r,['nota','note'])
      })).filter(x=>Number.isFinite(x.year)&&x.value_mdp_2018!=null).sort((a,b)=>a.year-b.year);
    } else {
      D.activity.vab_annual_real=[];
    }
    if(vabComponents.length){
      D.activity.vab_components_annual=vabComponents.map(r=>({
        year:num(pick(r,['anio','year'])),
        residential:num(pick(r,['vab_residencial_mdp','residential'])),
        nonresidential:num(pick(r,['vab_no_residencial_mdp','nonresidential'])),
        source:pick(r,['fuente','source'])
      })).filter(x=>Number.isFinite(x.year)&&(x.residential!=null||x.nonresidential!=null)).sort((a,b)=>a.year-b.year);
    } else {
      D.activity.vab_components_annual=[];
    }
    if(igaeMonthly.length){
      D.activity.igae_monthly=igaeMonthly.map(r=>({period:pick(r,['periodo','period']),index:num(pick(r,['indice','index'])),mom:num(pick(r,['variacion_mensual','mom'])),yoy:num(pick(r,['variacion_anual','yoy']))})).filter(x=>x.period&&(x.index!=null||x.yoy!=null)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }
    if(ifbMonthly.length){
      D.activity.ifb_monthly=ifbMonthly.map(r=>({period:pick(r,['periodo','period']),index:num(pick(r,['indice','index'])),mom:num(pick(r,['variacion_mensual','mom'])),yoy:num(pick(r,['variacion_anual','yoy']))})).filter(x=>x.period&&(x.index!=null||x.yoy!=null)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }
    if(imaiMonthly.length){
      D.activity.imai_monthly=imaiMonthly.map(r=>({period:pick(r,['periodo','period']),index:num(pick(r,['indice','index'])),mom:num(pick(r,['variacion_mensual','mom'])),yoy:num(pick(r,['variacion_anual','yoy']))})).filter(x=>x.period&&(x.index!=null||x.yoy!=null)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }

    // Diagnóstico: deja constancia de que las tres series llegaron al navegador.
    console.info('[Dashboard] Actividad cargada:', {
      vab: D.activity.vab_quarterly?.length || 0,
      ifb: D.activity.ifb_monthly?.length || 0,
      imai: D.activity.imai_monthly?.length || 0
    });

    const enoeLocalNorm=parseQuarterlyRows(enoeLocal);
    D.labor.enoe_quarterly=enoeLocalNorm;
    D.labor.enoe_quarterly_error=enoeLocalNorm.length
      ? 'Serie trimestral local observada; no se completa con estimaciones ni con una fuente de definición distinta.'
      : 'No hay observaciones trimestrales ENOE válidas cargadas.';
    if(enoeAnnual.length){
      D.labor.enoe_annual=enoeAnnual.map(r=>({
        period:String(pick(r,['periodo','period'])),
        total:num(pick(r,['total'])),
        formal:num(pick(r,['formal'])),
        informal:num(pick(r,['informal']))
      })).filter(x=>/^20\d{2}$/.test(x.period)&&x.total!=null)
        .sort((a,b)=>a.period.localeCompare(b.period));
    }

    if(imss.length){
      const imssRows=imss.map(r=>({period:pick(r,['periodo','period']),construction:num(pick(r,['construccion','construction'])),edification:num(pick(r,['edificacion','edification']))})).filter(x=>x.period&&x.construction!=null);
      D.labor.imss_monthly=imssRows;
      D.labor.imss_edification_note='Serie mensual de empleos/puestos registrados ante el IMSS en el sector construcción.';
    }

    if(inpp.length){
      D.prices.inpp_components_monthly=inpp.map(r=>({
        period:pick(r,['periodo','period']),
        materials:num(pick(r,['materiales','materials'])),
        labor:num(pick(r,['mano_obra','remuneraciones','labor'])),
        machinery:num(pick(r,['maquinaria','alquiler_maquinaria','machinery']))
      })).filter(x=>x.period&&(x.materials!=null||x.labor!=null||x.machinery!=null));
    }

    if(shf.length){
      D.prices.shf_quarterly=shf.map(r=>({period:pick(r,['periodo','period']),yoy:num(pick(r,['variacion_anual','yoy','variacion'])) ,index:num(pick(r,['indice','index']))})).filter(x=>x.period&&(x.yoy!=null||x.index!=null));
      const officialLevels=new Map(shfLevelsRows.map(r=>[pick(r,['periodo','period']),num(pick(r,['indice','index']))]).filter(([period,v])=>period&&Number.isFinite(v)));
      D.prices.shf_quarterly.forEach(r=>{if(officialLevels.has(r.period))r.index=officialLevels.get(r.period);});
    }

    if(shfStateRows.length){
      const keyMap={'Aguascalientes':'mx-ag','Baja California':'mx-bc','Baja California Sur':'mx-bs','Campeche':'mx-cm','Chiapas':'mx-cs','Chihuahua':'mx-ch','Ciudad de México':'mx-df','Coahuila':'mx-co','Coahuila de Zaragoza':'mx-co','Colima':'mx-cl','Durango':'mx-dg','Guanajuato':'mx-gj','Guerrero':'mx-gr','Hidalgo':'mx-hg','Jalisco':'mx-ja','Estado de México':'mx-mx','México':'mx-mx','Michoacán':'mx-mi','Michoacán de Ocampo':'mx-mi','Morelos':'mx-mo','Nayarit':'mx-na','Nuevo León':'mx-nl','Oaxaca':'mx-oa','Puebla':'mx-pu','Querétaro':'mx-qt','Quintana Roo':'mx-qr','San Luis Potosí':'mx-sl','Sinaloa':'mx-si','Sonora':'mx-so','Tabasco':'mx-tb','Tamaulipas':'mx-tm','Tlaxcala':'mx-tl','Veracruz':'mx-ve','Veracruz de Ignacio de la Llave':'mx-ve','Yucatán':'mx-yu','Zacatecas':'mx-za'};
      const rows=shfStateRows.map(r=>({state:pick(r,['entidad','estado','state']),value:num(pick(r,['precio_promedio_pesos','promedio','value'])),p25:num(pick(r,['p25_pesos','p25'])),p50:num(pick(r,['p50_pesos','mediana','p50'])),p75:num(pick(r,['p75_pesos','p75'])),period:pick(r,['periodo','period'])})).filter(x=>x.state&&x.value!=null);
      const national=rows.find(x=>String(x.state).toLowerCase()==='nacional');
      D.prices.shf_state_avg_price=rows.filter(x=>String(x.state).toLowerCase()!=='nacional').map(x=>({key:keyMap[x.state]||'',state:x.state,value:x.value,p25:x.p25,p50:x.p50,p75:x.p75,period:x.period}));
      D.prices.shf_state_price_period=(national||rows[0])?.period||D.prices.shf_state_price_period||null;
      if(national){
        D.prices.shf_national_distribution={key:'mx-national',state:'Nacional',value:national.value,p25:national.p25,p50:national.p50,p75:national.p75,period:national.period};
        D.prices.current={...(D.prices.current||{}),avg_price:national.value,median_price:national.p50,p25:national.p25,p75:national.p75,period:national.period};
      }
    }
    if(sniivKpiRows.length){
      D.production.current=D.production.current||{}; D.production.current.periods=D.production.current.periods||{};
      for(const r of sniivKpiRows){
        const metric=String(pick(r,['indicador','metric'])||''); const value=num(pick(r,['valor','value'])); const period=pick(r,['periodo','period']);
        if(metric==='ruv_inventory'){D.production.current.ruv_inventory_jun26=value;D.production.current.periods.ruv_inventory=period;}
        if(metric==='financing_total'){D.production.current.financing_total_jun26=value;D.production.current.periods.financing=period;}
        if(metric==='pvb_conavi_housing'){D.production.current.pvb_housing_jun15_26=value;D.production.current.periods.pvb=period;}
        if(metric==='pvb_conavi_hectares'){D.production.current.pvb_hectares_jun15_26=value;D.production.current.periods.pvb=period;}
        if(metric==='pvb_conavi_predios'){D.production.current.pvb_predios_jun15_26=value;D.production.current.periods.pvb=period;}
      }
    }
    if((D.prices.shf_quarterly||[]).length){ const q=D.prices.shf_quarterly.at(-1); D.prices.current={...(D.prices.current||{}),yoy:q.yoy,yoy_period:q.period}; }

    if(iccAnnual.length){
      D.prices.icc_city_annual=iccAnnual.map(r=>({
        year:num(pick(r,['anio','year'])),
        city:pick(r,['ciudad','city']),
        general:num(pick(r,['indice_general','general','icc'])),
        materials:num(pick(r,['materiales','materials'])),
        machinery:num(pick(r,['maquinaria','alquiler_maquinaria','machinery'])),
        labor:num(pick(r,['mano_obra','remuneraciones','labor'])),
        period_note:pick(r,['nota_periodo','period_note']),
        source:pick(r,['fuente','source'])
      })).filter(x=>Number.isFinite(x.year)&&x.city&&x.general!=null).sort((a,b)=>a.year-b.year||String(a.city).localeCompare(String(b.city)));
    }

    if(!iccBase2025.length && iccMonthly.length){
      D.prices.icc_monthly=iccMonthly.map(r=>({period:pick(r,['periodo','period']),general:num(pick(r,['indice_general','general','icc']))})).filter(x=>x.period&&x.general!=null);
      D.prices.icc_monthly_note='Serie mensual cargada desde icc_residencial_mensual.csv';
    } else if((D.prices.icc_city_annual||[]).length){
      D.prices.icc_monthly=[];
      D.prices.icc_monthly_note='No se construye una serie mensual a partir de datos anuales. Se requiere la serie mensual oficial del ICC.';
    }

    // Series trimestrales para el tablero: se usan cortes oficiales de marzo, junio,
    // septiembre y diciembre. No se interpolan observaciones faltantes.
    if(iccQuarterly.length){
      D.prices.icc_quarterly=iccQuarterly.map(r=>({
        period:pick(r,['periodo','period']),
        cutoff:pick(r,['mes_corte','cutoff']),
        general:num(pick(r,['indice_general','general','icc'])),
        yoy:num(pick(r,['variacion_anual','yoy'])),
        source:pick(r,['fuente','source'])
      })).filter(x=>x.period&&x.general!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    } else {
      D.prices.icc_quarterly=[];
    }

    if(inppQuarterly.length){
      D.prices.inpp_construction_quarterly=inppQuarterly.map(r=>({
        period:pick(r,['periodo','period']),
        cutoff:pick(r,['mes_corte','cutoff']),
        yoy:num(pick(r,['variacion_anual','yoy'])),
        source:pick(r,['fuente','source'])
      })).filter(x=>x.period&&x.yoy!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    } else {
      D.prices.inpp_construction_quarterly=[];
    }

    // Subíndices nacionales del ICC: únicamente observaciones mensuales oficiales.
    if(!iccBase2025.length && iccComponentsMonthly.length){
      D.prices.icc_components_monthly=iccComponentsMonthly.map(r=>({
        period:pick(r,['periodo','period']),
        materials:num(pick(r,['materiales','materials'])),
        machinery:num(pick(r,['maquinaria','machinery'])),
        labor:num(pick(r,['labor','remuneraciones'])),
        source:pick(r,['fuente','source'])
      })).filter(x=>x.period && (x.materials!=null || x.machinery!=null || x.labor!=null))
        .sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      D.prices.icc_components_latest=D.prices.icc_components_monthly.slice(-1);
      D.prices.icc_components_latest_note='Serie mensual oficial incorporada al proyecto. No se mensualizan datos anuales ni se insertan valores hardcodeados.';
      D.prices.icc_components_yoy_annual=[];
    } else if(!iccBase2025.length) {
      D.prices.icc_components_monthly=[];
      D.prices.icc_components_latest=[];
      D.prices.icc_components_yoy_annual=[];
      D.prices.icc_components_latest_note='N/D: no se encontró una serie mensual oficial local.';
    }

    if(enecEdifMM.length){
      D.activity.enec_edification_mm=enecEdifMM.map(r=>({
        period:pick(r,['periodo','period']),
        value:num(pick(r,['variacion_mensual_real','value']))
      })).filter(x=>x.period&&x.value!=null).sort((a,b)=>a.period.localeCompare(b.period));
    }
    if(!inppBase2025.length && inppConstructionLatest.length){
      D.prices.inpp_construction_latest=inppConstructionLatest.map(r=>({
        period:pick(r,['periodo','period']),
        monthly:num(pick(r,['variacion_mensual'])),
        cumulative:num(pick(r,['variacion_acumulada_dic'])),
        yoy:num(pick(r,['variacion_anual']))
      })).filter(x=>x.period);
    }

    // INPP construcción: observaciones mensuales oficiales. La tasa anual se conserva
    // mes a mes; no se agregan ni se sustituyen por cierres anuales.
    if(!iccBase2025.length && iccYoyMonthly.length){
      D.prices.icc_yoy_monthly=iccYoyMonthly.map(r=>({period:pick(r,['periodo','period']),yoy:num(pick(r,['variacion_anual','yoy']))})).filter(x=>x.period&&x.yoy!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      D.prices.icc_yoy_monthly_note='Variación anual mensual del índice nacional de construcción residencial por ciudad; observaciones verificadas, sin mezclarla con Edificación residencial por actividad económica y sin interpolación.';
    }
    if(imssTotalMonthly.length){
      D.labor.imss_total_monthly=imssTotalMonthly.map(r=>({period:pick(r,['periodo','period']),total:num(pick(r,['puestos_miles','total']))})).filter(x=>x.period&&x.total!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }
    if(enecActivityHistorical.length){
      D.activity.enec_production=enecActivityHistorical.map(r=>({period:pick(r,['periodo','period']),edification:num(pick(r,['edificacion_indice'])),public:num(pick(r,['publico_indice'])),private:num(pick(r,['privado_indice']))})).filter(x=>x.period&&x.edification!=null).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
    }

    if(!inppBase2025.length && inppConstructionMonthly.length){
      D.prices.inpp_construction_monthly=inppConstructionMonthly.map(r=>({
        period:pick(r,['periodo','period']),
        monthly:num(pick(r,['variacion_mensual','monthly'])),
        yoy:num(pick(r,['variacion_anual','yoy'])),
        source:pick(r,['fuente','source'])
      })).filter(x=>x.period&&(x.monthly!=null||x.yoy!=null))
        .sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      D.prices.inpp_construction_latest=D.prices.inpp_construction_monthly.slice(-1);
    } else if(!inppBase2025.length) {
      D.prices.inpp_construction_monthly=[];
    }

    if(priceHistory.length){
      D.prices.history_2019_2024=priceHistory.map(r=>({
        year:num(pick(r,['anio','year'])),
        icc_yoy:num(pick(r,['icc_residencial_var_anual_dic','icc_yoy'])),
        inpp_construction_yoy:num(pick(r,['inpp_construccion_var_anual_dic','inpp_construction_yoy'])),
        source_icc:pick(r,['fuente_icc','source_icc']),
        source_inpp:pick(r,['fuente_inpp','source_inpp'])
      })).filter(x=>Number.isFinite(x.year)&&(x.icc_yoy!=null||x.inpp_construction_yoy!=null)).sort((a,b)=>a.year-b.year);
    }

    D.activity._load_status={
      vab_quarterly:(D.activity.vab_quarterly||[]).length,
      ifb_monthly:(D.activity.ifb_monthly||[]).length,
      imai_monthly:(D.activity.imai_monthly||[]).length,
      igae_monthly:(D.activity.igae_monthly||[]).length,
      pib_construction_quarterly:(D.activity.pib_construction_quarterly||[]).length
    };
    return D;
  }
  window.DashboardDataLoader={get:()=>window.DASHBOARD_DATA,loadPeriodic};
})();
