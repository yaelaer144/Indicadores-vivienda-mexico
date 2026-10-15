#!/usr/bin/env python3
"""Actualiza ENOE trimestral desde Banco de Indicadores INEGI, validando contra la serie histórica local."""
import csv,json,os,re,statistics,unicodedata,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOKEN=os.environ.get('INEGI_API_TOKEN','').strip().strip('\"').strip("'");UA='dashboard-vivienda-infonavit/3.0'
API='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{id}/es/00/false/BISE/2.0/{token}?type=json';CAT='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/CL_INDICATOR/null/es/BIE-BISE/2.0/{token}?type=json';RES=ROOT/'inegi_resolved_ids.json';OUT=ROOT/'enoe_construccion_trimestral.csv'
def norm(s):return re.sub(r'[^a-z0-9]+',' ',unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()).strip()
def getj(u):return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':UA}),timeout=120))
def qperiod(p):
 s=str(p).strip();m=re.match(r'^((?:19|20)\d{2})[-/]?[TQ]?0?([1-4])$',s,re.I)
 return f'{m.group(1)}-T{int(m.group(2))}' if m else None
def api(i):
 d=getj(API.format(id=i,token=TOKEN));s=(d.get('Series') or [])[0];o={}
 for x in s.get('OBSERVATIONS') or []:
  p=qperiod(x.get('TIME_PERIOD'))
  try:v=float(str(x.get('OBS_VALUE')).replace(',',''))
  except:continue
  if p:o[p]=v
 return o,s.get('INDICADOR') or ''
def rows():
 with OUT.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def n(x):
 try:return float(str(x).replace(',',''))
 except:return None
def overlap(s,old,col,scale=1):
 es=[]
 for r in old:
  a=n(r.get(col));b=s.get(r.get('periodo'))
  if a and b is not None:es.append(abs((b/scale)-a)/abs(a))
 return statistics.median(es) if len(es)>=4 else None
def resolve(key,includes,excludes,col,catalog,resolved):
 old=rows();c=[]
 if os.getenv('INEGI_ID_'+key.upper()):c.append(os.getenv('INEGI_ID_'+key.upper()))
 if key in resolved:c.append(str(resolved[key]))
 sc=[]
 for x in catalog:
  d=x.get('Description','');z=norm(d)
  if any(norm(e) in z for e in excludes):continue
  s=sum(10 for i in includes if norm(i) in z)
  if s and x.get('value'):sc.append((s,str(x['value']),d))
 sc.sort(reverse=True);c += [i for _,i,_ in sc[:20]];c=list(dict.fromkeys(c));best=None
 for i in c:
  try:s,d=api(i)
  except:continue
  for scale in (1,1000):
   e=overlap(s,old,col,scale)
   if e is not None and (best is None or e<best[0]):best=(e,i,s,scale,d)
 if best is None or best[0]>0.04:raise RuntimeError(f'{key}: no se validó indicador ENOE; error={None if best is None else best[0]}')
 resolved[key]=best[1];return {p:v/best[3] for p,v in best[2].items()},best[0]
def main():
 if not TOKEN:raise SystemExit('Falta INEGI_API_TOKEN')
 catalog=getj(CAT.format(token=TOKEN)).get('CODE') or []
 try:resolved=json.loads(RES.read_text(encoding='utf-8'))
 except:resolved={}
 cons,e1=resolve('enoe_construccion',['poblacion ocupada','construccion'],['porcentaje','tasa','entidad federativa'],'total',catalog,resolved)
 tot,e2=resolve('enoe_ocupada_total',['poblacion ocupada','total nacional'],['porcentaje','tasa','construccion','entidad federativa'],'ocupada_total',catalog,resolved)
 ps=sorted(set(cons)&set(tot));out=[{'periodo':p,'total':cons[p],'ocupada_total':tot[p],'formal':'','informal':''} for p in ps if p>='2016-T1']
 if len(out)<20:raise SystemExit('Serie ENOE resultante demasiado corta; no se sobrescribe')
 tmp=OUT.with_suffix('.csv.tmp')
 with tmp.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=['periodo','total','ocupada_total','formal','informal']);w.writeheader();w.writerows(out)
 tmp.replace(OUT);RES.write_text(json.dumps(resolved,ensure_ascii=False,indent=2),encoding='utf-8');(ROOT/'enoe_update_status.json').write_text(json.dumps({'ultimo':out[-1]['periodo'],'error_construccion':e1,'error_total':e2},indent=2),encoding='utf-8')
if __name__=='__main__':main()

