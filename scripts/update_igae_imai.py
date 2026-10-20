#!/usr/bin/env python3
"""Actualización conservadora de índices mensuales INEGI vía API oficial.
Requiere INEGI_API_TOKEN, INEGI_IGAE_ID, INEGI_IMAI_ID; fuente por variable opcional.
No deduce automáticamente la identidad de una serie a partir de su valor.
"""
import csv, json, math, os, re, sys, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[1]
TOKEN=os.getenv('INEGI_API_TOKEN','').strip()
CFG=[('IGAE','igae_construccion_mensual.csv'),('IMAI','imai_construccion_mensual.csv')]
URL='https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{id}/es/00/false/{source}/2.0/{token}?type=json'

def pull(which):
    ind=os.getenv(f'INEGI_{which}_ID','').strip()
    source=(os.getenv(f'INEGI_{which}_SOURCE') or 'BIE-BISE').strip()
    if not re.fullmatch(r'\d{3,15}',ind): raise ValueError(f'Falta INEGI_{which}_ID (ID validado)')
    if source not in ('BISE','BIE-BISE'):raise ValueError('Fuente no permitida')
    url=URL.format(id=ind,source=source,token=TOKEN)
    req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'Indicadores-vivienda-mexico/1.0'})
    with urllib.request.urlopen(req,timeout=90) as resp: data=json.load(resp)
    series=data.get('Series') or []
    if not series:raise RuntimeError(f'{which}: respuesta sin Series; revisar ID y fuente')
    if len(series)!=1:raise RuntimeError(f'{which}: numero inesperado de series')
    info=series[0]
    rows={}
    for o in info.get('OBSERVATIONS',[]):
        period=str(o.get('TIME_PERIOD','')).strip()
        if not re.fullmatch(r'\d{4}-\d{2}',period) or not ('01'<=period[-2:]<='12') or period<'2016-01':continue
        try: val=float(str(o.get('OBS_VALUE','')).replace(',',''))
        except ValueError:continue
        if math.isfinite(val) and val>0:rows[period]=val
    if len(rows)<100 or '2016-01' not in rows:raise RuntimeError(f'{which}: historial insuficiente: {len(rows)}')
    return ind,source,rows,info

def historical(path):
    if not path.exists():return {}
    with path.open(encoding='utf-8-sig',newline='') as f:
        return {r['periodo']:float(r['indice']) for r in csv.DictReader(f) if r.get('periodo') and r.get('indice')}

def write(path, data):
    periods=sorted(data)
    lines=[]
    for i,p in enumerate(periods):
        x=data[p]; previous=data.get(periods[i-1]) if i else None
        prev_year=data.get(f'{int(p[:4])-1}-{p[-2:]}')
        lines.append({'periodo':p,'indice':round(x,9),'variacion_mensual':round((x/previous-1)*100,9) if previous else '', 'variacion_anual':round((x/prev_year-1)*100,9) if prev_year else ''})
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['periodo','indice','variacion_mensual','variacion_anual']);w.writeheader();w.writerows(lines)

def main():
    if not TOKEN:raise RuntimeError('Falta INEGI_API_TOKEN en GitHub Secrets')
    checked=[]
    for which,filename in CFG:
        indicator,source,new,info=pull(which)
        path=ROOT/filename; old=historical(path)
        # Los datos oficiales pueden revisarse; tolerar revisiones, nunca retroceder mes.
        if old and max(new)<max(old):raise RuntimeError(f'{which}: el ultimo mes retrocede de {max(old)} a {max(new)}')
        # Proteger contra seleccionar por accidente un indicador de otra escala.
        common=sorted(set(new)&set(old))[-24:]
        if old and len(common)>=6:
            errors=sorted(abs(new[p]-old[p])/old[p] for p in common if old[p]>0)
            if len(errors)>=6 and errors[len(errors)//2]>0.02:
                raise RuntimeError(f'{which}: el ID no coincide con el CSV historico; desviacion mediana >2%')
        checked.append((which,filename,indicator,source,new))
    # Ambas series deben validarse antes de escribir cualquiera.
    for which,filename,indicator,source,series in checked:
        write(ROOT/filename,series)
        print(f'{which}: {len(series)} meses; {min(series)} a {max(series)}; ID={indicator}; fuente={source}')
    (ROOT/'igae_imai_update_status.json').write_text(json.dumps({'fecha_utc':datetime.now(timezone.utc).isoformat(),'resultado':'ok','series':[{'nombre':x[0],'id':x[2],'fuente':x[3],'observaciones':len(x[4]),'ultimo_mes':max(x[4])} for x in checked]},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERROR:',str(e),file=sys.stderr);sys.exit(1)
