#!/usr/bin/env python3
"""Descarga ICC/INPP desde exportación CSV de INEGI y valida antes de publicar.

Modo normal: Playwright, sin token. Modo prueba:
python scripts/update_icc_inpp.py --icc-csv archivo.csv --inpp-csv archivo.csv
"""
import argparse
import csv
import io
import json
import math
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'julio 2025=100'
BASE_MONTH = '2025-07'
START = '2016-01'
URLS = {
 'icc': 'https://www.inegi.org.mx/app/indicesdepreciosv2/Estructura.aspx?idEstructura=1120019000100010',
 'inpp': 'https://www.inegi.org.mx/app/indicesdepreciosv2/Estructura.aspx?idEstructura=112001900050',
}
SPECS = {
 'icc': {
  'file': 'icc_incevis_base2025_mensual.csv',
  'columns': {'1660002':'general','1660003':'materiales','1660004':'maquinaria','1660005':'mano_obra'},
  'anchor': {'1660002':156.246, '1660003':157.178, '1660004':129.501, '1660005':152.941},
 },
 'inpp': {
  'file': 'inpp_construccion_edificacion_base2025_mensual.csv',
  'columns': {'1700226':'construccion','1700227':'edificacion','1700228':'edificacion_residencial','1700232':'edificacion_no_residencial'},
  'anchor': {'1700226':153.495,'1700227':154.904,'1700228':156.246,'1700232':152.507},
 },
}
# El CSV INPP incluye a veces un quinto componente no solicitado (236211).
MONTHS = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}


def norm(s):
 return unicodedata.normalize('NFKD', str(s)).encode('ascii','ignore').decode().lower().strip()


def month(s):
 x=norm(s)
 m=re.fullmatch(r'(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\s+(20\d{2})',x)
 if m:return f'{m.group(2)}-{MONTHS[m.group(1)]:02d}'
 m=re.fullmatch(r'(20\d{2})[-/](0?[1-9]|1[0-2])',x)
 if m:return f'{m.group(1)}-{int(m.group(2)):02d}'
 return None


def load_inegi_csv(path, kind):
 raw=Path(path).read_bytes()
 if len(raw)<200:raise ValueError(f'{kind}: descarga vacía o demasiado pequeña')
 for enc in ('utf-8-sig','cp1252','latin1'):
  try:lines=list(csv.reader(io.StringIO(raw.decode(enc)))) ;break
  except UnicodeError:continue
 else:raise ValueError(f'{kind}: codificación desconocida')
 header=next((i for i,row in enumerate(lines) if row and norm(row[0])=='fecha' and any(v.strip().isdigit() for v in row[1:])),None)
 if header is None:raise ValueError(f'{kind}: CSV no contiene fila Fecha con IDs de serie')
 ids=[v.strip() for v in lines[header][1:]]
 ids_needed=SPECS[kind]['columns']
 missing=set(ids_needed)-set(ids)
 if missing:raise ValueError(f'{kind}: faltan IDs {sorted(missing)}; exportación incorrecta')
 base_row=next((row for row in lines[:header] if row and norm(row[0])=='base'),None)
 if base_row is None or any('julio 2025=100' not in norm(base_row[ids.index(k)+1]).replace('base ','') for k in ids_needed):
  raise ValueError(f'{kind}: base distinta de julio 2025=100')
 pos={k:ids.index(k)+1 for k in ids_needed}
 data={}
 for row in lines[header+1:]:
  if not row:continue
  p=month(row[0])
  if not p or p<START:continue
  values={}
  for k, col in ids_needed.items():
   try:values[col]=float(row[pos[k]].strip().replace(',',''))
   except (ValueError,IndexError):raise ValueError(f'{kind}: dato inválido {p}/{col}')
   if not math.isfinite(values[col]) or not 20<=values[col]<=500:
    raise ValueError(f'{kind}: índice fuera de rango {p}/{col}={values[col]}')
  if p in data:raise ValueError(f'{kind}: mes duplicado {p}')
  data[p]=values
 if not data or min(data)>START or len(data)<120:
  raise ValueError(f'{kind}: cobertura insuficiente: {min(data) if data else "sin datos"}; n={len(data)}')
 periods=sorted(data)
 for a,b in zip(periods,periods[1:]):
  ay,am=map(int,a.split('-')); by,bm=map(int,b.split('-'))
  if by*12+bm-ay*12-am!=1:raise ValueError(f'{kind}: salto en histórico entre {a} y {b}')
 if BASE_MONTH not in data:raise ValueError(f'{kind}: falta julio de 2025 en la serie')
 # Nota: el CSV oficial rotula la base como julio 2025=100, pero los valores
 # exportados para julio 2025 no son 100. No forzamos un reescalamiento;
 # utilizamos las observaciones oficiales y una ancla de septiembre 2026.
 # Comparación de anclas recientes: evita publicar la serie equivocada.
 if '2026-09' in data:
  for k,expected in SPECS[kind]['anchor'].items():
   col=ids_needed[k]
   if abs(data['2026-09'][col]-expected)>0.5:
    raise ValueError(f'{kind}: discrepancia ancla septiembre 2026 en {col}')
 return data


def export_browser(kind, output):
 try:from playwright.sync_api import sync_playwright
 except ImportError as exc:raise RuntimeError('Falta playwright: pip install playwright && playwright install chromium') from exc
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  page=browser.new_page(accept_downloads=True,locale='es-MX',viewport={'width':1450,'height':1000})
  try:
   page.goto(URLS[kind],wait_until='domcontentloaded',timeout=90000)
   page.wait_for_timeout(2500)
   # Selección por filas legibles; nunca usar coordenadas absolutas.
   wanted=['Nacional','Materiales de construcción','Alquiler de maquinaria','Mano de obra'] if kind=='icc' else ['23 Construcción','236 Edificación','2361 Edificación residencial','2362 Edificación no residencial']
   # INEGI dibuja la jerarquía como tabla. Elegir por coincidencia de texto en cada fila.
   for label in wanted:
    candidates=page.locator('tr').filter(has_text=re.compile(r'^\s*[+−-]?\s*'+re.escape(label)+r'(?:\s|$)',re.I))
    if kind=='icc' and label=='Nacional':
     candidates=page.locator('tr').filter(has_text=re.compile(r'^\s*Nacional\s',re.I))
    if candidates.count()!=1:
     raise RuntimeError(f'{kind}: no se identificó una fila única para {label!r} ({candidates.count()}). Revisar estructura HTML')
    check=candidates.first.locator('input[type="checkbox"]').first
    if not check.count():raise RuntimeError(f'{kind}: sin casilla para {label}')
    if not check.is_checked():check.check(force=True)
   # Extraer CSV desde el control superior, no iconos de cada fila.
   controls=page.locator('a,button').filter(has_text=re.compile(r'^\s*CSV\s*$',re.I))
   if controls.count()<1:raise RuntimeError(f'{kind}: no se encontró control CSV')
   with page.expect_download(timeout=120000) as result:controls.first.click()
   result.value.save_as(str(output))
  finally:browser.close()


def build_rows(data, kind):
 columns=list(SPECS[kind]['columns'].values())
 rows=[]
 for p in sorted(data):
  r={'periodo':p}
  for col in columns:
   r[col]=format(data[p][col],'.12f').rstrip('0').rstrip('.')
  prev=f'{int(p[:4])-1}-{p[5:]}'
  for col in columns:
   r[col+'_yoy']=(format((data[p][col]/data[prev][col]-1)*100,'.9f') if prev in data else '')
  rows.append(r)
 return rows,['periodo']+columns+[c+'_yoy' for c in columns]


def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--icc-csv',type=Path,help='Solo para pruebas locales')
 ap.add_argument('--inpp-csv',type=Path,help='Solo para pruebas locales')
 args=ap.parse_args()
 if bool(args.icc_csv)!=bool(args.inpp_csv):ap.error('Ambos CSV deben especificarse juntos')
 with tempfile.TemporaryDirectory() as td:
  sources={}
  for kind in SPECS:
   supplied=getattr(args,kind+'_csv')
   path=supplied if supplied else Path(td)/(kind+'.csv')
   if not supplied:export_browser(kind,path)
   sources[kind]=load_inegi_csv(path,kind)
 # Validar coherencia cruzada: ICC general e INPP edificación residencial coinciden.
 icc,inpp=sources['icc'],sources['inpp']
 common=sorted(set(icc)&set(inpp))
 if len(common)<120:raise ValueError('Menos de 120 meses en común')
 if any(abs(icc[p]['general']-inpp[p]['edificacion_residencial'])>0.0001 for p in common):
  raise ValueError('ICC nacional e INPP residencial no coinciden: no se guardarán archivos')
 outputs={};status={'estado':'actualizado','fuente':'INEGI, índices de precios, base julio 2025=100','fecha_actualizacion_utc':datetime.now(timezone.utc).isoformat(),'series':{}}
 for kind,data in sources.items():
  filename=SPECS[kind]['file']
  rows,fields=build_rows(data,kind)
  with io.StringIO(newline='') as buff:
   writer=csv.DictWriter(buff,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(rows)
   outputs[filename]=buff.getvalue()
  status['series'][kind]={'mes_inicial':min(data),'mes_final':max(data),'meses':len(data),'columnas':list(SPECS[kind]['columns'].values())}
 # Conservar todos los archivos existentes hasta que se hayan validado ambas descargas.
 for filename,content in outputs.items():
  dest=ROOT/filename;temp=dest.with_suffix('.csv.tmp');temp.write_text(content,encoding='utf-8');temp.replace(dest)
 (ROOT/'icc_inpp_update_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(status,ensure_ascii=False,indent=2))


if __name__=='__main__':
 try:main()
 except Exception as exc:
  print(f'ICC/INPP: error, archivos existentes intactos: {exc}',file=sys.stderr)
  sys.exit(1)
