#!/usr/bin/env python3
"""Transforma descargas CSV oficiales del IGAE e IMAI a series originales mensuales.
Uso: python prepare_igae_imai.py IGAE_2.csv IMAI_2.csv [carpeta_salida]
No descarga automáticamente desde INEGI; requiere los CSV originales.
"""
import csv, re, sys, json
from pathlib import Path
from datetime import datetime, timezone
MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
NAMES={'construction':'23 - Construcción','edificacion':'236 - Edificación','obra_civil':'237 - Construcción de obras de ingeniería civil','trabajos_especializados':'238 - Trabajos especializados para la construcción'}
def parse(path,names):
 with open(path,encoding='utf-8-sig',newline='') as f:
  reader=csv.reader(f);heads=next(reader);rows=list(reader)
 assert rows and rows[0][0].strip()=='Índice de volumen físico, base 2018=100', 'No se encontró bloque de niveles originales base 2018'
 end=next((i for i,r in enumerate(rows) if i and r[0].startswith('Variación porcentual anual')),len(rows))
 section=rows[:end]; out={}
 for field,label in names.items():
  matches=[r for r in section if r and r[0].strip()==label]
  if len(matches)!=1:raise ValueError(f'{path}: indicador {label}: coincidencias={len(matches)}')
  series={}
  for col,raw in zip(heads[1:],matches[0][1:]):
   m=re.match(r'^(\d{4})\s*\|\s*([A-Za-záéíóúÁÉÍÓÚ]+)',col.strip())
   if not m or m.group(2).lower() not in MONTHS:continue
   date=f'{m.group(1)}-{MONTHS[m.group(2).lower()]:02d}'
   if date<'2016-01':continue
   try:v=float(raw.replace(',','').strip())
   except (ValueError,AttributeError):continue
   if v<=0:raise ValueError(f'Índice no positivo: {field} {date}')
   series[date]=v
  if len(series)<90:raise ValueError(f'Serie corta: {field}: {len(series)} meses')
  out[field]=series
 return out
def write(path,records,fields):
 with open(path,'w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(records)
def calculate(series):
 rows=[]
 for p,v in sorted(series.items()):
  y,month=map(int,p.split('-'));prev=series.get(f'{y-1:04d}-{month:02d}')
  rows.append({'periodo':p,'indice':round(v,9),'variacion_mensual':round((v/series[f'{y:04d}-{month-1:02d}']-1)*100,8) if month>1 and f'{y:04d}-{month-1:02d}' in series else (round((v/series[f'{y-1:04d}-12']-1)*100,8) if month==1 and f'{y-1:04d}-12' in series else ''),'variacion_anual':round((v/prev-1)*100,8) if prev else ''})
 return rows
def main():
 a=Path(sys.argv[1]) if len(sys.argv)>1 else Path('IGAE_2.csv');b=Path(sys.argv[2]) if len(sys.argv)>2 else Path('IMAI_2.csv');dest=Path(sys.argv[3]) if len(sys.argv)>3 else Path('.');dest.mkdir(parents=True,exist_ok=True)
 igae=parse(a,{'construction':NAMES['construction']});imai=parse(b,NAMES)
 overlap=sorted(set(igae['construction'])&set(imai['construction']));diffs=[abs(igae['construction'][p]-imai['construction'][p]) for p in overlap];maxdiff=max(diffs) if diffs else None
 if not overlap:raise ValueError('Sin periodos comunes entre IGAE e IMAI')
 write(dest/'igae_construccion_mensual.csv',calculate(igae['construction']),['periodo','indice','variacion_mensual','variacion_anual'])
 write(dest/'imai_construccion_mensual.csv',calculate(imai['construction']),['periodo','indice','variacion_mensual','variacion_anual'])
 detail=[]
 for p in sorted(set().union(*(set(s) for s in imai.values()))):
  r={'periodo':p}
  for k,s in imai.items():
   v=s.get(p);r[k]=round(v,9) if v is not None else ''
   prev=s.get(f'{int(p[:4])-1}{p[4:]}');r[k+'_yoy']=round((v/prev-1)*100,8) if v is not None and prev else ''
  detail.append(r)
 write(dest/'imai_construccion_subsectores_mensual.csv',detail,['periodo']+list(imai)+[k+'_yoy' for k in imai])
 status={'fuente':'INEGI tabulados oficiales CSV proporcionados por usuario','tipo':'series originales; índices de volumen físico base 2018=100','igae_construccion':{'primer_periodo':min(igae['construction']),'ultimo_periodo':max(igae['construction']),'observaciones':len(igae['construction'])},'imai_construccion':{'primer_periodo':min(imai['construction']),'ultimo_periodo':max(imai['construction']),'observaciones':len(imai['construction'])},'comparacion':{'periodos_comunes':len(overlap),'maxima_diferencia_absoluta':maxdiff,'coincidencia_exacta':maxdiff<=1e-6,'periodos_con_diferencias':sum(d>1e-6 for d in diffs)},'subsectores':{k:{'observaciones':len(s),'ultimo':max(s)} for k,s in imai.items()},'automatizacion_descarga':'pendiente: falta URL programable validada o IDs de API'}
 (dest/'diagnostico_igae_imai.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(status,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
