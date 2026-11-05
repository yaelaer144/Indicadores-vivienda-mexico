#!/usr/bin/env python3
"""Actualización conservadora de condiciones habitacionales.

Actualiza los CSV que YA utiliza el dashboard; no necesita cargas manuales.
No sustituye cifras con valores no comprobables ni inventa años.
"""
import csv
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = 'Mozilla/5.0 (compatible; IndicadoresVivienda/1.0; datos públicos)'
CSV_TENURE = ROOT / 'tenencia_2024.csv'
CSV_HIST = ROOT / 'tenencia_historica.csv'
CSV_AREA = ROOT / 'tenencia_rural_urbano_2024.csv'
CSV_CARENCIAS = ROOT / 'condiciones_historicas.csv'
CSV_CONAVI = ROOT / 'condiciones_resumen_2024.csv'
PDF_PM = 'https://www.inegi.org.mx/contenidos/desarrollosocial/pm/doc/pm_presentacion_{year}.pdf'


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=90) as response:
        return response.read()


def read_csv(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, columns, rows):
    # Escritura atómica y con esquema fijo: evita el fallo "dict contains fields not in fieldnames".
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(path)


def number(value):
    try:
        return float(str(value).replace(',', '').strip())
    except (TypeError, ValueError):
        return None


def published_years():
    # ENIGH es bienal. Un levantamiento nuevo solo se usará cuando realmente esté publicado.
    year = datetime.now(timezone.utc).year
    return list(range(year if year % 2 == 0 else year-1, 2015, -2))


def get_viviendas(year):
    url = f'https://www.inegi.org.mx/contenidos/programas/enigh/nc/{year}/microdatos/enigh{year}_ns_viviendas_csv.zip'
    payload = fetch(url)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        candidates = [name for name in z.namelist() if name.lower().endswith('.csv') and 'vivienda' in name.lower()]
        if not candidates:
            raise ValueError('ZIP sin tabla viviendas.csv')
        raw = z.read(candidates[0])
    # INEGI publica microdatos habitualmente en UTF-8 o Latin-1.
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            rows = list(csv.DictReader(io.StringIO(raw.decode(enc))))
            if rows and {'tenencia', 'tam_loc', 'factor'}.issubset(rows[0]):
                return rows
        except UnicodeDecodeError:
            pass
    raise ValueError(f'ENIGH {year}: no se localizaron tenencia, tam_loc y factor')


def update_tenure():
    errors = []
    latest = max((int(r['anio']) for r in read_csv(CSV_TENURE) if r.get('anio', '').isdigit()), default=0)
    # No descargar varios años históricos innecesariamente en cada ejecución.
    for year in published_years():
        if year < max(2024, latest):
            break
        try:
            rows = get_viviendas(year)
            # La vivienda es la unidad de análisis. Exigir factores positivos y códigos válidos.
            parsed = []
            for r in rows:
                factor = number(r.get('factor'))
                tenure = str(r.get('tenencia', '')).strip()
                size = str(r.get('tam_loc', '')).strip()
                if factor is not None and factor > 0 and tenure in {'1','2','3','4','5','6'} and size in {'1','2','3','4'}:
                    parsed.append((factor, tenure, size))
            total = sum(f for f,_,_ in parsed)
            if total < 1_000_000 or len(parsed) < 1000:
                raise ValueError('Datos ponderados incompletos o insuficientes')
            codes = [('Propia totalmente pagada', {'4'}), ('Propia pagándose', {'3'}), ('Rentada', {'1'}), ('Otros', {'2','5','6'})]
            groups = {label: sum(f for f,t,_ in parsed if t in cats) for label,cats in codes}
            if abs(sum(groups.values())-total) > total*0.000001:
                raise ValueError('Los grupos de tenencia no suman el total')
            national = [{'anio':year, 'categoria':label, 'porcentaje':round(100*value/total, 6), 'viviendas':round(value), 'definicion':f'Estimación directa ponderada con microdatos ENIGH {year}'} for label,value in groups.items()]
            row = {'anio':year, 'propia_pagada_pct':national[0]['porcentaje'], 'propia_pagandose_pct':national[1]['porcentaje'], 'rentada_pct':national[2]['porcentaje'], 'otros_pct':national[3]['porcentaje']}
            historic = [r for r in read_csv(CSV_HIST) if r.get('anio') != str(year)]
            historic.append(row)
            historic.sort(key=lambda r:int(r['anio']))
            areas=[]
            for area, sizes in [('Rural', {'4'}), ('Urbano', {'1','2','3'})]:
                subset=[(f,t) for f,t,size in parsed if size in sizes]
                denominator=sum(f for f,_ in subset)
                if denominator <= 0:raise ValueError('Sin observaciones en ' + area)
                vals=[round(100*sum(f for f,t in subset if t in cats)/denominator,6) for _,cats in codes]
                if abs(sum(vals)-100)>0.01:raise ValueError('Grupos no suman 100 en ' + area)
                areas.append({'ambito':area,'propia':vals[0],'pagandose':vals[1],'rentada':vals[2],'otros':vals[3], 'nota':f'ENIGH {year}, estimación directa ponderada con factor de expansión'})
            # Los tres archivos se mantienen con nombres estables para data-loader.js.
            write_csv(CSV_TENURE, ['anio','categoria','porcentaje','viviendas','definicion'], national)
            write_csv(CSV_HIST, ['anio','propia_pagada_pct','propia_pagandose_pct','rentada_pct','otros_pct'], historic)
            write_csv(CSV_AREA, ['ambito','propia','pagandose','rentada','otros','nota'], areas)
            return {'estado':'actualizado', 'anio':year, 'viviendas_expandidas':round(total), 'fuente':'INEGI ENIGH microdatos VIVIENDAS'}
        except Exception as exc:
            errors.append(f'{year}: {exc}')
    return {'estado':'conservado_sin_cambio','ultimo_anio':latest or None,'detalle':errors[:3]}


def extract_percent_series(text, label, years):
    # Tomar la FILA de la tabla, no un bloque arbitrario de 900 caracteres
    # que puede incorporar porcentajes de otras variables o millones de personas.
    lines = [re.sub(r'\s+', ' ', line).strip() for line in text.splitlines()]
    pattern = re.compile(label, re.IGNORECASE)
    for i, line in enumerate(lines):
        if not pattern.search(line):
            continue
        # Aceptar valores que aparecen inmediatamente después de la etiqueta.
        fragment = ' '.join(lines[i:i+3])
        match = pattern.search(fragment)
        suffix = fragment[match.end():] if match else ''
        values = [float(v) for v in re.findall(r'(?<!\d)(\d{1,2}\.\d)(?!\d)',suffix)]
        if len(values)>=len(years):
            return values[:len(years)]
    return None


def update_carencias():
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('Falta dependencia pypdf') from exc
    original={int(r['anio']):r for r in read_csv(CSV_CARENCIAS) if str(r.get('anio','')).isdigit()}
    latest=max(original,default=0)
    errors=[]
    for year in published_years():
        if year < max(2024,latest):break
        try:
            data=fetch(PDF_PM.format(year=year))
            reader=PdfReader(io.BytesIO(data))
            # Se trata de una revisión bienal: extraer el texto íntegro en orden.
            content='\n'.join(page.extract_text() or '' for page in reader.pages)
            years=list(range(2016,year+1,2))
            quality=extract_percent_series(content,r'Carencia por calidad y espacios de la vivienda',years)
            services=extract_percent_series(content,r'Carencia por acceso a los servicios b[aá]sicos en la vivienda',years)
            if quality is None or services is None:
                raise ValueError('No se identificaron las dos filas de porcentajes nacionales')
            # Comparar todas las cifras previamente validadas; tolerancia por redondeo.
            for i,y in enumerate(years):
                if y in original:
                    q=number(original[y]['carencia_calidad_espacios_pct'])
                    s=number(original[y]['carencia_servicios_basicos_pct'])
                    if q is not None and s is not None and (abs(quality[i]-q)>0.15 or abs(services[i]-s)>0.15):
                        raise ValueError(f'La lectura de {y} no coincide con el histórico validado')
            if not all(0<=v<=100 for v in quality+services):raise ValueError('Porcentajes fuera de rango')
            combined=dict(original)
            for i,y in enumerate(years):
                combined[y]={'anio':y,'carencia_calidad_espacios_pct':quality[i], 'carencia_servicios_basicos_pct':services[i], 'unidad':'% de la población', 'fuente':'INEGI · Pobreza multidimensional / ENIGH'}
            if year > latest:
                write_csv(CSV_CARENCIAS, ['anio','carencia_calidad_espacios_pct','carencia_servicios_basicos_pct','unidad','fuente'], [combined[y] for y in sorted(combined)])
                return {'estado':'actualizado','anio':year,'fuente':PDF_PM.format(year=year)}
            return {'estado':'sin_nuevo_levantamiento','ultimo_anio':latest}
        except Exception as exc:
            errors.append(f'{year}: {exc}')
    return {'estado':'conservado_sin_cambio','ultimo_anio':latest or None,'detalle':errors[:3]}


def update_conavi():
    # No inferir años ni porcentajes a partir de números sueltos extraídos de un PDF.
    # Los datos existentes quedan disponibles; actualización requiere fuente estructurada
    # con correspondencia explícita de indicador, unidad y año.
    rows=read_csv(CSV_CONAVI)
    years=sorted({int(r['anio']) for r in rows if r.get('anio','').isdigit()})
    return {'estado':'conservado_pendiente_fuente_estructurada', 'ultimo_anio':max(years) if years else None, 'detalle':'CONAVI/SIESCO: se conserva el último valor; no se reemplazan indicadores por extracción ambigua de PDF'}


def main():
    report={'checked_at_utc':datetime.now(timezone.utc).isoformat(), 'tenencia':None,'carencias':None,'conavi':None}
    for key, fn in [('tenencia',update_tenure), ('carencias',update_carencias), ('conavi',update_conavi)]:
        try:report[key]=fn()
        except Exception as exc:report[key]={'estado':'error_conservado','error':str(exc)}
    (ROOT/'conditions_update_status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    # La ausencia de publicación no es error. Fallos técnicos explícitos sí se notifican.
    if any(report[k]['estado']=='error_conservado' for k in ('tenencia','carencias','conavi')):
        raise SystemExit(1)

if __name__ == '__main__':main()
