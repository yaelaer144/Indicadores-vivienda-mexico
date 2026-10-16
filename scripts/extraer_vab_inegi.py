#!/usr/bin/env python3
"""Extrae VAB trimestral de PIBT CSV exportado por INEGI (base 2018).
Uso: python extraer_vab_inegi.py PIBT_2.csv vab_construccion_subsectores_trimestral.csv
Conserva el archivo de salida si la estructura no es válida.
"""
import csv, re, sys
from pathlib import Path

CODES = {'23': 'construccion_mdp_2018', '236': 'edificacion_mdp_2018', '237': 'obra_civil_mdp_2018', '238': 'trabajos_especializados_mdp_2018'}
FIELDS = ['periodo', *CODES.values(), 'construccion_yoy', 'edificacion_yoy', 'obra_civil_yoy', 'trabajos_especializados_yoy']

def extract(source):
    with open(source, encoding='utf-8-sig', newline='') as f:
        reader=csv.reader(f)
        header=next(reader)
        rows=list(reader)
    quarters=[]
    for index, col in enumerate(header):
        match=re.fullmatch(r'\s*(\d{4})\s*\|\s*T([1-4])(?:\s+[PR])?\s*', col)
        if match and int(match.group(1))>=2018:
            quarters.append((index, f'{match.group(1)}-T{match.group(2)}'))
    if not quarters: raise ValueError('No se encontraron columnas trimestrales base 2018')
    # La primera sección corresponde a niveles. Otras secciones: variación y composición porcentual.
    section=[]
    for row in rows:
        if row and 'Variación porcentual anual' in row[0]:break
        section.append(row)
    selected={}
    for row in section:
        if not row:continue
        match=re.match(r'^\s*(23|236|237|238)\s*-\s*(.*)',row[0])
        if match and match.group(1) not in selected:
            selected[match.group(1)]=row
    if set(selected)!=set(CODES): raise ValueError(f'Faltan series {set(CODES)-set(selected)}')
    result=[]
    for idx,period in quarters:
        vals={}
        for code,field in CODES.items():
            raw=selected[code][idx].strip() if idx<len(selected[code]) else ''
            if raw in ('','NA','N/D'):break
            vals[field]=float(raw.replace(',',''))
        if len(vals)!=4:continue
        if any(v<=0 for v in vals.values()):raise ValueError(f'Valor no positivo en {period}')
        if abs(vals[CODES['23']]-sum(vals[CODES[k]] for k in ('236','237','238')))>5:raise ValueError(f'Subsectores no concilian con sector 23 en {period}')
        result.append({'periodo':period,**vals})
    if len(result)<20:raise ValueError('Serie trimestral insuficiente; se conserva CSV existente')
    by={r['periodo']:r for r in result}
    for r in result:
        y,q=r['periodo'].split('-T'); prior=by.get(f'{int(y)-1}-T{q}')
        for col,yoy in zip(CODES.values(),FIELDS[5:]):
            r[yoy]=round((r[col]/prior[col]-1)*100,6) if prior and prior[col] else ''
    return result

def main():
    source=Path(sys.argv[1]) if len(sys.argv)>1 else Path('PIBT_2.csv')
    dest=Path(sys.argv[2]) if len(sys.argv)>2 else Path('vab_construccion_subsectores_trimestral.csv')
    rows=extract(source)
    tmp=dest.with_suffix(dest.suffix+'.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader();writer.writerows(rows)
    tmp.replace(dest)
    print(f'VAB validado: {len(rows)} trimestres; {rows[0]["periodo"]} a {rows[-1]["periodo"]}')

if __name__=='__main__':main()
