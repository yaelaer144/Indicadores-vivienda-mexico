#!/usr/bin/env python3
"""Transforma el XLSX oficial del PIB trimestral (base 2018) en CSV para dashboard.

Uso: python scripts/update_pib_vab_trimestral.py --input PIBT_2.xlsx
Opcional: variable PIB_VAB_XLSX_URL con URL DIRECTA verificada al XLSX oficial.
No intenta automatizar una URL de página HTML ni inventa rutas de descarga.
"""
import argparse, csv, io, json, os, re, sys, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
CODES = {'23':'construccion', '236':'edificacion', '237':'ingenieria_civil', '238':'trabajos_especializados'}

def colnumber(ref):
    letters = re.match(r'[A-Z]+', ref).group()
    n = 0
    for ch in letters: n = n*26 + ord(ch)-64
    return n

def read_xlsx(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared = [''.join(e.text or '' for e in si.iter() if e.tag.endswith('}t')) for si in root]
        sheet = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        rows = {}
        for row in sheet.findall('.//x:sheetData/x:row', NS):
            cells = {}
            for c in row.findall('x:c', NS):
                v = c.find('x:v', NS)
                inline = c.find('x:is', NS)
                value = (v.text or '') if v is not None else (''.join(inline.itertext()) if inline is not None else '')
                if c.get('t') == 's' and value: value = shared[int(value)]
                cells[colnumber(c.attrib['r'])] = value
            rows[int(row.attrib['r'])] = cells
    return rows

def transform(rows, start_year):
    header = ' '.join(rows.get(i,{}).get(1,'') for i in (1,2,3))
    if 'a precios de 2018' not in header.lower() or 'series originales' not in header.lower():
        raise ValueError('Archivo incorrecto: se requiere Series Originales, millones de pesos anualizados a precios de 2018')
    ids = {}
    for r, cells in rows.items():
        if r > 100: break  # Primer bloque: niveles de VAB, no índices ni variaciones
        label = cells.get(1, '').strip()
        for code in CODES:
            if re.match(r'^'+code+r'\s*-\s*', label):
                if code in ids: raise ValueError(f'Código {code} duplicado')
                ids[code] = r
    if set(ids) != set(CODES): raise ValueError(f'Faltan códigos: {set(CODES)-set(ids)}')
    year = None
    periods = {}
    for col in sorted(rows[6]):
        maybe_year = rows.get(5,{}).get(col,'').strip()
        if re.match(r'^(19|20)\d{2}(?:\s|$)', maybe_year): year=int(maybe_year[:4])
        quarter = rows[6].get(col,'').strip().split(' ')[0]
        if year is not None and quarter in ('T1','T2','T3','T4') and year >= start_year:
            periods[(year,int(quarter[1]))] = col
    if not periods: raise ValueError('No se encontraron columnas trimestrales')
    points=[]
    for (year,q), col in sorted(periods.items()):
        values={}
        missing=[]
        for code,name in CODES.items():
            raw=rows[ids[code]].get(col,'').replace(',','').strip()
            if not raw or raw in ('N/D','ND','NA','-'): missing.append(code)
            else:
                try: values[name]=float(raw)
                except ValueError: raise ValueError(f'Dato inválido {year} T{q} {code}: {raw}')
        if len(missing)==len(CODES): continue
        if missing: raise ValueError(f'Trimestre incompleto {year} T{q}: {missing}')
        if min(values.values()) < 0: raise ValueError(f'Nivel negativo en {year} T{q}')
        difference = values['construccion'] - sum(values[x] for x in ('edificacion','ingenieria_civil','trabajos_especializados'))
        if abs(difference)>max(0.05,values['construccion']*0.001):
            raise ValueError(f'No cuadra sector contra subsectores en {year} T{q}: {difference}')
        points.append({'anio':year,'trimestre':q,'periodo':f'{year}-T{q}', 'mes_cierre':f'{year}-{q*3:02d}',**values})
    if len(points)<8: raise ValueError('Histórico insuficiente')
    observed={(p['anio'],p['trimestre']) for p in points}
    for idx,p in enumerate(points):
        if idx and (p['anio']*4+p['trimestre'] != points[idx-1]['anio']*4+points[idx-1]['trimestre']+1):
            raise ValueError(f'Discontinuidad temporal detectada en {p["periodo"]}')
        prev=next((x for x in points if (x['anio'],x['trimestre'])==(p['anio']-1,p['trimestre'])),None)
        for k in CODES.values():
            p[k+'_var_anual'] = round((p[k]/prev[k]-1)*100,6) if prev and prev[k] else ''
    return points

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,help='XLSX descargado previamente del INEGI')
    parser.add_argument('--output',type=Path,default=Path('pib_vab_construccion_trimestral.csv'))
    parser.add_argument('--status',type=Path,default=Path('pib_vab_update_status.json'))
    parser.add_argument('--start-year',type=int,default=2016)
    a=parser.parse_args()
    if a.input: data=a.input.read_bytes(); source=str(a.input)
    else:
        url=os.getenv('PIB_VAB_XLSX_URL','').strip()
        if not url: parser.error('Proporcione --input o configure PIB_VAB_XLSX_URL con una URL directa verificada al XLSX')
        if not url.lower().startswith('https://'): parser.error('La URL debe usar HTTPS')
        request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(request, timeout=45) as response: data=response.read(25_000_001)
        if len(data)>25_000_000: raise ValueError('Descarga demasiado grande')
        source=url
    points=transform(read_xlsx(data),a.start_year)
    fields=['periodo','anio','trimestre','mes_cierre']
    for k in CODES.values(): fields.extend((k,k+'_var_anual'))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(points)
    status={'fuente':'INEGI SCNM PIB Trimestral base 2018','serie':'Original','unidad':'millones de pesos anualizados a precios de 2018','origen':source,'primero':points[0]['periodo'],'ultimo':points[-1]['periodo'],'trimestres':len(points),'procesado_utc':datetime.now(timezone.utc).isoformat()}
    a.status.parent.mkdir(parents=True,exist_ok=True)
    a.status.write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PIB/VAB validado: {status["primero"]} a {status["ultimo"]}; {len(points)} trimestres')
    print('Último trimestre:',{k:points[-1][k] for k in CODES.values()})
if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'ERROR PIB/VAB: {e}',file=sys.stderr);sys.exit(1)
