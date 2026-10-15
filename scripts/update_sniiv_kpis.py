#!/usr/bin/env python3
"""Actualiza KPIs de SNIIV que antes estaban fijos en el dashboard.

- Inventario activo RUV: total del último corte mensual disponible.
- Financiamientos: acciones acumuladas del año al último mes disponible.

El archivo estable sniiv_kpis.csv es consumido por data-loader.js. Si la API
cambia de estructura, el script falla sin sobrescribir el último archivo válido.
"""
import csv, json, re, urllib.request
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'sniiv_kpis.csv'; STATUS=ROOT/'sniiv_kpis_update_status.json'
BASE='https://sniiv.sedatu.gob.mx/api/CuboAPI'; UA='Mozilla/5.0 (compatible; Infonavit-dashboard/4.0)'

def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=120) as r:return json.load(r)

def get_text(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read().decode('utf-8','ignore')

def cutoff(page):
    txt=re.sub(r'<[^>]+>',' ',get_text(page)); txt=re.sub(r'\s+',' ',txt)
    months={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
    m=re.search(r'Al\s+(\d{1,2})\s+de\s+('+'|'.join(months)+r')\s+de\s+(20\d{2})',txt,re.I)
    if not m: raise RuntimeError('No se pudo identificar el corte en '+page)
    return int(m.group(3)),months[m.group(2).lower()],int(m.group(1))

def total(rows,field):
    s=0.0;n=0
    for r in rows:
        try:v=float(str(r.get(field,0) or 0).replace(',',''))
        except:continue
        s+=v;n+=1
    if n==0:raise RuntimeError(f'API sin campo {field}')
    return s

def main():
    iy,im,id_=cutoff('https://sniiv.sedatu.gob.mx/Cubo/Inventario')
    fy,fm,fd=cutoff('https://sniiv.sedatu.gob.mx/Cubo/Financiamiento')
    inv=get_json(f'{BASE}/GetInventario/{iy},{im}/00/000/estado')
    inv_total=total(inv,'viviendas')
    fin=get_json(f'{BASE}/GetFinanciamiento/{fy},{fy}/00/000/mes')
    # GetFinanciamiento devuelve acciones mensuales. Suma sólo meses hasta el corte visible.
    actions=0.0; used=0
    for r in fin:
        mv=r.get('mes')
        mnum=None
        try:mnum=int(float(mv))
        except:
            names={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}
            mnum=names.get(str(mv or '').strip().lower())
        if mnum is not None and mnum>fm:continue
        try:actions+=float(str(r.get('acciones',0) or 0).replace(',',''));used+=1
        except:pass
    if inv_total<10000 or actions<10000 or used==0:raise RuntimeError(f'Agregados SNIIV implausibles: inventario={inv_total}, financiamientos={actions}')
    rows=[
      {'indicador':'ruv_inventory','valor':round(inv_total),'periodo':f'{iy:04d}-{im:02d}-{id_:02d}','fuente':'SEDATU / SNIIV · Inventario de vivienda'},
      {'indicador':'financing_total','valor':round(actions),'periodo':f'{fy:04d}-{fm:02d}-{fd:02d}','fuente':'SEDATU / SNIIV · Financiamientos'}]
    tmp=OUT.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['indicador','valor','periodo','fuente']);w.writeheader();w.writerows(rows)
    tmp.replace(OUT)
    STATUS.write_text(json.dumps({'status':'ok','updated_at':datetime.now().isoformat(timespec='seconds'),'rows':rows},ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
