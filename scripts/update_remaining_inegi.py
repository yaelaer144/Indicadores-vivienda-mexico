#!/usr/bin/env python3
import csv,json,os,re,statistics,unicodedata,urllib.request,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TOKEN=os.environ.get('INEGI_API_TOKEN','').strip().strip('\"').strip("'")
START='2016-01'
API='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{id}/es/00/false/BISE/2.0/{token}?type=json'
CAT='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/CL_INDICATOR/null/es/BIE-BISE/2.0/{token}?type=json'
UA='dashboard-vivienda-infonavit/3.0'
RES=ROOT/'inegi_resolved_ids.json'

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9]+',' ',s).strip()
def getj(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'});return json.load(urllib.request.urlopen(req,timeout=120))
def period(p):
 m=re.match(r'^((?:19|20)\d{2})[-/]?([0-1]\d)$',str(p).strip());
 return f'{m.group(1)}-{int(m.group(2)):02d}' if m and 1<=int(m.group(2))<=12 else None
def api(i):
 d=getj(API.format(id=i,token=TOKEN)); s=(d.get('Series') or [])[0]; out={}
 for x in s.get('OBSERVATIONS') or []:
  p=period(x.get('TIME_PERIOD'));v=x.get('OBS_VALUE')
  try:v=float(str(v).replace(',',''))
  except:continue
  if p:out[p]=v
 return out,s.get('INDICADOR') or s.get('TOPIC') or ''
def read(path):
 if not path.exists():return []
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def num(x):
 try:return float(str(x).replace(',',''))
 except:return None
def err(ser,rows,pcol,vcol):
 es=[]
 for r in rows[-48:]:
  p=r.get(pcol); a=num(r.get(vcol)); b=ser.get(p)
  if a is not None and b is not None and abs(a)>1e-9:es.append(abs(b-a)/abs(a))
 return statistics.median(es) if len(es)>=3 else None
def resolve(key,include,exclude,path,pcol,vcol,catalog,resolved):
 ids=[]
 env=os.environ.get('INEGI_ID_'+re.sub(r'[^A-Z0-9]+','_',key.upper()))
 if env:ids.append(env)
 if key in resolved:ids.append(str(resolved[key]))
 scored=[]
 for c in catalog:
  desc=c.get('Description',''); n=norm(desc)
  if any(norm(x) in n for x in exclude):continue
  score=sum(10 for x in include if norm(x) in n)+sum(1 for x in include for w in norm(x).split() if w in set(n.split()))
  if score>0 and c.get('value'):scored.append((score,str(c['value']),desc))
 scored.sort(reverse=True)
 ids+= [i for _,i,_ in scored[:12]];ids=list(dict.fromkeys(ids)); old=read(path);best=None
 for i in ids:
  try:s,d=api(i)
  except:continue
  e=err(s,old,pcol,vcol)
  if e is None:continue
  if best is None or e<best[0]:best=(e,i,s,d)
  if e<0.002:break
 if best is None or best[0]>0.04:raise RuntimeError(f'{key}: sin serie validada; error={None if best is None else best[0]}')
 resolved[key]=best[1];return best[2],best[3],best[0]
def write(path,rows,fields):
 t=path.with_suffix('.csv.tmp')
 with t.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 t.replace(path)
def pct_mom(s):
 ps=sorted(s);out={}
 for i,p in enumerate(ps):
  out[p]=((s[p]/s[ps[i-1]]-1)*100) if i and s[ps[i-1]] else None
 return out
def pct_yoy(s):
 out={}
 for p,v in s.items():
  y,m=p.split('-');q=f'{int(y)-1}-{m}';out[p]=((v/s[q]-1)*100) if q in s and s[q] else None
 return out

def main():
 if not TOKEN:raise SystemExit('Falta INEGI_API_TOKEN')
 try:
  catalog=getj(CAT.format(token=TOKEN)).get('CODE') or []
 except Exception as exc:
  print(f"Catalogo INEGI no disponible: {type(exc).__name__}; usando identificadores conocidos",flush=True)
  catalog=[]
 try:resolved=json.loads(RES.read_text(encoding='utf-8'))
 except:resolved={}
 status={}
 # ENEC valor de producción: índices/niveles ya validados contra CSV local
 p=ROOT/'enec_actividad_historica.csv'
 specs={
  'edificacion_indice':('enec_prod_edificacion',['indice','valor de produccion','edificacion'],['variacion','entidad federativa']),
  'publico_indice':('enec_prod_publica',['indice','valor de produccion','sector publico'],['variacion','entidad federativa']),
  'privado_indice':('enec_prod_privada',['indice','valor de produccion','sector privado'],['variacion','entidad federativa'])}
 ss={}
 for col,(k,inc,exc) in specs.items():ss[col],_,e=resolve(k,inc,exc,p,'periodo',col,catalog,resolved);status[k]=e
 periods=sorted(set.intersection(*(set(v) for v in ss.values())))
 write(p,[{'periodo':x,**{c:ss[c][x] for c in ss}} for x in periods if x>=START],['periodo']+list(specs))
 # Tipo de trabajador: INEGI publica variaciones mensuales; se validan directamente contra el CSV existente.
 p=ROOT/'enec_personal_tipo_variacion_mensual.csv'
 specs={
  'total_mom_pct':('enec_personal_total_mom',['variacion porcentual mensual','personal ocupado total','construccion'],['entidad federativa','edificacion']),
  'obreros_mom_pct':('enec_obreros_mom',['variacion porcentual mensual','obreros','construccion'],['entidad federativa']),
  'administrativos_mom_pct':('enec_admin_mom',['variacion porcentual mensual','empleados','construccion'],['entidad federativa'])}
 ss={}
 for col,(k,inc,exc) in specs.items():ss[col],_,e=resolve(k,inc,exc,p,'periodo',col,catalog,resolved);status[k]=e
 periods=sorted(set.intersection(*(set(v) for v in ss.values())))
 write(p,[{'periodo':x,**{c:ss[c][x] for c in ss}} for x in periods if x>=START],['periodo']+list(specs))
 # Vivienda vs edificación: variación anual publicada por ENEC.
 p=ROOT/'enec_vivienda_yoy.csv'
 specs={'vivienda_yoy_pct':('enec_vivienda_yoy',['variacion porcentual anual','vivienda','construccion'],['entidad federativa']), 'edificacion_yoy_pct':('enec_edificacion_yoy',['variacion porcentual anual','edificacion','construccion'],['entidad federativa'])}
 ss={}
 for col,(k,inc,exc) in specs.items():ss[col],_,e=resolve(k,inc,exc,p,'periodo',col,catalog,resolved);status[k]=e
 periods=sorted(set.intersection(*(set(v) for v in ss.values())))
 write(p,[{'periodo':x,**{c:ss[c][x] for c in ss}} for x in periods if x>=START],['periodo']+list(specs))
 # Edificación: variación mensual real publicada.
 p=ROOT/'enec_edificacion_variacion_mensual.csv';s,_,e=resolve('enec_edificacion_mm',['variacion porcentual mensual','edificacion','valor de produccion'],['entidad federativa'],p,'periodo','variacion_mensual_real',catalog,resolved);status['enec_edificacion_mm']=e
 write(p,[{'periodo':x,'variacion_mensual_real':s[x]} for x in sorted(s) if x>=START],['periodo','variacion_mensual_real'])
 RES.write_text(json.dumps(resolved,ensure_ascii=False,indent=2),encoding='utf-8')
 (ROOT/'remaining_inegi_update_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
if __name__=='__main__':main()
