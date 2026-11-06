#!/usr/bin/env python3
"""PVB nacional: vigilancia conservadora de comunicados oficiales.

Solo agrega cifras de alcance nacional verificables; nunca sustituye 'entregadas'
por 'asignadas', 'colocadas', cifras regionales o de una institución.
Vigila por separado la cohorte CONAVI-PVB en los comunicados oficiales.
No confunde reserva territorial general, metas ni totales nacionales con la cohorte reportada.
"""
import csv
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'pvb_avance.csv'
STATUS = ROOT / 'pvb_update_status.json'
SNIIV = ROOT / 'sniiv_kpis.csv'
SNIIV_FIELDS = ['indicador','valor','periodo','fuente']
CONAVI_METRICS = ('pvb_conavi_housing','pvb_conavi_hectares','pvb_conavi_predios')
CONAVI_SEED = 'https://www.gob.mx/presidencia/articulos/version-estenografica-conferencia-de-prensa-de-la-presidenta-claudia-sheinbaum-pardo-del-15-de-junio-de-2026'
FIELDS = ['etapa', 'viviendas', 'periodo', 'relacion', 'fuente', 'url']
SEED = [
 CONAVI_SEED,
 'https://www.gob.mx/presidencia/prensa/vivienda-para-el-bienestar-hay-274-mil-en-construccion-en-el-pais-el-programa-atiende-a-cerca-de-7-millones-de-personas-presidenta',
 'https://www.gob.mx/sedatu/prensa/el-programa-de-vivienda-para-el-bienestar-avanza-hay-667-mil-viviendas-contratadas-y-277-mil-en-proceso-de-obra-sedatu',
 'https://www.gob.mx/presidencia/prensa/vivienda-para-el-bienestar-beneficiara-a-12-millones-de-familias-en-el-sexenio-y-significa-cerca-de-1-2-del-pib-anual-presidenta',
]
MONTHS = {'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,
          'julio':7,'agosto':8,'septiembre':9,'setiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
REL = {
 'Contratadas':'Total nacional contratado; incluye etapas posteriores',
 'En construcción':'Total nacional en obra; subconjunto de contratadas',
 'Entregadas':'Total nacional explícitamente reportado como entregado; no equivale a asignadas o colocadas',
 'Meta sexenal':'Meta sexenal nacional de vivienda nueva del PVB',
}

class Blocks(HTMLParser):
 def __init__(self):
  super().__init__(); self.items=[]; self.current=[]; self.depth=0; self.ign=0
 def handle_starttag(self, tag, attrs):
  if tag in ('script','style','noscript'): self.ign+=1
  if tag in ('p','li','h1','h2','h3'):
   if self.depth==0: self.current=[]
   self.depth+=1
 def handle_endtag(self, tag):
  if tag in ('script','style','noscript'): self.ign=max(0,self.ign-1)
  if tag in ('p','li','h1','h2','h3') and self.depth:
   self.depth-=1
   if self.depth==0:
    value=re.sub(r'\s+',' ',html.unescape(' '.join(self.current))).strip()
    if value:self.items.append(value)
 def handle_data(self,data):
  if self.depth and not self.ign:self.current.append(data)


def request(url, timeout=18):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; IndicadoresViviendaPVB/1.0)'})
 with urllib.request.urlopen(req,timeout=timeout) as resp:
  return resp.read().decode('utf-8','replace'),resp.geturl()

def normalize(s):
 import unicodedata
 return ''.join(c for c in unicodedata.normalize('NFKD',s.lower()) if not unicodedata.combining(c))

def amount(value):
 m=re.fullmatch(r'\s*(\d[\d., ]*?)\s*(mil|millones?|millon)?\s*',normalize(value))
 if not m:return None
 number=float(m.group(1).replace(' ','').replace(',',''))
 factor=1000000 if (m.group(2) or '').startswith('millon') else 1000 if m.group(2)=='mil' else 1
 return int(round(number*factor))

NUM=r'(\d[\d., ]{0,18}?(?:\s+mil(?:lones?)?|\s+millones?|\s+millon)?)'
# Más seguro que permitir un número suelto ilimitado: número seguido opcionalmente de unidad.
N=r'(\d{1,3}\s+mil\s+\d{1,3}|\d{1,3}(?:[,.]\d{3})+|\d{4,7}|\d{1,3}(?:[.,]\d+)?)\s*(mil(?:lones)?|millones?|millon)?'

def parse_num(raw):
 m=re.fullmatch(r'\s*'+N+r'\s*',normalize(raw))
 if not m:return None
 first,unit=m.groups()
 compound=re.fullmatch(r'(\d{1,3})\s+mil\s+(\d{1,3})',first)
 if compound:return int(compound.group(1))*1000+int(compound.group(2))
 if unit in ('millon','millones','million'): multiplier=1000000
 elif unit=='mil': multiplier=1000
 else: multiplier=1
 if multiplier>1:
  value=float(first.replace(',','.')) if '.' not in first or ',' not in first else None
  # Dos separadores de miles significan que no es una expresión decimal con unidad.
 else:
  if re.fullmatch(r'\d{1,3}(?:[,.]\d{3})+',first):value=int(re.sub(r'[,.]','',first))
  else:value=float(first.replace(',','.'))
 return int(round(value*multiplier)) if value is not None else None

def publication_date(source):
 # La fecha editorial se valida en los metadatos o encabezado, no en la primera fecha citada del texto.
 for pattern in (r'\b(20\d{2})-(\d\d)-(\d\d)T',r'\b(20\d{2})-(\d\d)-(\d\d)\b'):
  m=re.search(pattern,source[:22000]);
  if m:
   try:return date(*map(int,m.groups())).isoformat()
   except ValueError:pass
 m=re.search(r'\b(\d{1,2})\s+de\s+('+ '|'.join(MONTHS)+r')\s+de\s+(20\d{2})',normalize(source[:25000]))
 if m:
  try:return date(int(m.group(3)),MONTHS[m.group(2)],int(m.group(1))).isoformat()
  except ValueError:pass
 return None

def extract(raw,url):
 parser=Blocks();parser.feed(raw)
 title=next((x for x in parser.items if 'vivienda' in normalize(x) and len(x)<350),'')
 if not ('vivienda para el bienestar' in normalize(title) or 'programa de vivienda para el bienestar' in normalize(raw[:30000])):return None
 pub=publication_date(raw)
 if not pub or pub>date.today().isoformat():return None
 # Exigimos un párrafo nacional con contratadas Y obra, de modo que no se mezclen
 # subtotales de Infonavit/Conavi/Fovissste o cifras municipales.
 alltext=' '.join(parser.items)
 norm=normalize(alltext)
 national_context=('en todo el pais','infonavit, conavi y fovissste','infonavit, conavi','del programa de vivienda para el bienestar','programa vivienda para el bienestar')
 pairs=[]
 for phrase in parser.items:
  t=normalize(phrase)
  for match in re.finditer(r'('+N+r')\s+viviendas\s+contratadas',t):
   rawnum=match.group(1); contracted=parse_num(rawnum)
   if contracted is None:continue
   # Fragmento corto: las dos cifras deben estar directamente relacionadas.
   context=t[max(0,match.start()-200):min(len(t),match.end()+380)]
   for c in re.finditer(r'('+N+r')\s+(?:viviendas\s+)?(?:en\s+proceso\s+de\s+obra|en\s+obra|en\s+construccion)',context):
    construction=parse_num(c.group(1))
    if construction and 100000<=contracted<=1800000 and 10000<=construction<=contracted:
     pairs.append((contracted,construction,phrase))
 # Casos con redacción '667 mil viviendas contratadas ... 277 mil en proceso de obra'
 if not pairs:
  for phrase in parser.items:
   t=normalize(phrase)
   a=re.search(r'('+N+r')\s+viviendas\s+contratadas',t)
   b=re.search(r'('+N+r')\s+(?:viviendas\s+)?(?:en\s+proceso\s+de\s+obra|en\s+obra|en\s+construccion)',t)
   if a and b:
    x,y=parse_num(a.group(1)),parse_num(b.group(1))
    if x and y and 100000<=x<=1800000 and 10000<=y<=x:pairs.append((x,y,phrase))
 if not pairs:return None
 # Sin contexto nacional de vivienda, un par de cifras puede ser institucional.
 valid=[]
 for x,y,p in pairs:
  context=normalize(p+' '+title)
  if any(word in context for word in national_context) or ('programa' in context and 'vivienda' in context):valid.append((x,y,p))
 if not valid:return None
 x,y,phrase=max(valid,key=lambda p:p[0])
 values={'Contratadas':x,'En construcción':y}
 # No se extrapolan entregas desde colocaciones o asignaciones.
 # Solo aceptamos una frase de total nacional explícito si aparece en el MISMO párrafo
 # que las cifras nacionales o en un resumen nacional que las contiene.
 t=normalize(phrase)
 delivered=re.search(r'(?:se han entregado\s+('+N+r')\s+viviendas|('+N+r')\s+viviendas\s+entregadas)',t)
 if delivered:
  z=parse_num(delivered.group(1) or delivered.group(3))
  if z is not None and 0<z<=x:values['Entregadas']=z
 return pub,values,url

def discover():
 urls=list(SEED)
 # Buscador de noticias solo para descubrir URLs: los datos SIEMPRE se leen en gob.mx.
 query='site:gob.mx/sedatu/prensa/ "viviendas contratadas" "obra" "Vivienda para el Bienestar"'
 rss='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'es-419','gl':'MX','ceid':'MX:es-419'})
 try:
  content,_=request(rss,12)
  feed=ET.fromstring(content)
  for item in feed.findall('./channel/item')[:35]:
   link=(item.findtext('link') or '').strip()
   if 'gob.mx/' in link:urls.append(link)
 except Exception:pass
 # Recorrido editorial; solo se siguen enlaces de sedatu/presidencia.
 for agency in ('sedatu','presidencia'):
  for page in (1,2):
   try:
    content,_=request(f'https://www.gob.mx/{agency}/prensa?page={page}',12)
    for href in re.findall(r'href=["\']([^"\']+)["\']',content):
     href=html.unescape(href)
     if href.startswith('/'):href='https://www.gob.mx'+href
     if re.match(r'^https://www\.gob\.mx/(?:sedatu|presidencia)/prensa/[^?#]+',href) and ('vivienda' in href or 'bienestar' in href):urls.append(href.split('?')[0])
   except Exception:pass
 return list(dict.fromkeys(urls))[:35]

def extract_conavi_cohort(raw, url):
    """Identifica SOLO la cohorte anual CONAVI con viviendas, hectáreas y predios.

    No acepta reservas acumuladas ni metas. Requiere las tres cifras en un
    mismo fragmento y una referencia explícita a la cohorte del año.
    """
    parser = Blocks(); parser.feed(raw)
    plain = normalize(' '.join(parser.items))
    pub = publication_date(raw)
    if not pub or pub > date.today().isoformat():
        return None
    if 'conavi' not in plain or 'vivienda' not in plain:
        return None

    # Preferimos la sección de rendición de cuentas de CONAVI, no el resto
    # de la conferencia (donde hay totales de INFONAVIT y SEDATU).
    marker = re.search(r'director general de la comision nacional de vivienda', plain)
    if marker:
        plain = plain[marker.start():]

    for match in re.finditer(r'(?:otros?|nuevos?|suman|sumamos)\s+('+N+r')\s+predios', plain):
        predios = parse_num(match.group(1))
        after = plain[match.end():match.end()+220]
        hm = re.search(r'(?:para\s+que\s+)?(?:suman?|sumen?|son|equivalentes?\s+a|de)\s+('+N+r')\s+hectareas', after)
        vm = re.search(r'(?:que\s+)?(?:son|seran|para|sum(?:an|en)?)\s+('+N+r')\s+viviendas', after)
        if not (hm and vm):
            continue
        hectares = parse_num(hm.group(1))
        housing = parse_num(vm.group(1))
        before = plain[max(0, match.start()-500):match.start()]
        surrounding = plain[max(0,match.start()-500):match.end()+400]
        # Cohorte anual identificada, no el total de reserva acumulada.
        yearly = re.search(r'(?:para este periodo|en lo que va del|para el)\s+(20\d{2})', before)
        if not yearly:
            continue
        cohort_year = int(yearly.group(1))
        if cohort_year != int(pub[:4]):
            continue
        if any(x is None for x in (predios, hectares, housing)):
            continue
        if not (10 <= predios <= 2000 and 1 <= hectares <= 10000 and 1000 <= housing <= 500000):
            continue
        if not re.search(r'contrat|obra|proyectos?|trabajos preliminares', surrounding):
            continue
        return pub, {'pvb_conavi_housing':housing,
                     'pvb_conavi_hectares':hectares,
                     'pvb_conavi_predios':predios}, url
    return None


def update_conavi_kpis(found):
    """Conserva métricas del SNIIV y escribe la última cohorte CONAVI validada."""
    existing = []
    if SNIIV.exists():
        with SNIIV.open(encoding='utf-8-sig', newline='') as f:
            existing = list(csv.DictReader(f))
    candidates = sorted(found, key=lambda x:x[0], reverse=True)
    latest = candidates[0] if candidates else None
    current = {r.get('indicador'):r for r in existing}
    current_dates = [r.get('periodo','') for r in existing if r.get('indicador') in CONAVI_METRICS]
    # Jamás reemplazar una publicación nueva por otra más antigua.
    if latest and (not current_dates or latest[0] > max(current_dates)):
        pub, vals, url = latest
        existing = [r for r in existing if r.get('indicador') not in CONAVI_METRICS]
        existing.extend({'indicador':metric, 'valor':value, 'periodo':pub,
                         'fuente':'CONAVI / Presidencia · '+url}
                        for metric, value in vals.items())
        temp=SNIIV.with_suffix('.csv.tmp')
        with temp.open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=SNIIV_FIELDS,extrasaction='ignore')
            writer.writeheader(); writer.writerows(existing)
        temp.replace(SNIIV)
        return {'estado':'actualizado','periodo':pub,'valores':vals,'fuente':url}
    if current_dates:
        return {'estado':'conservado_sin_cambio','periodo':max(current_dates),
                'nota':'No hay nueva cohorte CONAVI-PVB validada para las tres métricas.'}
    return {'estado':'pendiente_fuente_validada',
            'nota':'No se detectó la cohorte anual completa. No se alteraron valores de respaldo.'}


def main():
 existing=[]
 if OUT.exists():
  with OUT.open(encoding='utf-8-sig',newline='') as f:existing=list(csv.DictReader(f))
 seen={(r.get('periodo'),r.get('etapa')) for r in existing}
 found=[];conavi_found=[];errors=[]
 for url in discover():
  if not re.match(r'^https://www\.gob\.mx/(?:sedatu|presidencia)/',url):continue
  try:
   content,realurl=request(url)
   result=extract(content,realurl)
   if result:found.append(result)
   scoped=extract_conavi_cohort(content,realurl)
   if scoped:conavi_found.append(scoped)
  except Exception as ex:errors.append(f'{url[:110]}: {type(ex).__name__}')
 added=[]
 # Un periodo-etapa solo se registra cuando está validado; conservar cualquier histórico existente.
 # En casos de fuentes dobles para una misma fecha, prioridad al mayor alcance nacional.
 for pub,values,url in sorted(found,key=lambda v:v[0]):
  for stage,value in values.items():
   if (pub,stage) in seen:continue
   existing.append({'etapa':stage,'viviendas':value,'periodo':pub,'relacion':REL[stage],
                    'fuente':'SEDATU / Presidencia de la República','url':url})
   added.append({'periodo':pub,'etapa':stage,'viviendas':value})
   seen.add((pub,stage))
 if added:
  existing.sort(key=lambda r:(r['periodo'],r['etapa']))
  tmp=OUT.with_suffix('.csv.tmp')
  with tmp.open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(existing)
  tmp.replace(OUT)
 conavi_status=update_conavi_kpis(conavi_found)
 status={'conavi':conavi_status,'status':'actualizado' if added or conavi_status['estado']=='actualizado' else 'sin_novedades_verificables',
         'checked_at_utc':datetime.now(timezone.utc).isoformat(),
         'articulos_validados':len(found),'articulos_conavi_validados':len(conavi_found),'nuevas_filas':added,'errores_consulta':errors[:15],
         'ultimo_periodo':max((r.get('periodo','') for r in existing),default=None),
         'nota':'Solo cifras nacionales de contratadas y en obra verificadas juntas. No se equiparan asignadas, colocadas y entregadas.'}
 STATUS.write_text(json.dumps(status,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
