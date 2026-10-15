#!/usr/bin/env python3
import csv,re,html,urllib.request,json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'pvb_avance.csv';UA='dashboard-vivienda-infonavit/3.0'
LIST_URLS=[f'https://www.gob.mx/sedatu/prensa?page={i}' for i in range(1,7)]

def fetch(u):
 req=urllib.request.Request(u,headers={'User-Agent':UA});return urllib.request.urlopen(req,timeout=90).read().decode('utf-8','ignore')
def textify(s):return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',s))).strip()
def number(s):
 s=s.lower().replace(',','').strip();m=re.match(r'([0-9]+(?:\.[0-9]+)?)\s*(mil|millones?)?',s)
 if not m:return None
 v=float(m.group(1));unit=m.group(2) or ''
 if unit.startswith('mil'):v*=1000
 elif unit.startswith('millon'):v*=1000000
 return int(round(v))
def extract_date(t):
 months={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
 m=re.search(r'(\d{1,2})\s+de\s+('+'|'.join(months)+r')\s+de\s+(20\d{2})',t,re.I)
 if not m:return None
 return f'{int(m.group(3)):04d}-{months[m.group(2).lower()]:02d}-{int(m.group(1)):02d}'
def extract_article(url):
 raw=fetch(url);t=textify(raw)
 if 'Vivienda para el Bienestar' not in t and 'viviendas contratadas' not in t.lower():return None
 date=extract_date(t); vals={}
 pats={
  'Contratadas':[r'([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas\s+contratadas',r'hay\s+(?:ya\s+)?([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas\s+contratadas'],
  'En construcción':[r'([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas\s+(?:ya\s+)?(?:en\s+construcci[oó]n|en\s+obra)',r'hay\s+(?:ya\s+)?([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+(?:viviendas\s+)?en\s+obra'],
  'Entregadas':[r'([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas\s+entregadas',r'se\s+han\s+entregado\s+([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas'],
  'Meta sexenal':[r'meta(?:\s+sexenal)?(?:\s+que\s+es)?\s+de\s+(?:un\s+)?([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas',r'meta\s+de\s+([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas']}
 for k,ps in pats.items():
  for p in ps:
   m=re.search(p,t,re.I)
   if m:
    n=number(m.group(1))
    if n and n>1000:vals[k]=n;break
 if not date or len([k for k in ('Contratadas','En construcción') if k in vals])<2:return None
 return date,vals,url


def update_conavi_kpis(text,date):
 try:
  if 'conavi' not in text.lower(): return
  pats={
   'pvb_conavi_predios':[r'([0-9]{1,4})\s+predios'],
   'pvb_conavi_hectares':[r'([0-9][0-9.,]*)\s+hect[aá]reas'],
  }
  vals={}
  for k,ps in pats.items():
   for pat in ps:
    m=re.search(pat,text,re.I)
    if m:
     vals[k]=number(m.group(1));break
  # viviendas vinculadas a CONAVI: exige contexto cercano a CONAVI/predios para evitar usar el avance nacional.
  m=re.search(r'CONAVI.{0,700}?([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas',text,re.I|re.S)
  if not m:m=re.search(r'([0-9][0-9.,]*\s*(?:mil|millones?)?)\s+viviendas.{0,700}?CONAVI',text,re.I|re.S)
  if m: vals['pvb_conavi_housing']=number(m.group(1))
  if not vals:return
  kp=ROOT/'sniiv_kpis.csv'; rows=[]
  if kp.exists():
   with kp.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
  by={r.get('indicador'):r for r in rows if r.get('indicador')}
  for k,v in vals.items():
   if v and v>0:by[k]={'indicador':k,'valor':v,'periodo':date,'fuente':'SEDATU / CONAVI · comunicado PVB'}
  with kp.open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=['indicador','valor','periodo','fuente']);w.writeheader();w.writerows(by.values())
 except Exception:
  pass

def main():
 links=[]
 for u in LIST_URLS:
  try:r=fetch(u)
  except:continue
  for href in re.findall(r'href=["\']([^"\']+/sedatu/prensa/[^"\']+)["\']',r,re.I):
   if href.startswith('/'):href='https://www.gob.mx'+href
   if href.startswith('http'):links.append(href.split('?')[0])
 links=list(dict.fromkeys(links))[:120]
 found=[]
 for u in links:
  try:a=extract_article(u)
  except:continue
  if a:found.append(a)
 if not found:raise SystemExit('No se encontró un comunicado PVB con contratadas y en construcción; se conserva CSV anterior.')
 date,vals,url=max(found,key=lambda x:x[0])
 try: update_conavi_kpis(textify(fetch(url)),date)
 except Exception: pass
 existing=[]
 if OUT.exists():
  with OUT.open(encoding='utf-8-sig',newline='') as f:existing=list(csv.DictReader(f))
 if any(r.get('periodo')==date for r in existing):return
 rows=existing[:]
 src='SEDATU · Gobierno de México'
 rel={'Contratadas':'avance acumulado del PVB al corte; universo contratado','En construcción':'avance acumulado del PVB al corte; subconjunto en obra','Entregadas':'avance acumulado explícitamente reportado como entregado','Meta sexenal':'meta sexenal reportada en la fuente'}
 for k in ('Contratadas','En construcción','Entregadas','Meta sexenal'):
  if k in vals:rows.append({'etapa':k,'viviendas':vals[k],'periodo':date,'relacion':rel[k],'fuente':src,'url':url})
 tmp=OUT.with_suffix('.csv.tmp')
 with tmp.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['etapa','viviendas','periodo','relacion','fuente','url']);w.writeheader();w.writerows(rows)
 tmp.replace(OUT)
 (ROOT/'pvb_update_status.json').write_text(json.dumps({'ultimo_corte':date,'valores':vals,'url':url},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
