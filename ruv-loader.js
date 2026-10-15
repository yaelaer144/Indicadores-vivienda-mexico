(function(){
  const BASE='https://sniiv.sedatu.gob.mx/api/CuboAPI/GetProduccion';
  const START=2018, END=new Date().getFullYear();
  const SEGMENT_CATS=['Económica','Popular B1','Popular B2','Popular B3','Tradicional','Media-residencial'];
  function hasData(x){return x&&x.total&&Array.isArray(x.total.annual)&&x.total.annual.length>=5&&x.segment&&Array.isArray(x.segment.annual)&&x.segment.annual.length>=5;}
  function yr(r){const v=Number(r['año']??r.anio??r.year);return v>=2000?v:null;}
  function mo(r){const v=Number(r.mes??r.month);if(v>=1&&v<=12)return v;const map={enero:1,febrero:2,marzo:3,abril:4,mayo:5,junio:6,julio:7,agosto:8,septiembre:9,octubre:10,noviembre:11,diciembre:12};return map[String(r.mes||'').trim().toLowerCase()]||null;}
  function normalizeSegment(v){
    const s=String(v||'').trim().toLowerCase();
    if(s.includes('econ'))return 'Económica';
    if(s.includes('128'))return 'Popular B1';
    if(s.includes('158'))return 'Popular B2';
    if(s.includes('200')||s.includes('popular'))return 'Popular B3';
    if(s.includes('trad'))return 'Tradicional';
    if(s.includes('media')||s.includes('resid'))return 'Media-residencial';
    return null;
  }
  function aggregateSegment(rows){
    const g=new Map(),months=new Map();
    rows.forEach(r=>{
      const y=yr(r),cat=normalizeSegment(r.segmento); if(!y||!cat)return;
      const n=Number(r.viviendas)||0;
      if(!g.has(y))g.set(y,new Map()); g.get(y).set(cat,(g.get(y).get(cat)||0)+n);
      const m=mo(r); if(m){if(!months.has(y))months.set(y,new Set());months.get(y).add(m);}
    });
    const annual=[...g.keys()].sort((a,b)=>a-b).map(y=>{
      const values={};SEGMENT_CATS.forEach(c=>values[c]=g.get(y).get(c)||0);
      const total=Object.values(values).reduce((a,b)=>a+b,0),ms=months.get(y),maxm=ms&&ms.size?Math.max(...ms):null;
      return {year:y,months_observed:maxm,partial:!!maxm&&maxm<12,total,values};
    }).filter(r=>r.total>0);
    return {categories:SEGMENT_CATS,annual};
  }
  function mergeAnnual(base=[],live=[]){
    const m=new Map(); (base||[]).forEach(r=>m.set(Number(r.year),r)); (live||[]).forEach(r=>m.set(Number(r.year),r));
    return [...m.values()].sort((a,b)=>a.year-b.year);
  }
  async function fetchOfficial(){
    const url=`${BASE}/${START},${END}/00/000/anio,mes,segmento`;
    const res=await fetch(url,{cache:'no-store'}); if(!res.ok)throw new Error(`SNIIV HTTP ${res.status}`);
    const rows=await res.json(); if(!Array.isArray(rows)||!rows.some(r=>yr(r)))throw new Error('SNIIV no devolvió años históricos utilizables');
    return {rows,url};
  }
  async function load(){
    const cached=window.RUV_PRODUCTION;
    if(hasData(cached)){window.DashboardCharts?.renderRuv?.(cached);window.DashboardApp?.updateRuvStatus?.(cached);}
    window.DashboardApp?.setRuvLoading?.(hasData(cached)?'RUV · histórico visible · verificando actualización SNIIV…':'Consultando histórico oficial SNIIV/RUV…');
    try{
      const {rows}=await fetchOfficial();
      const liveSegment=aggregateSegment(rows);
      const liveTotal={annual:liveSegment.annual.map(r=>({year:r.year,months_observed:r.months_observed,partial:r.partial,total:r.total}))};
      const out={...(cached||{}),source:'SEDATU / SNIIV / RUV',endpoint:BASE,generated_at:new Date().toISOString(),fallback:false};
      out.segment={categories:SEGMENT_CATS,annual:mergeAnnual(cached?.segment?.annual,liveSegment.annual)};
      out.total={annual:mergeAnnual(cached?.total?.annual,liveTotal.annual)};
      const dated=rows.map(r=>{const y=yr(r),m=mo(r);return y&&m?`${y}-${String(m).padStart(2,'0')}`:null;}).filter(Boolean).sort();
      out.latest_period=dated.at(-1)||cached?.latest_period||null;
      window.RUV_PRODUCTION=out;window.DashboardCharts?.renderRuv?.(out);window.DashboardApp?.updateRuvStatus?.(out);
    }catch(e){console.warn(e);if(hasData(cached)){window.DashboardApp?.updateRuvStatus?.(cached);}else{window.DashboardApp?.setRuvLoading?.('No fue posible consultar SNIIV.');}}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>setTimeout(load,0));else setTimeout(load,0);
})();
