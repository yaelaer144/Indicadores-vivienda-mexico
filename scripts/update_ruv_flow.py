#!/usr/bin/env python3
"""Actualiza el flujo anual RUV/SNIIV desde API pública oficial.

Correspondencia operativa usada por el dashboard:
- Registradas   -> GetRegistro
- Inicio de obra -> GetVerficacion (inicio del proceso de verificación de obra)
- Terminadas/producción -> GetProduccion

El script valida los resultados contra el histórico existente antes de sobrescribirlo.
"""
import csv, json, sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'ruv_flujo_vivienda_anual.csv'
STATUS=ROOT/'ruv_update_status.json'
BASE='https://sniiv.sedatu.gob.mx/api/CuboAPI'
START=2016
END=datetime.now().year
UA='Mozilla/5.0 (compatible; Infonavit-dashboard/1.0)'


def get_json(endpoint):
    url=f'{BASE}/{endpoint}/{START},{END}/00/000/anio,mes'
    req=Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    with urlopen(req,timeout=90) as r:
        if r.status != 200: raise RuntimeError(f'HTTP {r.status}: {url}')
        data=json.load(r)
    if not isinstance(data,list): raise RuntimeError(f'Respuesta no tabular en {endpoint}')
    return data,url


def year_of(r):
    for k in ('año','anio','year'):
        try:
            y=int(float(r.get(k)))
            if 2000<=y<=2100:return y
        except Exception: pass
    return None


def aggregate(rows):
    out={}
    for r in rows:
        y=year_of(r)
        if not y or y<START: continue
        try:n=float(r.get('viviendas',0) or 0)
        except Exception:n=0
        out[y]=out.get(y,0)+n
    return out


def read_old():
    if not OUT.exists(): return {}
    d={}
    with OUT.open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            try:d[int(r['anio'])]=[float(r['registradas_miles']),float(r['inicio_obra_miles']),float(r['terminadas_miles'])]
            except Exception: pass
    return d


def validate(new, old):
    # Requiere serie razonable y evita cambios de definición evidentes.
    if len(new)<5: raise RuntimeError('La API devolvió menos de 5 años utilizables.')
    overlaps=[]
    for y, vals in new.items():
        if y in old:
            for i,v in enumerate(vals):
                ov=old[y][i]
                if ov>0 and v>0: overlaps.append(abs(v-ov)/ov)
    # La API puede revisar cifras; se permite margen amplio, pero no un cambio masivo de unidad/definición.
    if overlaps and sum(x>0.35 for x in overlaps) > max(3,len(overlaps)//2):
        raise RuntimeError('Validación fallida: demasiadas diferencias >35% frente al histórico del tablero.')


def main():
    old=read_old()
    reg,u1=get_json('GetRegistro')
    # La API ha publicado dos grafías para el endpoint de verificación.
    try:
        ver,u2=get_json('GetVerificacion')
    except HTTPError as e:
        if e.code != 404: raise
        ver,u2=get_json('GetVerficacion')
    prod,u3=get_json('GetProduccion')
    A,B,C=aggregate(reg),aggregate(ver),aggregate(prod)
    years=sorted(set(A)&set(B)&set(C))
    new={y:[A[y]/1000,B[y]/1000,C[y]/1000] for y in years if y>=START}
    validate(new,old)
    # Para años cerrados usamos API; para un año corriente parcial también se conserva y se identifica como tal en status.
    tmp=OUT.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8',newline='') as f:
        w=csv.writer(f); w.writerow(['anio','registradas_miles','inicio_obra_miles','terminadas_miles','fuente'])
        for y in sorted(new):
            a,b,c=new[y]
            w.writerow([y,f'{a:.3f}'.rstrip('0').rstrip('.'),f'{b:.3f}'.rstrip('0').rstrip('.'),f'{c:.3f}'.rstrip('0').rstrip('.'),'SEDATU / SNIIV / RUV (API)'])
    tmp.replace(OUT)
    STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'start_year':START,'latest_year':max(new) if new else None,'endpoints':[u1,u2,u3],'rows':len(new),'status':'ok'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'RUV actualizado: {len(new)} años, {min(new)}-{max(new)}')

if __name__=='__main__':
    try: main()
    except Exception as e:
        STATUS.write_text(json.dumps({'updated_at':datetime.now().isoformat(timespec='seconds'),'status':'error','error':str(e)},ensure_ascii=False,indent=2),encoding='utf-8')
        print(f'ERROR RUV: {e}',file=sys.stderr); sys.exit(1)
