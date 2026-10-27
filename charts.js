(function(){
  const brand='#c8102e', blue='#315d78', grey='#8b949e', green='#2f7654', gold='#aa7a2b';
  function formatValue(v,d=1){return Number.isFinite(v)?new Intl.NumberFormat('es-MX',{minimumFractionDigits:d,maximumFractionDigits:d}).format(v):'N/D';}
  function crossesZero(datasets){const vals=(datasets||[]).flatMap(d=>(d.data||[])).filter(Number.isFinite);return vals.some(v=>v<0)&&vals.some(v=>v>0);}
  function line(id,labels,datasets,opts={}){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    const singlePoint=(labels||[]).length<=1, zeroBold=crossesZero(datasets);
    new Chart(el,{type:singlePoint?'bar':'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},spanGaps:true,plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>`${ctx.dataset.label}: ${formatValue(ctx.parsed.y,opts.decimals??1)}${opts.suffix||''}`}}},scales:{x:{grid:{display:false},ticks:{font:{size:9},maxTicksLimit:12},title:{display:!!opts.xTitle,text:opts.xTitle||'',font:{size:10}}},y:{grid:{color:(c)=>zeroBold&&c.tick?.value===0?'#69727c':'#eef1f3',lineWidth:(c)=>zeroBold&&c.tick?.value===0?2.5:1},ticks:{font:{size:9}},beginAtZero:!!opts.beginAtZero,min:opts.yMin,max:opts.yMax,title:{display:!!opts.yTitle,text:opts.yTitle||'',font:{size:10}}}}}});
  }
  function bar(id,labels,datasets,opts={}){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    new Chart(el,{type:'bar',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>`${ctx.dataset.label}: ${formatValue(ctx.parsed.y,opts.decimals??1)}${opts.suffix||''}`}}},scales:{x:{stacked:!!opts.stacked,grid:{display:false},ticks:{font:{size:9},maxTicksLimit:12}},y:{stacked:!!opts.stacked,grid:{color:'#eef1f3'},ticks:{font:{size:9}},beginAtZero:opts.beginAtZero!==false,title:{display:!!opts.yTitle,text:opts.yTitle||'',font:{size:10}}}}}});
  }
  function pie(id,labels,data,opts={}){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    new Chart(el,{type:'pie',data:{labels,datasets:[{data,backgroundColor:opts.colors||['#c8102e','#aa7a2b','#315d78','#8b949e']}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},
      tooltip:{callbacks:{label:(ctx)=>`${ctx.label}: ${ctx.parsed.toFixed(1)}%`}}}}});
  }
  function stackedPercentBar(id,labels,datasets,opts={}){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    const horizontal=!!opts.horizontal;
    new Chart(el,{type:'bar',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,indexAxis:horizontal?'y':'x',interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>{const v=horizontal?ctx.parsed.x:ctx.parsed.y;return `${ctx.dataset.label}: ${Number.isFinite(v)?v.toFixed(opts.decimals??1):'N/D'}%`;}}}},scales:horizontal?{x:{stacked:true,min:0,max:100,grid:{color:'#eef1f3'},ticks:{font:{size:9},callback:v=>`${v}%`},title:{display:true,text:opts.xTitle||'Porcentaje de viviendas (%)',font:{size:10}}},y:{stacked:true,grid:{display:false},ticks:{font:{size:9}}}}:{x:{stacked:true,grid:{display:false},ticks:{font:{size:9},maxTicksLimit:12}},y:{stacked:true,min:0,max:100,grid:{color:'#eef1f3'},ticks:{font:{size:9},callback:v=>`${v}%`},title:{display:true,text:opts.yTitle||'Porcentaje de viviendas (%)',font:{size:10}}}}}});
  }
  function dualAxisLine(id,labels,datasets,opts={}){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    new Chart(el,{type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>`${ctx.dataset.label}: ${Number.isFinite(ctx.parsed.y)?ctx.parsed.y.toFixed(ctx.dataset.decimals??1):'N/D'}${ctx.dataset.unit||''}`}}},scales:{x:{grid:{display:false},ticks:{font:{size:9},maxTicksLimit:12}},y:{position:'left',beginAtZero:false,min:opts.leftMin,max:opts.leftMax,grid:{color:'#eef1f3'},ticks:{font:{size:9}},title:{display:true,text:opts.leftTitle||'',font:{size:10}}},y1:{position:'right',beginAtZero:false,min:opts.rightMin,max:opts.rightMax,grid:{drawOnChartArea:false},ticks:{font:{size:9}},title:{display:true,text:opts.rightTitle||'',font:{size:10}}}}}});
  }
  function doughnut(id,labels,data,unit='Porcentaje de viviendas (%)'){
    const el=document.getElementById(id); if(!el||!window.Chart)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    new Chart(el,{type:'doughnut',data:{labels,datasets:[{data,backgroundColor:[brand,blue,grey],borderColor:'#fff',borderWidth:3}]},options:{responsive:true,maintainAspectRatio:false,cutout:'62%',plugins:{legend:{position:'bottom',labels:{font:{size:10},boxWidth:10}},tooltip:{callbacks:{label:(ctx)=>`${ctx.label}: ${ctx.parsed.toFixed(1)}% · ${unit}`}}}}});
  }
  function ds(label,data,color,dash){return{label,data,borderColor:color,backgroundColor:color,tension:.25,pointRadius:2,pointHoverRadius:4,borderWidth:2,spanGaps:true,borderDash:dash||[]}}
  function yoy(values){return values.map((v,i)=>i===0||!Number.isFinite(v)||!Number.isFinite(values[i-1])||values[i-1]===0?null:(v/values[i-1]-1)*100);}
  function sameMonth(rows,key){
    const m=new Map(rows.map(r=>[r.period,r[key]]));
    return rows.map(r=>{const [y,mo]=r.period.split('-');const prev=m.get(`${Number(y)-1}-${mo}`);const v=r[key];return Number.isFinite(v)&&Number.isFinite(prev)&&prev!==0?(v/prev-1)*100:null;});
  }
  function sameQuarter(rows,key){
    const m=new Map(rows.map(r=>[r.period,r[key]]));
    return rows.map(r=>{const mt=String(r.period||'').match(/^(\d{4})-T([1-4])$/);if(!mt)return null;const prev=m.get(`${Number(mt[1])-1}-T${mt[2]}`),v=r[key];return Number.isFinite(v)&&Number.isFinite(prev)&&prev!==0?(v/prev-1)*100:null;});
  }
  function biennialPP(years,values){return values.map((v,i)=>{if(i===0)return null;const dy=years[i]-years[i-1];return Number.isFinite(v)&&Number.isFinite(values[i-1])&&dy>0?(v-values[i-1])/dy:null;});}
  function trendCycle(values,window=5){
    const half=Math.floor(window/2);
    return (values||[]).map((v,i)=>{
      const vals=[];
      for(let j=Math.max(0,i-half);j<=Math.min(values.length-1,i+half);j++) if(Number.isFinite(values[j])) vals.push(values[j]);
      return vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;
    });
  }
  function monthlyRange(start,end){
    if(!/^\d{4}-\d{2}$/.test(start||'')||!/^\d{4}-\d{2}$/.test(end||''))return [];
    let [y,m]=start.split('-').map(Number), [ey,em]=end.split('-').map(Number), out=[];
    while(y<ey||(y===ey&&m<=em)){out.push(`${y}-${String(m).padStart(2,'0')}`);m++;if(m===13){m=1;y++;}}
    return out;
  }
  function quarterFromMonthly(rows, keys){
    const groups=new Map();
    (rows||[]).forEach(r=>{
      const m=String(r.period||'').match(/^(\d{4})-(\d{2})$/); if(!m)return;
      const year=Number(m[1]), month=Number(m[2]), q=Math.ceil(month/3), k=`${year}-T${q}`;
      if(!groups.has(k))groups.set(k,[]); groups.get(k).push(r);
    });
    return [...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([period,rs])=>{
      const o={period,months:rs.length,partial:rs.length<3};
      keys.forEach(key=>{const vals=rs.map(r=>r[key]).filter(Number.isFinite);o[key]=vals.length?vals.reduce((a,b)=>a+b,0)/vals.length:null;});
      return o;
    });
  }
  function quarterEndFromMonthly(rows, keys){
    const groups=new Map();
    (rows||[]).forEach(r=>{
      const m=String(r.period||'').match(/^(\d{4})-(\d{2})$/); if(!m)return;
      const year=Number(m[1]), month=Number(m[2]), q=Math.ceil(month/3), k=`${year}-T${q}`;
      if(!groups.has(k))groups.set(k,[]); groups.get(k).push(r);
    });
    return [...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0])).map(([period,rs])=>{
      rs.sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      const last=rs[rs.length-1], mo=Number(String(last.period).slice(5,7));
      const expectedEnd=Number(period.slice(-1))*3;
      const o={period,partial:mo!==expectedEnd,sourcePeriod:last.period};
      keys.forEach(key=>o[key]=Number.isFinite(last[key])?last[key]:null);
      return o;
    });
  }
  function variationLine(id,labels,datasets,unit='Porcentaje (%)',suffix='%'){
    line(id,labels,datasets,{beginAtZero:false,yTitle:unit,suffix,decimals:1});
  }
  function noData(id,message='N/D · La serie oficial no está incluida en la descarga local.') {
    const el=document.getElementById(id); if(!el)return;
    const wrap=el.parentElement; if(!wrap)return;
    el.style.display='none';
    let note=wrap.querySelector('.chart-no-data');
    if(!note){ note=document.createElement('div'); note.className='chart-no-data'; wrap.appendChild(note); }
    note.textContent=message;
    note.style.cssText='height:100%;min-height:190px;display:flex;align-items:center;justify-content:center;text-align:center;padding:18px;color:#667085;font-size:13px;line-height:1.45;background:#fafbfc;border:1px dashed #d9dee5;border-radius:8px;box-sizing:border-box';
  }

  function displaySurfaceLabel(label,allCats=[]){
    const low=String(label||'').toLowerCase().replace(/²/g,'2');
    if(low.includes('38')&&(low.includes('menor')||low.includes('<38')))return '<38 m²';
    if(low.includes('45')&&(low.includes('menor')||low.includes('<45'))){
      const has38=allCats.some(x=>String(x).toLowerCase().includes('38'));
      return has38?'38–<45 m²':'<45 m²';
    }
    if((low.includes('45')&&low.includes('60'))||(low.includes('menor')&&low.includes('60')))return '45–<60 m²';
    if((low.includes('60')&&low.includes('80'))||(low.includes('menor')&&low.includes('80')))return '60–<80 m²';
    if((low.includes('mayor')&&low.includes('80'))||low.includes('80 m2 o mas')||low.includes('80 m² o más'))return '≥80 m²';
    return String(label||'Sin especificar');
  }
  function shareHistory(id,block,kind){
    const el=document.getElementById(id); if(!el||!window.Chart||!block||!Array.isArray(block.annual)||!block.annual.length)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    const palette=[brand,blue,green,gold,grey,'#6c5b7b','#4b7f91','#9b6a45'];
    const labels=block.annual.map(r=>`${r.year}${r.partial?'*':''}`);
    const cats=block.categories||[];
    const datasets=cats.map((cat,i)=>({
      label:kind==='surface'?displaySurfaceLabel(cat,cats):cat,
      data:block.annual.map(r=>r.total?((Number(r.values?.[cat]||0)/r.total)*100):null),
      counts:block.annual.map(r=>Number(r.values?.[cat]||0)),
      borderColor:palette[i%palette.length],backgroundColor:palette[i%palette.length],
      borderWidth:2.2,pointRadius:3,pointHoverRadius:5,tension:.2,spanGaps:false,fill:false
    }));
    new Chart(el,{type:'line',data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,usePointStyle:true,pointStyle:'line',font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>{const pct=Number.isFinite(ctx.parsed.y)?ctx.parsed.y.toFixed(1):'N/D';const n=ctx.dataset.counts?.[ctx.dataIndex]??0;return `${ctx.dataset.label}: ${pct}% · ${new Intl.NumberFormat('es-MX').format(n)} viviendas`;}}}},scales:{x:{grid:{display:false},ticks:{font:{size:9}}},y:{min:0,max:100,grid:{color:'#eef1f3'},ticks:{font:{size:9},callback:v=>`${v}%`},title:{display:true,text:'Participación en viviendas producidas (%)',font:{size:10}}}}}});
  }

  function ruvTotalHistory(id,block){
    const el=document.getElementById(id); if(!el||!window.Chart||!block||!Array.isArray(block.annual)||!block.annual.length)return;
    const rows=[...block.annual].sort((a,b)=>a.year-b.year);
    const labels=rows.map(r=>`${r.year}${r.partial?'*':''}`);
    const values=rows.map(r=>Number(r.total||0)/1000);
    line(id,labels,[ds('Viviendas producidas',values,brand)],{beginAtZero:false,yTitle:'Miles de viviendas',suffix:' mil',decimals:1});
  }
  function ruvSegmentHistory(id,block){
    const el=document.getElementById(id); if(!el||!window.Chart||!block||!Array.isArray(block.annual)||!block.annual.length)return;
    const old=Chart.getChart?Chart.getChart(el):null; if(old)old.destroy();
    const rows=[...block.annual].sort((a,b)=>a.year-b.year);
    const cats=block.categories||[];
    const palette=[brand,'#8d0b20','#d96a7c','#f0b6c0',grey,'#5e6670'];
    const datasets=cats.map((cat,i)=>({
      label:cat,
      data:rows.map(r=>r.total?Number(r.values?.[cat]||0)/r.total*100:null),
      counts:rows.map(r=>Number(r.values?.[cat]||0)),
      backgroundColor:palette[i%palette.length],
      borderColor:'#ffffff',borderWidth:1
    }));
    new Chart(el,{type:'bar',data:{labels:rows.map(r=>`${r.year}${r.partial?'*':''}`),datasets},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{position:'bottom',labels:{boxWidth:10,font:{size:10}}},tooltip:{callbacks:{label:(ctx)=>{const pct=Number.isFinite(ctx.parsed.y)?ctx.parsed.y.toFixed(1):'N/D';const n=ctx.dataset.counts?.[ctx.dataIndex]??0;return `${ctx.dataset.label}: ${pct}% · ${new Intl.NumberFormat('es-MX').format(n)} viviendas`;}}}},scales:{x:{stacked:true,grid:{display:false},ticks:{font:{size:9},maxRotation:0,minRotation:0}},y:{stacked:true,min:0,max:100,grid:{color:'#eef1f3'},ticks:{font:{size:9},callback:v=>`${v}%`},title:{display:true,text:'Participación en la producción (%)',font:{size:10}}}}}});
  }

  window.DashboardCharts={
    renderRuv(data){
      if(!data)return;
      ruvTotalHistory('prod-ruv-total',data.total);
      ruvSegmentHistory('prod-ruv-segment',data.segment);
    },
    render(){const D=window.DASHBOARD_DATA;
      // Resumen
      const sumShf=D.prices.shf_quarterly||[]; if(sumShf.length){
        const iccRaw=D.prices.icc_yoy_monthly||[];
        // Normaliza fechas ICC al mes calendario (YYYY-MM) para evitar pérdidas en el cruce.
        const iccMonthly=iccRaw.map(x=>{
          const f=String(x.period||'');
          const m=f.match(/^(\d{4})-(\d{2})/);
          return m ? {...x,period:`${m[1]}-${m[2]}`} : x;
        });
        // Ubicar cada observación trimestral SHF en el mes de cierre:
        // T1 = marzo, T2 = junio, T3 = septiembre, T4 = diciembre.
        // No se crean observaciones SHF en los otros meses.
        const shfMonths=[];
        sumShf.forEach(row=>{
          const m=String(row.period||'').match(/^(\d{4})-T([1-4])$/);
          if(m){
            const closingMonth=String(Number(m[2])*3).padStart(2,'0');
            shfMonths.push({period:`${m[1]}-${closingMonth}`,yoy:row.yoy});
          }
        });
        // Eje cronológico mensual compartido por SHF trimestral e ICC mensual.
        const periods=[...shfMonths.map(x=>x.period),...iccMonthly.map(x=>x.period)].filter(x=>/^\d{4}-\d{2}$/.test(x));
        const labels=periods.length?monthlyRange(periods.reduce((a,b)=>a<b?a:b),periods.reduce((a,b)=>a>b?a:b)):[];
        const iccMap=new Map(iccMonthly.map(x=>[x.period,Number.isFinite(x.yoy)?x.yoy:null]));
        const shfMap=new Map(shfMonths.map(x=>[x.period,Number.isFinite(x.yoy)?x.yoy:null]));
        const shfSeries=ds('SHF · variación anual trimestral',labels.map(period=>shfMap.get(period) ?? null),brand);
        shfSeries.tension=0;
        line('sum-shf',labels,[
          shfSeries,
          ds('ICC residencial · variación anual mensual',labels.map(period=>iccMap.get(period) ?? null),blue)
        ],{beginAtZero:false,yTitle:'Variación anual (%)',suffix:'%'});
      } else {line('sum-shf',D.prices.years,[ds('Variación anual porcentual',D.prices.shf_yoy,brand)],{beginAtZero:false,yTitle:'Variación anual porcentual (%)',suffix:'%'});}
      const sumEnoe=(D.labor.enoe_quarterly||[]).filter(x=>/^20\d{2}-T[1-4]$/.test(x.period||''));
      if(sumEnoe.length){
        const a=ds('Ocupación en construcción',sumEnoe.map(x=>Number.isFinite(x.total)?x.total/1000:null),brand); a.yAxisID='y'; a.unit=' millones'; a.decimals=2;
        const b=ds('Población ocupada total',sumEnoe.map(x=>Number.isFinite(x.occupied_total)?x.occupied_total/1000:null),blue); b.yAxisID='y1'; b.unit=' millones'; b.decimals=1;
        dualAxisLine('sum-employment',sumEnoe.map(x=>x.period),[a,b],{leftMin:4.5,leftMax:5.0,rightMin:58,rightMax:61,leftTitle:'Construcción · millones',rightTitle:'Total nacional · millones'});
      }

      // PIB de vivienda: las visualizaciones viven en Producción de vivienda
      bar('act-pib',D.activity.years,Object.entries(D.activity.components).map(([label,data],i)=>({label,data:data.map(v=>Number.isFinite(v)?v/1000000:null),backgroundColor:[brand,blue,grey,gold][i]})),{stacked:true,yTitle:'Billones de pesos corrientes',decimals:2});
      line('act-share',D.activity.years,[ds('Participación del PIB de vivienda',D.activity.participation,brand)],{beginAtZero:false,yTitle:'Porcentaje del PIB (%)',suffix:'%',yMin:5,yMax:5.8});

      // Actividad económica: respetar periodicidad de publicación
      const vabq=D.activity.vab_subsectors_quarterly||[];
      if(vabq.length){
        const a=ds('Construcción',vabq.map(x=>x.construction/1000000),blue); a.yAxisID='y'; a.unit=' billones'; a.decimals=2;
        const b=ds('Edificación',vabq.map(x=>x.edification/1000000),brand); b.yAxisID='y'; b.unit=' billones'; b.decimals=2;
        const c=ds('Obras de ingeniería civil',vabq.map(x=>x.civil/1000000),gold); c.yAxisID='y1'; c.unit=' billones'; c.decimals=3;
        const d=ds('Trabajos especializados',vabq.map(x=>x.specialized/1000000),green); d.yAxisID='y1'; d.unit=' billones'; d.decimals=3;
        dualAxisLine('act-vab',vabq.map(x=>x.period),[a,b,c,d],{leftTitle:'Construcción y edificación · billones de pesos de 2018',rightTitle:'Obras civiles y trabajos especializados · billones'});
        variationLine('act-vab-var',vabq.map(x=>x.period),[
          ds('Construcción',vabq.map(x=>x.construction_yoy),blue),
          ds('Edificación',vabq.map(x=>x.edification_yoy),brand),
          ds('Obras de ingeniería civil',vabq.map(x=>x.civil_yoy),gold),
          ds('Trabajos especializados',vabq.map(x=>x.specialized_yoy),green)
        ],'Variación anual real (%)','%');
      }
      const igaem=D.activity.igae_monthly||[];
      if(igaem.length){
        const labels=igaem.map(x=>x.period);
        line('act-igae',labels,[ds('IGAE construcción · mensual',igaem.map(x=>x.index),blue)],{beginAtZero:false,yTitle:'Índice · Base 2018=100',decimals:1});
        variationLine('act-igae-var',labels,[ds('Variación anual',igaem.map(x=>x.yoy),brand)],'Variación anual (%)','%');
      }
      const ifbm=D.activity.ifb_monthly||[];
      if(ifbm.length){
        line('act-ifb',ifbm.map(x=>x.period),[ds('IFB · construcción residencial',trendCycle(ifbm.map(x=>x.index)),blue)],{beginAtZero:false,yTitle:'Índice 2019=100 · a.e.',decimals:1});
      }
      const imaim=D.activity.imai_monthly||[];
      if(imaim.length){
        line('act-imai',imaim.map(x=>x.period),[ds('IMAI · construcción',trendCycle(imaim.map(x=>x.index)),blue)],{beginAtZero:false,yTitle:'Índice 2021=100 · a.e.',decimals:1});
      }

      // ENEC · actividad de empresas constructoras
      const enecA=D.activity.enec_production||[];
      const enecP=enecA.map(x=>x.period);
      if(enecA.length){
        line('act-enec-production',enecP,[ds('Edificación',trendCycle(enecA.map(x=>x.edification)),brand),ds('Sector público',trendCycle(enecA.map(x=>x.public)),blue),ds('Sector privado',trendCycle(enecA.map(x=>x.private)),green)],{beginAtZero:false,yTitle:'Índice · Base 2018=100'});
      }

      // Mercado laboral
      const eq=(D.labor.enoe_quarterly||[]).filter(x=>/^20\d{2}-T[1-4]$/.test(x.period));
      if(eq.length){
        const hasSplit=eq.every(x=>Number.isFinite(x.formal)&&Number.isFinite(x.informal));
        if(hasSplit) bar('lab-enoe',eq.map(x=>x.period),[{label:'Formal',data:eq.map(x=>x.formal),backgroundColor:blue},{label:'Informal',data:eq.map(x=>x.informal),backgroundColor:brand}],{stacked:true,yTitle:'Miles de empleos'});
        else bar('lab-enoe',eq.map(x=>x.period),[{label:'Empleos en construcción',data:eq.map(x=>x.total),backgroundColor:brand}],{yTitle:'Miles de empleos'});
        variationLine('lab-enoe-var',eq.map(x=>x.period),[ds('Variación anual',sameQuarter(eq,'total'),brand)],'Variación anual (%)','%');
      }
      else {const c=document.getElementById('lab-enoe'); if(c&&c.parentElement){c.style.display='none'; const m=document.createElement('div');m.className='note';m.style.padding='28px';m.innerHTML='<strong>Serie trimestral no disponible.</strong> El archivo ENOE no contiene observaciones válidas para mostrar.';c.parentElement.appendChild(m);}}
      const im=D.labor.imss_monthly||[]; if(im.length){const labels=im.map(x=>x.period), sets=[ds('Construcción',im.map(x=>Number.isFinite(x.construction)?x.construction/1000:null),blue)]; if(im.some(x=>x.edification!=null))sets.push(ds('Edificación',im.map(x=>Number.isFinite(x.edification)?x.edification/1000:null),brand)); line('lab-imss',labels,sets,{beginAtZero:false,yTitle:'Millones de trabajadores afiliados',decimals:2}); variationLine('lab-imss-var',labels,sets.length===1?[ds('Variación anual porcentual',sameMonth(im,'construction'),sets[0].borderColor)]:sets.map((z,i)=>ds(z.label,sameMonth(im,i===0?'construction':'edification'),z.borderColor)),'Variación anual porcentual (%)','%');} else {line('lab-imss',D.labor.years,[ds('Trabajadores afiliados IMSS',D.labor.imss.map(x=>x/1000),blue)],{beginAtZero:false,yTitle:'Millones de trabajadores afiliados',decimals:2}); variationLine('lab-imss-var',D.labor.years,[ds('Variación anual porcentual',yoy(D.labor.imss),blue)],'Variación anual porcentual (%)','%');}
      const p=D.labor.monthly_indices.map(x=>x.period);
      line('lab-personal',p,[ds('Construcción',D.labor.monthly_indices.map(x=>x.empl_const),blue),ds('Edificación',D.labor.monthly_indices.map(x=>x.empl_edif),brand)],{beginAtZero:false,yTitle:'Índice · Base 2018=100'});
      variationLine('lab-personal-var',p,[ds('Construcción',sameMonth(D.labor.monthly_indices,'empl_const'),blue),ds('Edificación',sameMonth(D.labor.monthly_indices,'empl_edif'),brand)],'Variación anual porcentual (%)','%');
      line('lab-hours',p,[ds('Construcción',trendCycle(D.labor.monthly_indices.map(x=>x.hours_const)),blue),ds('Edificación',trendCycle(D.labor.monthly_indices.map(x=>x.hours_edif)),brand)],{beginAtZero:false,yTitle:'Índice · Base 2018=100'});
      line('lab-rem',p,[ds('Construcción',trendCycle(D.labor.monthly_indices.map(x=>x.rem_const)),blue),ds('Edificación',trendCycle(D.labor.monthly_indices.map(x=>x.rem_edif)),brand)],{beginAtZero:false,yTitle:'Índice · Base 2018=100'});
      const salP=D.labor.salary_monthly.map(x=>x.period), salV=D.labor.salary_monthly.map(x=>x.daily*30.4);
      line('lab-salary',salP,[ds('SBC mensual promedio',salV,green)],{beginAtZero:false,yTitle:'Pesos corrientes por mes',suffix:' MXN/mes'});
      variationLine('lab-salary-var',salP,[ds('Variación anual porcentual',sameMonth(D.labor.salary_monthly,'daily'),green)],'Variación anual porcentual (%)','%');
      const wt=D.labor.enec_worker_type_index||[];
      if(wt.length){
        const wtLabels = wt.map(x => x.period);

        // Índices oficiales ENEC, base 2018=100
        line('lab-enec-worker-type', wtLabels, [
          ds('Personal total', wt.map(x => x.total), grey),
          ds('Obreros', wt.map(x => x.workers), brand),
          ds('Administrativos', wt.map(x => x.admin), blue)
        ], {
          beginAtZero: false,
          yTitle: 'Índice · base 2018=100',
          decimals: 1
        });

        // Variaciones porcentuales anuales
        variationLine('lab-enec-worker-type-var', wtLabels, [
          ds('Personal total', wt.map(x => x.total_yoy), grey),
          ds('Obreros', wt.map(x => x.workers_yoy), brand),
          ds('Administrativos', wt.map(x => x.admin_yoy), blue)
        ], 'Variación anual porcentual (%)', '%');
      }


      // Producción
      line('prod-flow',D.production.years,[ds('Registradas',D.production.registered,blue),ds('Inicio de obra',D.production.started,gold),ds('Terminadas / producción',D.production.finished,brand)],{beginAtZero:false,yTitle:'Miles de viviendas'});
      variationLine('prod-flow-var',D.production.years,[ds('Registradas',yoy(D.production.registered),blue),ds('Inicio de obra',yoy(D.production.started),gold),ds('Terminadas / producción',yoy(D.production.finished),brand)],'Variación anual porcentual (%)','%');
      const hv=D.production.enec_housing_yoy||[];
      if(hv.length){
        line('prod-enec-housing',hv.map(x=>x.period),[ds('Vivienda',hv.map(x=>x.housing),brand),ds('Edificación',hv.map(x=>x.edification),blue)],{beginAtZero:false,yTitle:'Variación anual porcentual (%)',suffix:'%'});
      }

      // Precios
      const hv2=D.activity.enec_edification_mm||[];
      if(hv2.length){
        line('prod-enec-housing-activity',hv2.map(x=>x.period),[ds('Producción de edificación',hv2.map(x=>x.value),brand)],{beginAtZero:false,yTitle:'Variación mensual real (%)',suffix:'%'});
      }
      const pvb=D.production.pvb||{rows:[]};
      const pvbOrder=['Contratadas','En construcción','Entregadas'];
      const pvbRows=(pvb.rows||[]).filter(x=>pvbOrder.includes(x.stage)).sort((a,b)=>pvbOrder.indexOf(a.stage)-pvbOrder.indexOf(b.stage));
      if(pvbRows.length){
        bar('prod-pvb',pvbRows.map(x=>x.stage),[{label:'Viviendas',data:pvbRows.map(x=>x.housing),backgroundColor:brand}],{beginAtZero:true,yTitle:'Viviendas',decimals:0});
      } else {
        noData('prod-pvb','N/D · No se encontraron datos válidos en pvb_avance.csv.');
      }
      const shq=D.prices.shf_quarterly||[];
      const shfIndexRows=shq.filter(x=>Number.isFinite(x.index));
      if(shfIndexRows.length>=2){line('price-shf-index',shfIndexRows.map(x=>x.period),[ds('Índice SHF',shfIndexRows.map(x=>x.index),blue)],{beginAtZero:false,yTitle:'Índice · base 2017=100',decimals:1});}
      else {noData('price-shf-index','El índice SHF oficial (base 2017=100) aún no está disponible en el CSV de niveles. La actualización automática intentará incorporarlo desde datos abiertos SHF. No se estiman niveles a partir de tasas anuales.');}
      if(shq.length){line('price-shf',shq.map(x=>x.period),[ds('Variación anual porcentual',shq.map(x=>x.yoy),brand)],{beginAtZero:false,yTitle:'Variación anual porcentual (%)',suffix:'%'});} else {line('price-shf',D.prices.years,[ds('Variación anual porcentual',D.prices.shf_yoy,brand)],{beginAtZero:false,yTitle:'Variación anual porcentual (%)',suffix:'%'});}
      // ICC: el nivel mensual y su variación anual se grafican por separado.
      // Nunca se empalman índices (base julio 2019=100) con porcentajes en una misma gráfica.
      const iccLevels=(D.prices.icc_monthly||[]).filter(x=>x.period&&Number.isFinite(x.general)).sort((a,b)=>String(a.period).localeCompare(String(b.period)));
      if(iccLevels.length){
        line('price-costs',iccLevels.map(x=>x.period),[ds('ICC residencial',iccLevels.map(x=>x.general),blue)],{beginAtZero:false,yTitle:'Índice · base julio 2025 = 100',decimals:1});
      } else {
        noData('price-costs','N/D · No se encontró la serie mensual de nivel del costo de construcción residencial.');
      }

      // Variación anual: se calcula desde el nivel cuando existe t-12 y se complementa
      // con observaciones mensuales verificadas del mismo indicador. Se grafican sólo observaciones disponibles; no se interpolan.
      const iccLevelMap=new Map(iccLevels.map(x=>[x.period,x.general]));
      const iccMap=new Map();
      iccLevels.forEach(x=>{const [y,m]=String(x.period).split('-');const prev=iccLevelMap.get(`${Number(y)-1}-${m}`);if(Number.isFinite(prev)&&prev!==0)iccMap.set(x.period,(x.general/prev-1)*100);});
      (D.prices.icc_yoy_monthly||[]).forEach(x=>{if(x.period&&Number.isFinite(x.yoy))iccMap.set(x.period,x.yoy);});
      const iccPeriods=[...iccMap.keys()].sort();
      if(iccPeriods.length){
        const labels=iccPeriods;
        variationLine('price-costs-var',labels,[ds('Variación anual',labels.map(p=>iccMap.get(p)),blue)],'Variación anual porcentual (%)','%');
      } else {
        noData('price-costs-var','N/D · No se encontró variación anual mensual del ICC residencial.');
      }

      const inppMonthly=D.prices.inpp_construction_monthly||[];
      if(inppMonthly.length){
        line('price-housing-components',inppMonthly.map(x=>x.period),[ds('Construcción',inppMonthly.map(x=>x.level),brand)],{beginAtZero:false,yTitle:'Índice · base julio 2025 = 100',decimals:1});
        variationLine('price-housing-components-var',inppMonthly.map(x=>x.period),[ds('Construcción',inppMonthly.map(x=>x.yoy),brand)],'Variación anual porcentual (%)','%');
        line('price-inpp-edification',inppMonthly.map(x=>x.period),[
          ds('Edificación',inppMonthly.map(x=>x.edification),blue),
          ds('Edificación residencial',inppMonthly.map(x=>x.residential),brand),
          ds('Edificación no residencial',inppMonthly.map(x=>x.nonresidential),gold)
        ],{beginAtZero:false,yTitle:'Índice · base julio 2025 = 100',decimals:1});
      } else {
        noData('price-housing-components','N/D · No se encontró la serie mensual oficial del INPP construcción.');
        noData('price-housing-components-var','N/D · No se encontró la variación anual del INPP construcción.');
        noData('price-inpp-edification','N/D · No se encontraron las series de edificación.');
      }

      // Subíndices del ICC: niveles y variación anual desde las mismas series oficiales.
      const iccm=D.prices.icc_components_monthly||[];
      if(iccm.length){
        line('price-inpp-components',iccm.map(x=>x.period),[
          ds('Materiales de construcción',iccm.map(x=>x.materials),blue),
          ds('Alquiler de maquinaria',iccm.map(x=>x.machinery),gold),
          ds('Mano de obra',iccm.map(x=>x.labor),brand)
        ],{beginAtZero:false,yTitle:'Índice · base julio 2025 = 100',decimals:1});
        variationLine('price-inpp-components-var',iccm.map(x=>x.period),[
          ds('Materiales de construcción',iccm.map(x=>x.materials_yoy),blue),
          ds('Alquiler de maquinaria',iccm.map(x=>x.machinery_yoy),gold),
          ds('Mano de obra',iccm.map(x=>x.labor_yoy),brand)
        ],'Variación anual porcentual (%)','%');
      }

      // Financiamiento: mantener la periodicidad anual disponible, separado del INPP.
      const py=D.prices.bridge_years||D.prices.inpp_years||[];
      if(py.length && (D.prices.bridge_rate||[]).length){
        line('price-financing',py,[
          ds('Costo de financiamiento / crédito puente',D.prices.bridge_rate||[],blue)
        ],{beginAtZero:false,yTitle:'Porcentaje (%)',suffix:'%',decimals:1});
      }

      // Condiciones habitacionales
      const cy=D.conditions.history_years||[];
      if(cy.length){
        line('cond-history',cy,[
          ds('Calidad y espacios',D.conditions.deprivation_history?.quality_space_pct||[],brand),
          ds('Servicios básicos',D.conditions.deprivation_history?.basic_services_pct||[],blue)
        ],{beginAtZero:false,yTitle:'Porcentaje de la población (%)',suffix:'%'});
      }
      const qd=D.conditions.qualitative_deficit||{};
      if(qd.components){
        bar('cond-needs-history',['Materiales','Espacios','Servicios'],[{label:'Viviendas con necesidad de mejoramiento',data:[qd.components.materials_pct,qd.components.spaces_pct,qd.components.services_pct],backgroundColor:brand}],{yTitle:'Porcentaje de viviendas (%)',suffix:'%'});
      }
      const th=D.conditions.tenure_history||{};
      if((th.years||[]).length){
        stackedPercentBar('cond-tenure-compare',th.years,[
          {label:'Propia totalmente pagada',data:th.own_paid_pct||[],backgroundColor:brand},
          {label:'Propia pagándose',data:th.paying_pct||[],backgroundColor:gold},
          {label:'Rentada',data:th.rented_pct||[],backgroundColor:blue},
          {label:'Otros',data:th.other_pct||[],backgroundColor:grey}
        ],{yTitle:'Porcentaje de viviendas (%)'});
      }
      const tt=D.conditions.tenure||{};
      pie('cond-tenure',['Propia totalmente pagada','Propia pagándose','Rentada','Otros'],[
        tt.own_strict,tt.paying,tt.rented,tt.other
      ]);
      const tru=D.conditions.tenure_rural_urban||{};
      if((tru.labels||[]).length){
        if(tru.four_categories){
        stackedPercentBar('cond-tenure-rural-urban',tru.labels,[
          {label:'Propia totalmente pagada',data:tru.four_categories.own_paid||[],backgroundColor:brand},
          {label:'Propia pagándose',data:tru.four_categories.paying||[],backgroundColor:gold},
          {label:'Rentada',data:tru.four_categories.rented||[],backgroundColor:blue},
          {label:'Otros',data:tru.four_categories.other||[],backgroundColor:grey}
        ],{horizontal:true,xTitle:'Porcentaje de viviendas ocupadas (%)'});
      } else {
        stackedPercentBar('cond-tenure-rural-urban',tru.labels,[
          {label:'Propia + pagándose',data:tru.own||[],backgroundColor:brand},
          {label:'No propia',data:tru.non_own||[],backgroundColor:grey}
        ],{horizontal:true,xTitle:'Porcentaje de viviendas ocupadas (%)'});
      }
      }
      const dep=D.conditions.deprivation||{};
      bar('cond-deprivation',['Calidad y espacios','Servicios básicos'],[{label:'Porcentaje de la población',data:[dep.quality_space_2024,dep.basic_services_2024],backgroundColor:brand}],{yTitle:'Porcentaje de la población (%)',suffix:'%'});
      const mat=D.conditions.materials||{};
      bar('cond-materials',['Muros','Techos','Pisos'],[{label:'Material inadecuado',data:[mat.walls_inadequate,mat.roofs_inadequate,mat.floor_inadequate],backgroundColor:blue}],{yTitle:'Porcentaje de viviendas (%)',suffix:'%'});
    }
  };
})();
