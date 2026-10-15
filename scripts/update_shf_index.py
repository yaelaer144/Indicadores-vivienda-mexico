#!/usr/bin/env python3
"""Actualiza Índice SHF desde el archivo oficial de datos abiertos.

Busca automáticamente el enlace más reciente en gob.mx y extrae la serie nacional
trimestral. Si SHF modifica el formato y no se puede reconocer con seguridad, no
sobrescribe el CSV vigente.
"""
import csv, io, json, re, sys, tempfile, zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'shf_indice_trimestral.csv'
OUT_STATE=ROOT/'shf_precios_entidad.csv'
OUT_LEVEL=ROOT/'shf_indice_nivel_trimestral.csv'
STATUS=ROOT/'shf_update_status.json'
PAGE='https://www.gob.mx/shf/documentos/indice-shf-de-precios-de-la-vivienda-en-mexico-2025-a-2026'
UA='Mozilla/5.0 (compatible; Infonavit-dashboard/1.0)'

def fetch(url):
    req=Request(url,headers={'User-Agent':UA,'Accept':'*/*'})
    with urlopen(req,timeout=90) as r:return r.read(),r.geturl(),r.headers.get('Content-Type','')

def links(html,base):
    s=html.decode('utf-8','ignore')
    found=[]
    for m in re.finditer(r'href=["\']([^"\']+)["\']',s,re.I):
        u=urljoin(base,m.group(1)); context=s[max(0,m.start()-250):m.end()+250].lower()
        if ('datos abiertos' in context or 'indice shf' in context) and any(x in u.lower() for x in ('.xlsx','.xls','.csv','download','uploads')): found.append(u)
    # preferred newest-ish links first by textual order reversed, deduplicated
    return list(dict.fromkeys(found))[::-1]

def to_rows(blob,name=''):
    if name.lower().endswith('.csv') or (b',' in blob[:500] and not blob.startswith(b'PK')):
        text=blob.decode('utf-8-sig','ignore'); return [list(r) for r in csv.reader(io.StringIO(text))]
    try:
        import openpyxl
        wb=openpyxl.load_workbook(io.BytesIO(blob),data_only=True,read_only=True)
        return [[c for c in row] for ws in wb.worksheets for row in ws.iter_rows(values_only=True)]
    except Exception as e: raise RuntimeError(f'No se pudo leer archivo SHF: {e}')

def norm_period(v):
    s=str(v or '').strip().upper().replace(' ','')
    m=re.search(r'(20\d{2})[-_/]?(?:T|Q|TRIM(?:ESTRE)?)?([1-4])',s)
    if m:return f'{m.group(1)}-T{m.group(2)}'
    # Excel date or labels like 1T2026
    m=re.search(r'([1-4])T(20\d{2})',s)
    if m:return f'{m.group(2)}-T{m.group(1)}'
    return None

def number(v):
    try:return float(str(v).replace('%','').replace(',','').strip())
    except:return None

def extract(rows):
    # Strategy A: each row includes period and one national YoY/variation figure.
    out={}
    for i,row in enumerate(rows):
        cells=[str(x or '').strip() for x in row]
        per=next((norm_period(x) for x in cells if norm_period(x)),None)
        if not per: continue
        # prioritize cells near headers/labels indicating variacion/apreciacion/nacional
        nums=[number(x) for x in row]
        nums=[x for x in nums if x is not None and -50<x<1000]
        # annual variations are typically -20..50, index typically >50
        cand=[x for x in nums if -30<=x<=50]
        if cand:
            # avoid quarter/year tokens converted to number; choose last plausible decimal/rate
            out[per]=cand[-1]
    # Strategy B: header row periods, row named Nacional/Variación anual
    for i,row in enumerate(rows):
        labels=' | '.join(str(x or '') for x in row).lower()
        if ('nacional' in labels and ('vari' in labels or 'aprecia' in labels)) or ('variación anual' in labels and 'nacional' in labels):
            for j in range(max(0,i-5),min(len(rows),i+6)):
                hdr=rows[j]
                periods=[norm_period(x) for x in hdr]
                if sum(bool(x) for x in periods)>=2:
                    for k,p in enumerate(periods):
                        if p and k<len(row):
                            v=number(row[k])
                            if v is not None and -30<=v<=50: out[p]=v
    return dict(sorted((p,v) for p,v in out.items() if int(p[:4])>=2016))



def extract_official_index(rows, annual):
    """Detect an explicitly labeled national index, base 2017=100.

    Accept only when ≥3 observed year-over-year movements independently match
    the SHF annual series (tolerance due to published rounding). Ambiguous files
    are rejected, rather than reconstructing or inventing a level.
    """
    possibilities=[]
    def normalized(x):
        import unicodedata
        return unicodedata.normalize('NFKD', str(x or '')).encode('ascii','ignore').decode().lower()
    def check(candidate):
        tests=[]
        for per,v in candidate.items():
            if per not in annual: continue
            year,quarter=per.split('-T')
            prev=candidate.get(f'{int(year)-1}-T{quarter}')
            if prev is not None and prev>0:
                tests.append(abs((v/prev-1)*100-annual[per]))
        return len(tests)>=3 and sorted(tests)[len(tests)//2]<0.75 and max(tests)<2
    # Vertical: one line per quarter, a column expressly headed "national index".
    for h,head in enumerate(rows):
        heads=[normalized(v) for v in head]
        for col,label in enumerate(heads):
            if 'indice' not in label or ('varia' in label or 'tasa' in label or 'porcent' in label):continue
            if not ('nacion' in label or any('nacion' in x for x in heads)):continue
            result={}
            for row in rows[h+1:h+180]:
                if col>=len(row):continue
                per=next((norm_period(v) for v in row[:min(3,len(row))] if norm_period(v)),None)
                value=number(row[col])
                if per and value and 60<=value<=1000:result[per]=value
            if check(result):possibilities.append(result)
    # Horizontal: row tagged national + index, columns tagged by quarters.
    for h,head in enumerate(rows):
        periods=[norm_period(v) for v in head]
        if sum(bool(t) for t in periods)<8:continue
        for row in rows[h+1:h+20]:
            description=' '.join(normalized(v) for v in row[:5])
            if 'nacion' not in description or 'indice' not in description or 'varia' in description:continue
            result={}
            for col,per in enumerate(periods):
                value=number(row[col]) if col<len(row) else None
                if per and value and 60<=value<=1000:result[per]=value
            if check(result):possibilities.append(result)
    if not possibilities:return {}
    best=max(possibilities,key=len)
    return dict(sorted((k,v) for k,v in best.items() if int(k[:4])>=2016))

def write_official_index(levels):
    if not levels:return 0
    old={}
    if OUT_LEVEL.exists():
        with OUT_LEVEL.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                v=number(r.get('indice'))
                if v is not None:old[r['periodo']]=v
    old.update(levels)
    tmp=OUT_LEVEL.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f)
        w.writerow(['periodo','indice','base','fuente'])
        for per,v in sorted(old.items()):w.writerow([per,round(v,6),'2017=100','SHF · Índice nacional oficial'])
    tmp.replace(OUT_LEVEL)
    return len(old)

STATE_ALIASES={
'NACIONAL':'Nacional','AGUASCALIENTES':'Aguascalientes','BAJA CALIFORNIA':'Baja California','BAJA CALIFORNIA SUR':'Baja California Sur','CAMPECHE':'Campeche','CHIAPAS':'Chiapas','CHIHUAHUA':'Chihuahua','CIUDAD DE MEXICO':'Ciudad de México','CDMX':'Ciudad de México','COAHUILA':'Coahuila','COAHUILA DE ZARAGOZA':'Coahuila','COLIMA':'Colima','DURANGO':'Durango','GUANAJUATO':'Guanajuato','GUERRERO':'Guerrero','HIDALGO':'Hidalgo','JALISCO':'Jalisco','MEXICO':'Estado de México','ESTADO DE MEXICO':'Estado de México','MICHOACAN':'Michoacán','MICHOACAN DE OCAMPO':'Michoacán','MORELOS':'Morelos','NAYARIT':'Nayarit','NUEVO LEON':'Nuevo León','OAXACA':'Oaxaca','PUEBLA':'Puebla','QUERETARO':'Querétaro','QUINTANA ROO':'Quintana Roo','SAN LUIS POTOSI':'San Luis Potosí','SINALOA':'Sinaloa','SONORA':'Sonora','TABASCO':'Tabasco','TAMAULIPAS':'Tamaulipas','TLAXCALA':'Tlaxcala','VERACRUZ':'Veracruz','VERACRUZ DE IGNACIO DE LA LLAVE':'Veracruz','YUCATAN':'Yucatán','ZACATECAS':'Zacatecas'}
def ascii_upper(x):
    import unicodedata
    return unicodedata.normalize('NFKD',str(x or '')).encode('ascii','ignore').decode().upper().strip()
def extract_states(rows,period):
    out=[]
    for row in rows:
        cells=[str(x or '').strip() for x in row]
        entity=None
        for x in cells[:5]:
            k=ascii_upper(x)
            if k in STATE_ALIASES: entity=STATE_ALIASES[k]; break
        if not entity: continue
        vals=[]
        for x in row:
            v=number(x)
            if v is not None and 100000<=v<=30000000: vals.append(v)
        if len(vals)>=4:
            # Los archivos SHF suelen presentar promedio, p25, mediana y p75.
            avg,p25,p50,p75=vals[-4:]
            if p25<=p50<=p75 and avg>0:
                out.append({'entidad':entity,'precio_promedio_pesos':round(avg),'p25_pesos':round(p25),'p50_pesos':round(p50),'p75_pesos':round(p75),'periodo':period,'fuente':'Sociedad Hipotecaria Federal (SHF)'})
    # Deduplicar por entidad y exigir cobertura nacional amplia.
    d={r['entidad']:r for r in out}; out=list(d.values())
    if len(out)<30 or 'Nacional' not in d:return []
    return sorted(out,key=lambda r:(r['entidad']!='Nacional',r['entidad']))
def write_states(rows):
    tmp=OUT_STATE.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['entidad','precio_promedio_pesos','p25_pesos','p50_pesos','p75_pesos','periodo','fuente']);w.writeheader();w.writerows(rows)
    tmp.replace(OUT_STATE)

def old_map():
    d={}
    if OUT.exists():
        with OUT.open(encoding='utf-8-sig',newline='') as f:
            for r in csv.DictReader(f):
                try:d[r['periodo']]=float(r['variacion_anual'])
                except:pass
    return d

def validate(new,old):
    if len(new)<8: raise RuntimeError(f'SHF: sólo se reconocieron {len(new)} trimestres; no se reemplaza la serie.')
    ov=[abs(new[p]-old[p]) for p in new if p in old]
    if ov and sum(x>1.5 for x in ov)>max(2,len(ov)//3): raise RuntimeError('SHF: la serie detectada no coincide con el histórico (posible cambio de formato).')

def main():
    html,base,_=fetch(PAGE); candidates=links(html,base)
    if not candidates: raise RuntimeError('No se encontró enlace de datos abiertos SHF en la página oficial.')
    old=old_map(); errors=[]
    for u in candidates:
        try:
            blob,final,ctype=fetch(u); rows=to_rows(blob,final); new=extract(rows); validate(new,old)
            with OUT.open('w',encoding='utf-8',newline='') as f:
                w=csv.writer(f); w.writerow(['periodo','variacion_anual']); [w.writerow([p,f'{v:.3f}'.rstrip('0').rstrip('.')]) for p,v in new.items()]
            latest=max(new); yy,qq=latest.split('-T'); label=f'{qq}T {yy}'
            level_rows=extract_official_index(rows,new)
            level_count=write_official_index(level_rows)
            state_rows=extract_states(rows,label)
            if state_rows: write_states(state_rows)
            STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'status':'ok','source_page':PAGE,'download_url':final,'latest_period':latest,'rows':len(new),'state_rows':len(state_rows),'index_level_rows':level_count,'index_level_status':'validado' if level_rows else 'pendiente_nivel_oficial'},ensure_ascii=False,indent=2),encoding='utf-8')
            print(f'SHF actualizado: {len(new)} trimestres hasta {latest}; estados={len(state_rows)}; niveles validados={level_count}'); return
        except Exception as e: errors.append(f'{u}: {e}')
    raise RuntimeError(' | '.join(errors[-4:]))
if __name__=='__main__':
    try:main()
    except Exception as e:
        STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'status':'error','error':str(e)},ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'ERROR SHF: {e}',file=sys.stderr); sys.exit(1)
