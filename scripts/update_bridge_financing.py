#!/usr/bin/env python3
"""Actualiza la tasa de crédito puente de banca comercial desde CNBV.

Fuente primaria: libro de Series Históricas de Banca Múltiple (SH_BM.xlsm),
publicado por CNBV en Portafolio de Información. Se escanean hojas/filas buscando
la serie etiquetada como crédito puente para construcción de vivienda y tasa de
interés. El algoritmo es conservador: si no reconoce estructura y fechas con
seguridad, conserva el CSV actual.
"""
import csv, io, json, re, sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'bridge_financing_anual.csv'
STATUS=ROOT/'bridge_financing_update_status.json'
URL='https://portafolioinfo.cnbv.gob.mx/_layouts/15/download.aspx?SourceUrl=https://portafolioinfo.cnbv.gob.mx/PortafolioInformacion/SH_BM.xlsm'
UA='Mozilla/5.0 (compatible; Infonavit-dashboard/1.0)'
START=2016

def download():
    with urlopen(Request(URL,headers={'User-Agent':UA}),timeout=120) as r:return r.read(),r.geturl()

def n(v):
    try:return float(str(v).replace('%','').replace(',','').strip())
    except:return None

def parse_date(v):
    if hasattr(v,'year') and hasattr(v,'month'): return int(v.year),int(v.month)
    s=str(v or '').strip().lower()
    m=re.search(r'(20\d{2})[-/ ]?(0?[1-9]|1[0-2])$',s)
    if m:return int(m.group(1)),int(m.group(2))
    months={'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
    y=re.search(r'20\d{2}',s)
    if y:
        for k,mo in months.items():
            if k in s:return int(y.group()),mo
    return None

def extract(blob):
    import openpyxl
    wb=openpyxl.load_workbook(io.BytesIO(blob),data_only=True,read_only=True,keep_vba=True)
    monthly={}
    debug=[]
    for ws in wb.worksheets:
        rows=list(ws.iter_rows(values_only=True))
        for i,row in enumerate(rows):
            label=' '.join(str(x or '') for x in row[:15]).lower()
            if 'puente' not in label: continue
            # require construction/housing context and a rate concept on row or nearby rows
            vicinity=' '.join(' '.join(str(x or '') for x in rows[j][:15]).lower() for j in range(max(0,i-3),min(len(rows),i+4)))
            if not any(k in vicinity for k in ('tasa','interés','interes')): continue
            debug.append((ws.title,i+1,label[:180]))
            # Search nearby row that explicitly has tasa + puente, else current row.
            candidates=[]
            for j in range(max(0,i-3),min(len(rows),i+4)):
                txt=' '.join(str(x or '') for x in rows[j][:15]).lower()
                if 'tasa' in txt and ('puente' in txt or 'construcción de vivienda' in vicinity or 'construccion de vivienda' in vicinity): candidates.append((j,rows[j]))
            if not candidates: candidates=[(i,row)]
            # Find a header row above with many dates and map to values.
            for j,data_row in candidates:
                for h in range(max(0,j-12),j+1):
                    dates=[parse_date(x) for x in rows[h]]
                    if sum(bool(x) for x in dates)<6: continue
                    for col,d in enumerate(dates):
                        if d and col<len(data_row):
                            val=n(data_row[col])
                            if val is not None and 0<val<50: monthly[d]=val
    if not monthly:
        raise RuntimeError('CNBV: no se pudo identificar automáticamente la fila de tasa de crédito puente en SH_BM.xlsm.')
    # El dashboard usa cierre de diciembre; para año corriente usa último mes disponible.
    annual={}
    years=sorted({y for y,m in monthly if y>=START})
    for y in years:
        choices=sorted((m,v) for (yy,m),v in monthly.items() if yy==y)
        if choices:
            dec=[v for m,v in choices if m==12]
            annual[y]=dec[-1] if dec else choices[-1][1]
    return annual,debug

def old():
    d={}
    if OUT.exists():
        with OUT.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                try:d[int(r['anio'])]=float(r['tasa_credito_puente_pct'])
                except:pass
    return d

def validate(new,prior):
    if len(new)<5: raise RuntimeError('CNBV: menos de 5 años reconocidos.')
    dif=[abs(new[y]-prior[y]) for y in new if y in prior]
    if dif and sum(x>3 for x in dif)>max(2,len(dif)//2): raise RuntimeError('CNBV: la serie candidata difiere demasiado del histórico; no se sobrescribe.')

def main():
    blob,final=download(); new,dbg=extract(blob); prior=old(); validate(new,prior)
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f);w.writerow(['anio','tasa_credito_puente_pct','fuente'])
        for y in sorted(new):w.writerow([y,f'{new[y]:.4f}'.rstrip('0').rstrip('.'),'CNBV · Series Históricas Banca Múltiple'])
    STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'status':'ok','source_url':final,'latest_year':max(new),'rows':len(new),'matches':dbg[:10]},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Crédito puente actualizado: {min(new)}-{max(new)}')
if __name__=='__main__':
    try:main()
    except Exception as e:
        STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'status':'error','error':str(e),'source_url':URL},ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'ERROR crédito puente: {e}',file=sys.stderr);sys.exit(1)
