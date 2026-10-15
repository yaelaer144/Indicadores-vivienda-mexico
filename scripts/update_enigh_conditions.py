#!/usr/bin/env python3
"""Actualiza automáticamente las visualizaciones ENIGH/CONAVI cuando aparece un nuevo levantamiento.
- Tenencia nacional y rural/urbana: microdatos VIVIENDAS de ENIGH (factor de expansión).
- Déficit cualitativo/materiales: último documento técnico CONAVI/SIESCO, con extracción validada.
Nunca elimina el histórico previo si no logra validar una fuente nueva.
"""
import csv,io,os,re,zipfile,urllib.request,json,html
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];UA='dashboard-vivienda-infonavit/3.0'

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':UA});return urllib.request.urlopen(req,timeout=180).read()
def n(x):
 try:return float(str(x).replace(',','').strip())
 except:return None
def weighted(rows,cond):return sum(float(r['factor'])*cond(r) for r in rows if n(r.get('factor')) is not None)
def enigh_zip(year):return f'https://www.inegi.org.mx/contenidos/programas/enigh/nc/{year}/microdatos/enigh{year}_ns_viviendas_csv.zip'
def load_viviendas(year):
 data=fetch(enigh_zip(year));z=zipfile.ZipFile(io.BytesIO(data));names=[x for x in z.namelist() if x.lower().endswith('.csv') and 'vivienda' in x.lower()]
 if not names:raise RuntimeError('ZIP ENIGH sin viviendas.csv')
 raw=z.read(names[0]);
 text=raw.decode('utf-8-sig','ignore');rows=list(csv.DictReader(io.StringIO(text)))
 needed={'tenencia','tam_loc','factor'}
 if not rows or not needed.issubset(set(rows[0])):raise RuntimeError(f'ENIGH {year}: faltan variables {needed-set(rows[0])}')
 return rows

def update_tenure():
 current=datetime.utcnow().year
 candidates=[y for y in range(current if current%2==0 else current-1,2015,-2)]
 year=None;rows=None
 for y in candidates:
  try:rows=load_viviendas(y);year=y;break
  except Exception:continue
 if year is None:raise RuntimeError('No se encontró microdato ENIGH VIVIENDAS reciente')
 total=sum(n(r.get('factor')) or 0 for r in rows)
 if total<=1e6:raise RuntimeError('Factor ENIGH inválido')
 # Códigos de tenencia ENIGH: 1 rentada, 2 prestada, 3 propia pagándose, 4 propia, 5 intestada/litigio, 6 otra.
 groups={'Propia totalmente pagada':{'4'},'Propia pagándose':{'3'},'Rentada':{'1'},'Otros':{'2','5','6'}}
 out=[]
 for label,codes in groups.items():
  v=sum((n(r.get('factor')) or 0) for r in rows if str(r.get('tenencia','')).strip() in codes);out.append({'anio':year,'categoria':label,'porcentaje':100*v/total,'viviendas':round(v),'definicion':'Estimación ponderada directa con microdatos VIVIENDAS ENIGH'})
 p=ROOT/f'tenencia_{year}.csv';
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=out[0]);w.writeheader();w.writerows(out)
 # mantener nombre estable consumido por el dashboard
 (ROOT/'tenencia_2024.csv').write_bytes(p.read_bytes())
 # Histórico: insertar/reemplazar último año
 hist=ROOT/'tenencia_historica.csv';old=[]
 if hist.exists():
  with hist.open(encoding='utf-8-sig',newline='') as f:old=list(csv.DictReader(f))
 m={r['categoria']:float(r['porcentaje']) for r in out};row={'anio':year,'propia_pagada_pct':m['Propia totalmente pagada'],'propia_pagandose_pct':m['Propia pagándose'],'rentada_pct':m['Rentada'],'otros_pct':m['Otros']}
 old=[r for r in old if str(r.get('anio'))!=str(year)]+[row];old.sort(key=lambda r:int(r['anio']))
 with hist.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=['anio','propia_pagada_pct','propia_pagandose_pct','rentada_pct','otros_pct']);w.writeheader();w.writerows(old)
 # rural/urbano
 area=[]
 for label,fn in [('Rural',lambda r:str(r.get('tam_loc','')).strip()=='4'),('Urbano',lambda r:str(r.get('tam_loc','')).strip() in {'1','2','3'})]:
  sub=[r for r in rows if fn(r)];den=sum(n(r.get('factor')) or 0 for r in sub);vals={}
  for lab,codes in groups.items():vals[lab]=100*sum((n(r.get('factor')) or 0) for r in sub if str(r.get('tenencia','')).strip() in codes)/den
  area.append({'ambito':label,'propia':vals['Propia totalmente pagada'],'pagandose':vals['Propia pagándose'],'rentada':vals['Rentada'],'otros':vals['Otros'],'nota':f'Cálculo directo ponderado con ENIGH {year}; factor de expansión.'})
 with (ROOT/'tenencia_rural_urbano_2024.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=area[0]);w.writeheader();w.writerows(area)
 return year

def update_conavi_deficit():
 # Intenta localizar el documento más reciente desde SIESCO. Requiere pypdf instalado por el workflow.
 try:
  from pypdf import PdfReader
 except Exception as e:raise RuntimeError('Falta pypdf') from e
 page=fetch('https://siesco.conavi.gob.mx/Siesco/Documentos').decode('utf-8','ignore')
 links=[]
 for h in re.findall(r'href=["\']([^"\']+\.pdf[^"\']*)',page,re.I):
  u=html.unescape(h)
  if 'deficit' in u.lower() and 'cualit' in u.lower():
   if u.startswith('/'):u='https://siesco.conavi.gob.mx'+u
   elif not u.startswith('http'):u='https://siesco.conavi.gob.mx/Siesco/'+u.lstrip('/')
   links.append(u)
 if not links:return None
 # prueba los primeros enlaces, normalmente ordenados de más reciente a más antiguo
 for u in links[:8]:
  try:
   pdf=fetch(u);reader=PdfReader(io.BytesIO(pdf));txt='\n'.join((p.extract_text() or '') for p in reader.pages)
  except Exception:continue
  ym=re.search(r'(20(?:2[4-9]|3\d))',txt);year=int(ym.group(1)) if ym else None
  pats={
   'materiales_muros_inadecuados_pct':r'Paredes\s+inadecuadas[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'materiales_techos_inadecuados_pct':r'Techos\s+inadecuados[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'materiales_pisos_inadecuados_pct':r'Piso(?:s)?\s+inadecuado(?:s)?[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'deficit_materiales_pct':r'Materiales\s+inadecuados[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'deficit_espacios_pct':r'Espacios\s+inadecuados[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'deficit_servicios_pct':r'Servicios\s+inadecuados[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%',
   'deficit_cualitativo_pct':r'D[ée]ficit\s+cualitativo[^\n%]*?([0-9]+(?:\.[0-9]+)?)\s*%'}
  vals={}
  for k,p in pats.items():
   m=re.search(p,txt,re.I);vals[k]=float(m.group(1)) if m else None
  vm=re.search(r'(?:total\s+de\s+)?([0-9]{1,3}(?:[, ]\d{3}){2,})\s+viviendas\s+en\s+d[ée]ficit\s+cualitativo',txt,re.I)
  if vm:vals['deficit_cualitativo_viviendas']=int(re.sub(r'[, ]','',vm.group(1)))
  if sum(v is not None for v in vals.values())<6:continue
  old={}
  p=ROOT/'condiciones_resumen_2024.csv'
  if p.exists():
   with p.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):old[r['indicador']]=r
  for k,v in vals.items():
   if v is not None:old[k]={'anio':year or '', 'indicador':k,'valor':v,'unidad':'viviendas' if k.endswith('_viviendas') else '%','fuente':f'CONAVI · déficit cualitativo {year or "último"}'}
  with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=['anio','indicador','valor','unidad','fuente']);w.writeheader();w.writerows(old.values())
  return year
 return None

def update_poverty_carencias():
    """Actualiza histórico de carencias desde la presentación oficial de Pobreza multidimensional de INEGI."""
    try:
      from pypdf import PdfReader
    except Exception as e: raise RuntimeError('Falta pypdf') from e
    current=datetime.utcnow().year
    candidates=[y for y in range(current if current%2==0 else current-1,2015,-2)]
    for y in candidates:
      url=f'https://www.inegi.org.mx/contenidos/desarrollosocial/pm/doc/pm_presentacion_{y}.pdf'
      try:
        reader=PdfReader(io.BytesIO(fetch(url))); txt='\n'.join((p.extract_text() or '') for p in reader.pages)
      except Exception: continue
      # Localiza la tabla nacional; se esperan años pares consecutivos desde 2016.
      def vals_after(label):
        m=re.search(label+r'.{0,900}',txt,re.I|re.S)
        if not m:return []
        nums=[float(x) for x in re.findall(r'(?<!\d)(\d{1,2}\.\d)(?!\d)',m.group(0))]
        # filtra porcentajes plausibles y quita repeticiones inmediatas generadas por columnas de millones/carencias
        return [v for v in nums if 0<=v<=100]
      q=vals_after(r'Carencia por calidad y espacios de la vivienda')
      b=vals_after(r'Carencia por acceso a los servicios b[aá]sicos en la vivienda')
      years=list(range(2016,y+1,2))
      # En la presentación la primera secuencia corresponde a porcentajes por año.
      if len(q)<len(years) or len(b)<len(years):continue
      q=q[:len(years)];b=b[:len(years)]
      # validación contra 2024 conocida cuando esté presente, evita tomar columnas equivocadas.
      if 2024 in years:
        i=years.index(2024)
        if not (abs(q[i]-7.9)<1.0 and abs(b[i]-14.1)<1.0):continue
      out=[{'anio':yr,'carencia_calidad_espacios_pct':q[i],'carencia_servicios_basicos_pct':b[i]} for i,yr in enumerate(years)]
      pp=ROOT/'condiciones_historicas.csv'
      with pp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['anio','carencia_calidad_espacios_pct','carencia_servicios_basicos_pct']);w.writeheader();w.writerows(out)
      return y
    raise RuntimeError('No se validó presentación INEGI de pobreza multidimensional')

def main():
 status={}
 try:status['enigh_tenencia_year']=update_tenure()
 except Exception as e:status['enigh_error']=str(e)
 try:status['conavi_deficit_year']=update_conavi_deficit()
 except Exception as e:status['conavi_error']=str(e)
 try:status['pobreza_carencias_year']=update_poverty_carencias()
 except Exception as e:status['pobreza_carencias_error']=str(e)
 (ROOT/'conditions_update_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
 if len(status)==2 and all(k.endswith('error') for k in status):raise SystemExit(str(status))
if __name__=='__main__':main()
