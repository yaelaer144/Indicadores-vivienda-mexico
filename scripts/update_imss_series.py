#!/usr/bin/env python3
"""Actualiza empleo y SBC de construcción a partir de Datos Abiertos IMSS / Asegurados.

Reglas oficiales usadas:
- sector_economico_1 = 4: Industria de la construcción.
- SBC diario = sum(masa_sal_ta) / sum(ta_sal).
- Puestos = sum(ta).

El script nunca reemplaza los CSV con una descarga vacía o inválida.
"""
import csv, io, json, re, sys, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from calendar import monthrange
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
UA='dashboard-vivienda-infonavit/2.0 (+GitHub Actions)'
OUT_CONS=ROOT/'imss_construccion_mensual.csv'
OUT_SBC=ROOT/'imss_sbc_construccion_mensual.csv'
OUT_TOTAL=ROOT/'imss_total_mensual.csv'
STATUS=ROOT/'imss_update_status.json'
START_PERIOD='2016-01'

BASES=[
  'https://datos.imss.gob.mx/sites/default/files/asg-{date}.csv',
  'https://www2.imss.gob.mx/sites/default/files/asg-{date}.csv',
]
DISCOVERY=[
  'https://datos.imss.gob.mx/group/asegurados',
  'https://datos.imss.gob.mx/dataset/asegurados',
]
API_DISCOVERY=[
  'https://datos.imss.gob.mx/api/3/action/package_search?q=asegurados',
  'https://datos.imss.gob.mx/api/3/action/package_search?q=asg',
  'https://datos.imss.gob.mx/api/1/metastore/query?fulltext=asegurados',
]

def get(url, timeout=90):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/csv,text/plain,text/html,*/*'})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read(), r.geturl(), r.headers.get('Content-Type','')

def month_iter(start_ym, end_ym):
    y,m=map(int,start_ym.split('-')); ey,em=map(int,end_ym.split('-'))
    while (y,m) <= (ey,em):
        yield y,m
        m += 1
        if m==13: y,m=y+1,1

def read_existing(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))

def existing_periods(path):
    return {r.get('periodo','') for r in read_existing(path) if re.match(r'^\d{4}-\d{2}$',r.get('periodo',''))}

def last_period(path, fallback='2023-06'):
    rows=read_existing(path)
    vals=sorted(r.get('periodo','') for r in rows if re.match(r'^\d{4}-\d{2}$',r.get('periodo','')))
    return vals[-1] if vals else fallback

def next_month(ym):
    y,m=map(int,ym.split('-')); m+=1
    if m==13:y,m=y+1,1
    return f'{y:04d}-{m:02d}'

def discovered_links():
    links=[]
    def add_from_text(txt):
        # URLs absolutas o hrefs relativos que contengan el patrón mensual ASG.
        pats = re.findall(r'https?://[^\s"\'<>]+',txt,re.I) + re.findall(r'href=["\']([^"\']+)["\']',txt,re.I)
        for href in pats:
            if not re.search(r'asg-\d{4}-\d{2}-\d{2}',href,re.I):
                continue
            if href.startswith('//'): href='https:'+href
            elif href.startswith('/'): href='https://datos.imss.gob.mx'+href
            elif not href.startswith('http'): href='https://datos.imss.gob.mx/'+href.lstrip('/')
            links.append(href.replace('&amp;','&').replace('\\/','/'))
    for page in DISCOVERY + API_DISCOVERY:
        try:
            b,final,ct=get(page,45); add_from_text(b.decode('utf-8','ignore'))
        except Exception:
            continue
    return list(dict.fromkeys(links))

def candidate_urls(y,m,links):
    d=f'{y:04d}-{m:02d}-{monthrange(y,m)[1]:02d}'
    out=[u for u in links if d in u]
    out += [x.format(date=d) for x in BASES]
    return list(dict.fromkeys(out))

def to_float(x):
    if x is None:return 0.0
    s=str(x).strip().replace(',','')
    if s in ('','NA','N/A','null','None'): return 0.0
    try:return float(s)
    except:return 0.0

def sniff_text(raw):
    for enc in ('utf-8-sig','latin-1','cp1252'):
        try:return raw.decode(enc)
        except UnicodeDecodeError: pass
    return raw.decode('utf-8','replace')

def aggregate(raw):
    txt=sniff_text(raw)
    sample=txt[:10000]
    delim='|' if sample.count('|') > sample.count(',') else ','
    rd=csv.DictReader(io.StringIO(txt),delimiter=delim)
    if not rd.fieldnames: raise ValueError('Archivo IMSS sin encabezados')
    names={str(x).strip().lower():x for x in rd.fieldnames}
    required=['sector_economico_1','ta','ta_sal','masa_sal_ta']
    miss=[x for x in required if x not in names]
    if miss: raise ValueError('Faltan columnas IMSS: '+', '.join(miss))
    cons_ta=cons_tasal=cons_mass=total_ta=0.0; n=0
    for r in rd:
        n+=1
        total_ta += to_float(r.get(names['ta']))
        sec=str(r.get(names['sector_economico_1'],'')).strip()
        try: secnorm=str(int(float(sec)))
        except: secnorm=sec
        if secnorm=='4':
            cons_ta += to_float(r.get(names['ta']))
            cons_tasal += to_float(r.get(names['ta_sal']))
            cons_mass += to_float(r.get(names['masa_sal_ta']))
    if n<10 or cons_ta<=1000 or cons_tasal<=0 or cons_mass<=0:
        raise ValueError(f'Agregado IMSS implausible: filas={n}, construcción={cons_ta}, ta_sal={cons_tasal}')
    sbc=cons_mass/cons_tasal
    if not (50 < sbc < 5000): raise ValueError(f'SBC implausible: {sbc}')
    return {'construction_thousands':cons_ta/1000.0,'total_thousands':total_ta/1000.0,'sbc':sbc,'rows':n}

def merge(path, period, row, fields):
    rows=read_existing(path)
    by={r.get('periodo'):r for r in rows if r.get('periodo')}
    by[period]=row
    vals=[by[k] for k in sorted(by)]
    tmp=path.with_suffix(path.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(vals)
    tmp.replace(path)

def fetch_period(y,m,links):
    period=f'{y:04d}-{m:02d}'; errors=[]
    for url in candidate_urls(y,m,links):
        try:
            raw,final,ct=get(url,35)
            if raw[:200].lower().find(b'<html')>=0: raise ValueError('respuesta HTML, no CSV')
            agg=aggregate(raw); return period,agg,final,errors
        except urllib.error.HTTPError as e:
            if e.code not in (403,404): errors.append(f'{url}: HTTP {e.code}')
        except Exception as e: errors.append(f'{url}: {e}')
    return period,None,None,errors

def main():
    links=discovered_links()
    existing_cons=existing_periods(OUT_CONS); existing_sbc=existing_periods(OUT_SBC); existing_total=existing_periods(OUT_TOTAL)
    today=date.today(); end=f'{today.year:04d}-{today.month:02d}'
    missing=[(y,m) for y,m in month_iter(START_PERIOD,end) if not (f'{y:04d}-{m:02d}' in existing_cons and f'{y:04d}-{m:02d}' in existing_sbc and f'{y:04d}-{m:02d}' in existing_total)]
    results=[]; found=[]
    # El backfill 2018-actualidad se descarga en paralelo para que la primera ejecución
    # en GitHub Actions no tarde horas. Escritura de archivos se mantiene secuencial.
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(fetch_period,y,m,links):(y,m) for y,m in missing}
        for fut in as_completed(futs):
            period,agg,url,errors=fut.result()
            if agg is None: results.append({'periodo':period,'status':'no_disponible','errors':errors[-2:]})
            else: found.append((period,agg,url))
    for period,agg,url in sorted(found):
        merge(OUT_CONS,period,{'periodo':period,'construccion':f"{agg['construction_thousands']:.3f}"},['periodo','construccion'])
        merge(OUT_SBC,period,{'periodo':period,'sbc_diario_pesos':f"{agg['sbc']:.2f}",'fuente':'IMSS · Datos Abiertos Asegurados'},['periodo','sbc_diario_pesos','fuente'])
        merge(OUT_TOTAL,period,{'periodo':period,'puestos_miles':f"{agg['total_thousands']:.3f}",'fuente':'IMSS · Datos Abiertos Asegurados','nota':'Total nacional; se mantiene separado de la serie sectorial de construcción.'},['periodo','puestos_miles','fuente','nota'])
        results.append({'periodo':period,'status':'actualizado','url':url,'filas':agg['rows'],'construccion_miles':round(agg['construction_thousands'],3),'sbc':round(agg['sbc'],2)})
    results.sort(key=lambda x:x['periodo'])
    status={'inicio_historico':START_PERIOD,'updated_by':'GitHub Actions / IMSS Datos Abiertos','regla_sector':'sector_economico_1 = 4','regla_sbc':'sum(masa_sal_ta) / sum(ta_sal)','meses_faltantes_al_inicio':len(missing),'resultados':results}
    STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
