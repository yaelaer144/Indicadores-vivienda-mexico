(function(){
  const OUTLINE=[[-97.140008,25.869997],[-97.528072,24.992144],[-97.702946,24.272343],[-97.776042,22.93258],[-97.872367,22.444212],[-97.699044,21.898689],[-97.38896,21.411019],[-97.189333,20.635433],[-96.525576,19.890931],[-96.292127,19.320371],[-95.900885,18.828024],[-94.839063,18.562717],[-94.42573,18.144371],[-93.548651,18.423837],[-92.786114,18.524839],[-92.037348,18.704569],[-91.407903,18.876083],[-90.77187,19.28412],[-90.53359,19.867418],[-90.451476,20.707522],[-90.278618,20.999855],[-89.601321,21.261726],[-88.543866,21.493675],[-87.658417,21.458846],[-87.05189,21.543543],[-86.811982,21.331515],[-86.845908,20.849865],[-87.383291,20.255405],[-87.621054,19.646553],[-87.43675,19.472403],[-87.58656,19.04013],[-87.837191,18.259816],[-88.090664,18.516648],[-88.300031,18.499982],[-88.490123,18.486831],[-88.848344,17.883198],[-89.029857,18.001511],[-89.150909,17.955468],[-89.14308,17.808319],[-90.067934,17.819326],[-91.00152,17.817595],[-91.002269,17.254658],[-91.453921,17.252177],[-91.08167,16.918477],[-90.711822,16.687483],[-90.600847,16.470778],[-90.438867,16.41011],[-90.464473,16.069562],[-91.74796,16.066565],[-92.229249,15.251447],[-92.087216,15.064585],[-92.20323,14.830103],[-92.22775,14.538829],[-93.359464,15.61543],[-93.875169,15.940164],[-94.691656,16.200975],[-95.250227,16.128318],[-96.053382,15.752088],[-96.557434,15.653515],[-97.263592,15.917065],[-98.01303,16.107312],[-98.947676,16.566043],[-99.697397,16.706164],[-100.829499,17.171071],[-101.666089,17.649026],[-101.918528,17.91609],[-102.478132,17.975751],[-103.50099,18.292295],[-103.917527,18.748572],[-104.99201,19.316134],[-105.493038,19.946767],[-105.731396,20.434102],[-105.397773,20.531719],[-105.500661,20.816895],[-105.270752,21.076285],[-105.265817,21.422104],[-105.603161,21.871146],[-105.693414,22.26908],[-106.028716,22.773752],[-106.90998,23.767774],[-107.915449,24.548915],[-108.401905,25.172314],[-109.260199,25.580609],[-109.444089,25.824884],[-109.291644,26.442934],[-109.801458,26.676176],[-110.391732,27.162115],[-110.641019,27.859876],[-111.178919,27.941241],[-111.759607,28.467953],[-112.228235,28.954409],[-112.271824,29.266844],[-112.809594,30.021114],[-113.163811,30.786881],[-113.148669,31.170966],[-113.871881,31.567608],[-114.205737,31.524045],[-114.776451,31.799532],[-114.9367,31.393485],[-114.771232,30.913617],[-114.673899,30.162681],[-114.330974,29.750432],[-113.588875,29.061611],[-113.424053,28.826174],[-113.271969,28.754783],[-113.140039,28.411289],[-112.962298,28.42519],[-112.761587,27.780217],[-112.457911,27.525814],[-112.244952,27.171727],[-111.616489,26.662817],[-111.284675,25.73259],[-110.987819,25.294606],[-110.710007,24.826004],[-110.655049,24.298595],[-110.172856,24.265548],[-109.771847,23.811183],[-109.409104,23.364672],[-109.433392,23.185588],[-109.854219,22.818272],[-110.031392,22.823078],[-110.295071,23.430973],[-110.949501,24.000964],[-111.670568,24.484423],[-112.182036,24.738413],[-112.148989,25.470125],[-112.300711,26.012004],[-112.777297,26.32196],[-113.464671,26.768186],[-113.59673,26.63946],[-113.848937,26.900064],[-114.465747,27.14209],[-115.055142,27.722727],[-114.982253,27.7982],[-114.570366,27.741485],[-114.199329,28.115003],[-114.162018,28.566112],[-114.931842,29.279479],[-115.518654,29.556362],[-115.887365,30.180794],[-116.25835,30.836464],[-116.721526,31.635744],[-117.12776,32.53534],[-115.99135,32.61239],[-114.72139,32.72083],[-114.815,32.52528],[-113.30498,32.03914],[-111.02361,31.33472],[-109.035,31.34194],[-108.24194,31.34222],[-108.24,31.754854],[-106.50759,31.75452],[-106.1429,31.39995],[-105.63159,31.08383],[-105.03737,30.64402],[-104.70575,30.12173],[-104.45697,29.57196],[-103.94,29.27],[-103.11,28.97],[-102.48,29.76],[-101.6624,29.7793],[-100.9576,29.38071],[-100.45584,28.69612],[-100.11,28.11],[-99.52,27.54],[-99.3,26.84],[-99.02,26.37],[-98.24,26.06],[-97.53,25.84],[-97.140008,25.869997]];
  const STATE_POINTS=[{"key":"mx-ag","abbr":"AGS","lng":-102.296,"lat":21.876,"dx":-18,"dy":-12},{"key":"mx-bc","abbr":"BC","lng":-115.4678,"lat":32.6633,"dx":0,"dy":0},{"key":"mx-bs","abbr":"BCS","lng":-110.3108,"lat":24.1422,"dx":0,"dy":0},{"key":"mx-cm","abbr":"CAMP","lng":-90.5306,"lat":19.85,"dx":0,"dy":0},{"key":"mx-cs","abbr":"CHIS","lng":-93.1167,"lat":16.7528,"dx":0,"dy":0},{"key":"mx-ch","abbr":"CHIH","lng":-106.0889,"lat":28.6353,"dx":0,"dy":0},{"key":"mx-co","abbr":"COAH","lng":-101.0,"lat":25.4333,"dx":0,"dy":0},{"key":"mx-cl","abbr":"COL","lng":-103.7247,"lat":19.2433,"dx":-12,"dy":18},{"key":"mx-df","abbr":"CDMX","lng":-99.1333,"lat":19.4333,"dx":18,"dy":-21},{"key":"mx-dg","abbr":"DGO","lng":-104.6667,"lat":24.0167,"dx":0,"dy":0},{"key":"mx-gj","abbr":"GTO","lng":-101.2567,"lat":21.0178,"dx":-19,"dy":15},{"key":"mx-gr","abbr":"GRO","lng":-99.5,"lat":17.55,"dx":0,"dy":0},{"key":"mx-hg","abbr":"HGO","lng":-98.75,"lat":20.1,"dx":29,"dy":-20},{"key":"mx-ja","abbr":"JAL","lng":-103.3475,"lat":20.6767,"dx":-20,"dy":10},{"key":"mx-mx","abbr":"EDOMEX","lng":-99.6569,"lat":19.2925,"dx":-30,"dy":8},{"key":"mx-mi","abbr":"MICH","lng":-101.1922,"lat":19.7026,"dx":-23,"dy":10},{"key":"mx-mo","abbr":"MOR","lng":-99.2342,"lat":18.9186,"dx":2,"dy":26},{"key":"mx-na","abbr":"NAY","lng":-104.8931,"lat":21.5083,"dx":0,"dy":0},{"key":"mx-nl","abbr":"NL","lng":-100.3,"lat":25.6667,"dx":0,"dy":0},{"key":"mx-oa","abbr":"OAX","lng":-96.7253,"lat":17.0606,"dx":0,"dy":0},{"key":"mx-pu","abbr":"PUE","lng":-98.1833,"lat":19.0333,"dx":40,"dy":26},{"key":"mx-qt","abbr":"QRO","lng":-100.3928,"lat":20.5875,"dx":-23,"dy":-26},{"key":"mx-qr","abbr":"QROO","lng":-88.3053,"lat":18.5036,"dx":0,"dy":0},{"key":"mx-sl","abbr":"SLP","lng":-100.9761,"lat":22.1511,"dx":0,"dy":0},{"key":"mx-si","abbr":"SIN","lng":-107.3939,"lat":24.8069,"dx":0,"dy":0},{"key":"mx-so","abbr":"SON","lng":-110.9542,"lat":29.0989,"dx":0,"dy":0},{"key":"mx-tb","abbr":"TAB","lng":-92.9281,"lat":17.9892,"dx":0,"dy":0},{"key":"mx-tm","abbr":"TAMPS","lng":-99.1333,"lat":23.7333,"dx":0,"dy":0},{"key":"mx-tl","abbr":"TLAX","lng":-98.2382,"lat":19.3169,"dx":40,"dy":17},{"key":"mx-ve","abbr":"VER","lng":-96.9275,"lat":19.54,"dx":0,"dy":0},{"key":"mx-yu","abbr":"YUC","lng":-89.62,"lat":20.97,"dx":0,"dy":0},{"key":"mx-za","abbr":"ZAC","lng":-102.5736,"lat":22.7736,"dx":0,"dy":0}];

  function esc(s){return String(s).replace(/[&<>\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]));}
  function hexToRgb(h){const n=parseInt(h.slice(1),16);return [(n>>16)&255,(n>>8)&255,n&255];}
  function rgbToHex(rgb){return '#'+rgb.map(v=>Math.max(0,Math.min(255,Math.round(v))).toString(16).padStart(2,'0')).join('');}
  function colorScale(v,min,max){
    if(!Number.isFinite(v)) return '#d9dee3';
    const a=hexToRgb('#f7ccd4'), b=hexToRgb('#8d0b20');
    const t=max===min?0.5:Math.max(0,Math.min(1,(v-min)/(max-min)));
    return rgbToHex(a.map((x,i)=>x+(b[i]-x)*t));
  }
  function money(v){return Number.isFinite(v)?new Intl.NumberFormat('es-MX',{style:'currency',currency:'MXN',maximumFractionDigits:0}).format(v):'N/D';}
  function detailHtml(shf){
    const row=shf||{};
    const isNational=row.key==='mx-national'||row.state==='Nacional';
    const metric=(label,value,extra='')=>`<div class="quantile-item"><span>${label}</span><strong>${money(value)}</strong>${extra?`<small>${extra}</small>`:''}</div>`;
    return `<div class="state-name">${esc(row.state||'Nacional')}</div>
      <div class="state-metric shf">
        <span>SHF · distribución del valor de avalúo</span>
        <div class="quantile-grid">
          ${metric('Precio promedio',row.value,'promedio aritmético')}
          ${metric('Cuantil 25',row.p25,'25% de las operaciones por debajo')}
          ${metric('Cuantil 50 · mediana',row.p50,'50% de las operaciones por debajo')}
          ${metric('Cuantil 75',row.p75,'75% de las operaciones por debajo')}
        </div>
        <p><b>Qué mide:</b> distribución de los valores de avalúo de viviendas adquiridas mediante crédito hipotecario ${isNational?'a nivel nacional':'en la entidad seleccionada'}. SHF = Sociedad Hipotecaria Federal. Periodo: ${esc(row.period||D.meta?.latest_period||'N/D')}. Unidad: pesos corrientes por vivienda.</p>
      </div>`;
  }
  function sortRows(rows,mode){
    const out=rows.slice();
    if(mode==='price-asc') return out.sort((a,b)=>(a.value??Infinity)-(b.value??Infinity)||a.state.localeCompare(b.state,'es'));
    if(mode==='price-desc') return out.sort((a,b)=>(b.value??-Infinity)-(a.value??-Infinity)||a.state.localeCompare(b.state,'es'));
    return out.sort((a,b)=>a.state.localeCompare(b.state,'es'));
  }

  window.DashboardMap={render(){
    const D=window.DASHBOARD_DATA;
    const shfRows=(D.prices.shf_state_avg_price||[]).slice();
    const national=D.prices.shf_national_distribution||{key:'mx-national',state:'Nacional',value:D.prices.current?.avg_price,p25:D.prices.current?.p25,p50:D.prices.current?.median_price,p75:D.prices.current?.p75,period:D.meta?.latest_period||'N/D'};
    const target=document.getElementById('mx-map'); if(!target)return;
    const detail=document.getElementById('state-detail');
    const tbody=document.getElementById('state-price-table-body');
    const sorter=document.getElementById('state-price-sort');

    const W=940,H=560,mapH=475,pad=30;
    const lngs=OUTLINE.map(p=>p[0]), lats=OUTLINE.map(p=>p[1]);
    const minLng=Math.min(...lngs),maxLng=Math.max(...lngs),minLat=Math.min(...lats),maxLat=Math.max(...lats);
    const meanLat=(minLat+maxLat)/2;
    const lonScale=Math.cos(meanLat*Math.PI/180);
    const geoWidth=(maxLng-minLng)*lonScale,geoHeight=maxLat-minLat;
    const scale=Math.min((W-pad*2)/geoWidth,(mapH-pad*2)/geoHeight);
    const usedWidth=geoWidth*scale,usedHeight=geoHeight*scale;
    const offsetX=(W-usedWidth)/2,offsetY=(mapH-usedHeight)/2;
    const project=([lng,lat])=>[offsetX+(lng-minLng)*lonScale*scale,offsetY+(maxLat-lat)*scale];
    const outlinePath=OUTLINE.map((p,i)=>{const [x,y]=project(p);return `${i?'L':'M'}${x.toFixed(1)},${y.toFixed(1)}`;}).join(' ')+' Z';
    const shfByKey=Object.fromEntries(shfRows.map(r=>[r.key,r]));
    const vals=shfRows.filter(r=>Number.isFinite(r.value)).map(r=>r.value);
    const min=Math.min(...vals),max=Math.max(...vals);

    const connectors=[]; const markers=[];
    STATE_POINTS.forEach(s=>{
      const shf=shfByKey[s.key]||{key:s.key,state:s.abbr,value:null,p25:null,p50:null,p75:null,period:D.meta?.latest_period||'N/D'};
      const [x0,y0]=project([s.lng,s.lat]); const x=x0+s.dx, y=y0+s.dy;
      if(s.dx||s.dy) connectors.push(`<line x1="${x0.toFixed(1)}" y1="${y0.toFixed(1)}" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" class="map-link"/>`);
      const fill=colorScale(shf.value,min,max);
      const title=`${shf.state}: SHF ${Number.isFinite(shf.value)?money(shf.value):'N/D'}`;
      markers.push(`<g class="state-marker" data-key="${esc(s.key)}" tabindex="0" role="button" aria-label="${esc(title)}"><title>${esc(title)}</title><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="14" fill="${fill}"/><text x="${x.toFixed(1)}" y="${(y+3.2).toFixed(1)}">${esc(s.abbr)}</text></g>`);
    });

    target.innerHTML=`<svg class="local-mx-map" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Mapa de México con precio promedio estatal de vivienda SHF">
      <defs><linearGradient id="price-gradient" x1="0" x2="1"><stop offset="0%" stop-color="#f7ccd4"/><stop offset="100%" stop-color="#8d0b20"/></linearGradient></defs>
      <path d="${outlinePath}" class="mexico-outline"/>${connectors.join('')}${markers.join('')}
      <g class="map-legend" transform="translate(28,505)"><rect class="map-legend-bg" x="-12" y="-27" width="330" height="65" rx="9"/><text x="0" y="-10">SHF · precio promedio · pesos corrientes</text><rect x="0" y="0" width="235" height="12" rx="6" fill="url(#price-gradient)"/><text x="0" y="29">${money(min)}</text><text x="235" y="29" text-anchor="end">${money(max)}</text><rect x="250" y="0" width="12" height="12" rx="2" fill="#d9dee3"/><text x="268" y="10">N/D</text></g>
    </svg>`;

    let selectedKey=null;
    const select=(key,scroll=false)=>{
      selectedKey=key&&shfByKey[key]?key:null;
      target.querySelectorAll('.state-marker').forEach(g=>g.classList.toggle('selected',g.dataset.key===selectedKey));
      if(detail) detail.innerHTML=detailHtml(selectedKey?shfByKey[selectedKey]:national);
      if(tbody){
        tbody.querySelectorAll('tr').forEach(tr=>tr.classList.toggle('selected',tr.dataset.key===selectedKey));
        const row=selectedKey?tbody.querySelector(`tr[data-key="${selectedKey}"]`):tbody.querySelector('tr[data-key="mx-national"]');
        // La selección sólo resalta la fila; nunca desplaza la página hacia el listado.
      }
    };
    const renderTable=(mode='alpha')=>{
      if(!tbody)return;
      const nationalRow=`<tr data-key="mx-national" class="national-row"><td>Nacional</td><td class="price-cell">${money(national.value)}</td></tr>`;
      tbody.innerHTML=nationalRow+sortRows(shfRows,mode).map(r=>`<tr data-key="${esc(r.key)}"><td>${esc(r.state)}</td><td class="price-cell">${money(r.value)}</td></tr>`).join('');
      tbody.querySelectorAll('tr').forEach(tr=>{
        tr.addEventListener('click',()=>{
          if(tr.dataset.key==='mx-national') select(null,false); else select(tr.dataset.key,false);
        });
        tr.addEventListener('dblclick',e=>{e.preventDefault();select(null,false);});
      });
      // Reapply visual selection after resorting.
      select(selectedKey,false);
    };
    target.querySelectorAll('.state-marker').forEach(g=>{
      g.addEventListener('click',()=>select(g.dataset.key,false));
      g.addEventListener('dblclick',e=>{e.preventDefault();select(null,false);});
      g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(g.dataset.key,false);} if(e.key==='Escape'){select(null,false);}});
    });
    if(sorter) sorter.addEventListener('change',()=>renderTable(sorter.value));
    renderTable(sorter?.value||'alpha');
    select(null,false);
  }};
})();
