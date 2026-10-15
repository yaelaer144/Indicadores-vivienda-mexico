#!/usr/bin/env python3
"""Actualiza series INEGI del dashboard mediante la API del Banco de Indicadores.

Seguridad:
- Nunca sobrescribe un CSV si la API devuelve vacío/incompleto.
- Para series sin ID fijado, resuelve candidatos por catálogo y exige coincidencia
  con el histórico ya validado del dashboard antes de aceptar el indicador.
- Guarda los IDs resueltos para ejecuciones siguientes.
"""
import csv, json, math, os, re, statistics, unicodedata, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
START_MONTH='2016-01'
START_QUARTER='2018-T1'
START_YEAR='2016'
TOKEN=os.environ.get('INEGI_API_TOKEN','').strip().strip('\"').strip("'")
API='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{id}/es/00/false/BISE/2.0/{token}?type=json'
CAT='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/CL_INDICATOR/null/es/BIE-BISE/2.0/{token}?type=json'
UA='dashboard-vivienda-infonavit/2.0 (+GitHub Actions)'
RESOLVED=ROOT/'inegi_resolved_ids.json'
STATUS=ROOT/'auto_update_status.json'

# IDs ya verificados en el proyecto.
PRICE_IDS={
 'general':1660002,'materiales':1660003,'maquinaria':1660004,'mano_obra':1660005,
 'construccion':1700226,'edificacion':1700227,'edificacion_residencial':1700228,
 'edificacion_no_residencial':1700232,'obra_civil':1700239,
}

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()

def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r: return json.load(r)

def api_series(indicator_id, expected='monthly'):
    d=get_json(API.format(id=indicator_id,token=TOKEN))
    if not d.get('Series'): raise RuntimeError(f'INEGI sin Series para {indicator_id}')
    s=d['Series'][0]; obs=s.get('OBSERVATIONS') or []
    raw=[]
    for x in obs:
        v=x.get('OBS_VALUE')
        if v in (None,''): continue
        try:v=float(str(v).replace(',',''))
        except:continue
        raw.append((str(x.get('TIME_PERIOD','')).strip(),v))
    if not raw: raise RuntimeError(f'INEGI devolvió serie vacía para {indicator_id}')
    out={}
    for p,v in raw:
        pp=normalize_period(p,expected)
        if pp: out[pp]=v
    if not out: raise RuntimeError(f'No se reconocieron periodos para {indicator_id}')
    return out, {'id':str(indicator_id),'description':s.get('INDICADOR') or s.get('TOPIC') or '', 'freq':s.get('FREQ'),'unit':s.get('UNIT'),'lastupdate':s.get('LASTUPDATE')}

def normalize_period(p, expected):
    p=p.strip()
    if expected=='annual':
        m=re.search(r'(19|20)\d{2}',p); return m.group(0) if m else None
    if expected=='quarterly':
        m=re.match(r'^((?:19|20)\d{2})[-/]?[TQ]?0?([1-4])$',p,re.I)
        if m:return f'{m.group(1)}-T{int(m.group(2))}'
        m=re.match(r'^((?:19|20)\d{2})[-/]([0-9]{2})$',p)
        if m and 1<=int(m.group(2))<=4:return f'{m.group(1)}-T{int(m.group(2))}'
        return None
    m=re.match(r'^((?:19|20)\d{2})[-/]?([0-1]\d)$',p)
    if m and 1<=int(m.group(2))<=12:return f'{m.group(1)}-{int(m.group(2)):02d}'
    return None

def read_csv(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def write_csv(path,rows,fields):
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
    tmp.replace(path)

def numeric(x):
    try:return float(str(x).replace(',',''))
    except:return None

def load_resolved():
    try:return json.loads(RESOLVED.read_text(encoding='utf-8'))
    except:return {}

def load_catalog():
    d=get_json(CAT.format(token=TOKEN))
    codes=d.get('CODE') or []
    if not codes: raise RuntimeError('INEGI: catálogo sin indicadores; comprobar fuente y token')
    return codes

def candidate_score(desc, include, exclude):
    n=norm(desc)
    if any(norm(x) in n for x in exclude): return -999
    inc=[norm(x) for x in include]
    score=sum(10 for x in inc if x in n)
    # recompensa palabras individuales para tolerar pequeñas diferencias en catálogo
    words=set(n.split())
    score += sum(1 for x in inc for w in x.split() if w in words)
    return score

def overlap_error(series, rows, period_col, value_col):
    pairs=[]
    for r in rows[-36:]:
        p=str(r.get(period_col,'')).strip(); old=numeric(r.get(value_col)); new=series.get(p)
        if old is not None and new is not None and abs(old)>1e-9:
            pairs.append(abs(new-old)/max(abs(old),1e-9))
    if len(pairs)<3:return None
    return statistics.median(pairs)

def resolve(key, include, exclude, expected, path, period_col, value_col, catalog, resolved, max_candidates=8):
    # Override opcional por secret/env; útil si INEGI cambia descripciones.
    env=os.environ.get('INEGI_ID_'+re.sub(r'[^A-Z0-9]+','_',key.upper()))
    ids=[]
    if env: ids.append(str(env))
    if key in resolved: ids.append(str(resolved[key]))
    scored=[]
    for c in catalog:
        desc=c.get('Description',''); sc=candidate_score(desc,include,exclude)
        if sc>0: scored.append((sc,str(c.get('value')),desc))
    scored.sort(reverse=True,key=lambda x:x[0])
    ids += [x[1] for x in scored[:max_candidates] if x[1]]
    ids=list(dict.fromkeys(ids))
    if not ids: raise RuntimeError(f'{key}: falta ID validado; el catálogo de INEGI no responde y no se puede resolver automáticamente')
    old=read_csv(path)
    best=None
    for iid in ids:
        try: ser,meta=api_series(iid,expected)
        except Exception: continue
        err=overlap_error(ser,old,period_col,value_col)
        if err is None: continue
        item=(err,iid,ser,meta)
        if best is None or err<best[0]:best=item
        if err<0.002:break
    if best is None or best[0]>0.03:
        raise RuntimeError(f'No se validó un indicador INEGI para {key}; mejor error={None if best is None else best[0]:}')
    resolved[key]=best[1]
    return best[2],best[3],best[0]

def yoy(rows,key,lag,period_key='periodo',out_key=None):
    out_key=out_key or key+'_yoy'; vals={r[period_key]:numeric(r.get(key)) for r in rows}
    ordered=sorted(vals)
    pos={p:i for i,p in enumerate(ordered)}
    for r in rows:
        i=pos[r[period_key]]; v=numeric(r.get(key)); prev=vals.get(ordered[i-lag]) if i>=lag else None
        r[out_key]=(v/prev-1)*100 if v is not None and prev not in (None,0) else ''

def mom(rows,key,period_key='periodo',out_key='variacion_mensual'):
    vals={r[period_key]:numeric(r.get(key)) for r in rows}; ordered=sorted(vals); pos={p:i for i,p in enumerate(ordered)}
    for r in rows:
        i=pos[r[period_key]];v=numeric(r.get(key));prev=vals.get(ordered[i-1]) if i>=1 else None
        r[out_key]=(v/prev-1)*100 if v is not None and prev not in (None,0) else ''

def update_prices():
    S={k:api_series(v,'monthly')[0] for k,v in PRICE_IDS.items()}
    periods=sorted(set(S['general']) & set(S['materiales']) & set(S['maquinaria']) & set(S['mano_obra']))
    rows=[{'periodo':p,**{k:S[k].get(p) for k in ['general','materiales','maquinaria','mano_obra']}} for p in periods if p>=START_MONTH]
    for k in ['general','materiales','maquinaria','mano_obra']:yoy(rows,k,12)
    if len(rows)<24: raise RuntimeError('INEGI precios: menos de 24 observaciones; se conserva histórico')
    write_csv(ROOT/'icc_incevis_base2025_mensual.csv',rows,['periodo','general','materiales','maquinaria','mano_obra','general_yoy','materiales_yoy','maquinaria_yoy','mano_obra_yoy'])
    keys=['construccion','edificacion','edificacion_residencial','edificacion_no_residencial','obra_civil']
    periods=sorted(set.intersection(*(set(S[k]) for k in keys)))
    rows=[{'periodo':p,**{k:S[k].get(p) for k in keys}} for p in periods if p>=START_MONTH]
    for k in keys:yoy(rows,k,12)
    if len(rows)<24: raise RuntimeError('INEGI INPP: menos de 24 observaciones; se conserva histórico')
    write_csv(ROOT/'inpp_construccion_edificacion_base2025_mensual.csv',rows,['periodo']+keys+[k+'_yoy' for k in keys])
    return rows[-1]['periodo'] if rows else None

def update_simple_monthly(name,key,spec,catalog,resolved):
    path=ROOT/name; old=read_csv(path)
    ser,meta,err=resolve(key,spec['include'],spec.get('exclude',[]),'monthly',path,'periodo','indice',catalog,resolved)
    periods=sorted(set(ser) | {r.get('periodo') for r in old if r.get('periodo')})
    rows=[{'periodo':p,'indice':ser.get(p, next((numeric(r.get('indice')) for r in old if r.get('periodo')==p),None))} for p in periods if p>=START_MONTH]
    rows=[r for r in rows if r['indice'] is not None]
    mom(rows,'indice');yoy(rows,'indice',12,out_key='variacion_anual')
    write_csv(path,rows,['periodo','indice','variacion_mensual','variacion_anual'])
    return {'id':meta['id'],'error_overlap':err,'ultimo':rows[-1]['periodo']}

def update_vab(catalog,resolved):
    path=ROOT/'vab_construccion_subsectores_trimestral.csv'
    specs={
      'construccion_mdp_2018':('vab_construccion',['producto interno bruto trimestral','construccion'],['variacion','porcentual','edificacion','ingenieria civil','trabajos especializados']),
      'edificacion_mdp_2018':('vab_edificacion',['producto interno bruto trimestral','edificacion'],['variacion','porcentual','residencial','no residencial']),
      'obra_civil_mdp_2018':('vab_obra_civil',['producto interno bruto trimestral','construccion de obras de ingenieria civil'],['variacion','porcentual']),
      'trabajos_especializados_mdp_2018':('vab_trabajos_especializados',['producto interno bruto trimestral','trabajos especializados para la construccion'],['variacion','porcentual']),
    }
    series={};info={}
    for col,(key,inc,exc) in specs.items():
        ser,meta,err=resolve(key,inc,exc,'quarterly',path,'periodo',col,catalog,resolved);series[col]=ser;info[col]={'id':meta['id'],'error_overlap':err}
    periods=sorted(set.intersection(*(set(x) for x in series.values())))
    rows=[{'periodo':p,**{c:series[c][p] for c in series}} for p in periods if p>=START_QUARTER]
    for c,out in [('construccion_mdp_2018','construccion_yoy'),('edificacion_mdp_2018','edificacion_yoy'),('obra_civil_mdp_2018','obra_civil_yoy'),('trabajos_especializados_mdp_2018','trabajos_especializados_yoy')]:yoy(rows,c,4,out_key=out)
    write_csv(path,rows,['periodo']+list(series)+['construccion_yoy','edificacion_yoy','obra_civil_yoy','trabajos_especializados_yoy'])
    info['ultimo']=rows[-1]['periodo'];return info

def update_enec_labor(catalog,resolved):
    path=ROOT/'enec_indices_laborales_mensual.csv'
    defs={
      'personal_construccion':('enec_personal_construccion',['personal ocupado total','sector 23 construccion'],['variacion','entidad federativa']),
      'personal_edificacion':('enec_personal_edificacion',['personal ocupado total','236 edificacion'],['variacion','entidad federativa']),
      'horas_construccion':('enec_horas_construccion',['horas trabajadas','sector 23 construccion'],['variacion','entidad federativa']),
      'horas_edificacion':('enec_horas_edificacion',['horas trabajadas','236 edificacion'],['variacion','entidad federativa']),
      'remuneraciones_construccion':('enec_rem_construccion',['remuneraciones medias reales','sector 23 construccion'],['variacion','entidad federativa']),
      'remuneraciones_edificacion':('enec_rem_edificacion',['remuneraciones medias reales','236 edificacion'],['variacion','entidad federativa']),
    }
    series={};info={}
    for col,(key,inc,exc) in defs.items():
        ser,meta,err=resolve(key,inc,exc,'monthly',path,'periodo',col,catalog,resolved);series[col]=ser;info[col]={'id':meta['id'],'error_overlap':err}
    periods=sorted(set.intersection(*(set(x) for x in series.values())))
    rows=[{'periodo':p,**{c:series[c][p] for c in series},'base':'2018=100','fuente':'INEGI · ENEC'} for p in periods if p>=START_MONTH]
    write_csv(path,rows,['periodo']+list(series)+['base','fuente']);info['ultimo']=rows[-1]['periodo'];return info

def update_csvm(catalog,resolved):
    path=ROOT/'csvm_pib_vivienda_anual.csv'
    defs={
      'pib_total_mdp':('csvm_pib_total',['cuenta satelite de vivienda','producto interno bruto','vivienda'],['porcentaje','participacion','variacion']),
      'participacion_pib_pct':('csvm_participacion',['cuenta satelite de vivienda','participacion','producto interno bruto'],['variacion']),
      'edificacion_mdp':('csvm_edificacion',['cuenta satelite de vivienda','edificacion'],['porcentaje','variacion']),
      'adquisicion_mdp':('csvm_adquisicion',['cuenta satelite de vivienda','adquisicion'],['porcentaje','variacion']),
      'uso_mdp':('csvm_uso',['cuenta satelite de vivienda','uso de vivienda'],['porcentaje','variacion']),
      'regulacion_fomento_mdp':('csvm_regulacion',['cuenta satelite de vivienda','regulacion','fomento'],['porcentaje','variacion']),
    }
    series={};info={}
    for col,(key,inc,exc) in defs.items():
        ser,meta,err=resolve(key,inc,exc,'annual',path,'anio',col,catalog,resolved);series[col]=ser;info[col]={'id':meta['id'],'error_overlap':err}
    periods=sorted(set.intersection(*(set(x) for x in series.values())))
    rows=[{'anio':p,**{c:series[c][p] for c in series},'fuente':'INEGI · Cuenta Satélite de Vivienda de México'} for p in periods if p>=START_YEAR]
    write_csv(path,rows,['anio']+list(series)+['fuente']);info['ultimo']=rows[-1]['anio'];return info

def main():
    if not TOKEN: raise SystemExit('Falta el secret INEGI_API_TOKEN')
    resolved=load_resolved(); catalog=load_catalog(); report={}
    group=os.environ.get('INEGI_UPDATE_GROUP','all').strip().lower()
    if group in ('all','monthly'):
        try:
            report['precios']={'status':'actualizado','ultimo':update_prices(),'ids':PRICE_IDS}
        except Exception as exc:
            report['precios']={'status':'error','error':str(exc)}
    tasks=[
      ('igae',lambda:update_simple_monthly('igae_construccion_mensual.csv','igae_construccion',{'include':['indicador global de la actividad economica','construccion'],'exclude':['variacion porcentual']},catalog,resolved)),
      ('imai',lambda:update_simple_monthly('imai_construccion_mensual.csv','imai_construccion',{'include':['indicador mensual de la actividad industrial','construccion'],'exclude':['variacion porcentual']},catalog,resolved)),
      ('ifb',lambda:update_simple_monthly('ifb_residencial_mensual.csv','ifb_residencial',{'include':['inversion fija bruta','construccion residencial'],'exclude':['variacion porcentual']},catalog,resolved)),
      ('vab',lambda:update_vab(catalog,resolved)),
      ('enec_labor',lambda:update_enec_labor(catalog,resolved)),
      ('csvm',lambda:update_csvm(catalog,resolved)),
    ]
    tasks=[(name,fn) for name,fn in tasks if group=='all' or (group=='monthly' and name in ('igae','imai','ifb','enec_labor')) or (group=='quarterly' and name=='vab') or (group=='annual' and name=='csvm')]
    for name,fn in tasks:
        try: report[name]={'status':'actualizado',**fn()}
        except Exception as e: report[name]={'status':'conservado_sin_cambio','error':str(e)}
    RESOLVED.write_text(json.dumps(resolved,ensure_ascii=False,indent=2),encoding='utf-8')
    report['updated_at_utc']=datetime.now(timezone.utc).isoformat()
    report['inicio_historico']=START_YEAR
    report['updated_by']='GitHub Actions / INEGI API'
    STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    errors=[k for k,v in report.items() if isinstance(v,dict) and v.get('status') in ('error','conservado_sin_cambio')]
    if errors: raise SystemExit('INEGI: series sin actualizar: '+', '.join(errors))
    if any(isinstance(v,dict) and v.get('status')=='conservado_sin_cambio' for v in report.values()):
        raise SystemExit('Algunas series INEGI no se actualizaron; consulte auto_update_status.json')

if __name__=='__main__': main()

