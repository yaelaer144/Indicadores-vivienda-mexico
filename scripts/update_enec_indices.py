#!/usr/bin/env python3
"""Actualizador ENEC directo: seis índices por sector 23/subsector 236.

No depende de CL_INDICATOR. Publica CSV únicamente si todas las series
son utilizables y pasan la validación contra el histórico local.
"""
import csv
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'enec_indices_laborales_mensual.csv'
STATUS = ROOT / 'enec_indices_update_status.json'

IDS = {
    # Personal ocupado total
    'personal_construccion': '720286',
    'personal_edificacion': '722171',

    # Personal ocupado por tipo de trabajador
    'personal_obreros': '720290',
    'personal_administrativos': '720292',

    # Horas trabajadas - series actuales
    'horas_construccion': '720298',
    'horas_edificacion': '722195',

    # Remuneraciones - series actuales
    'remuneraciones_construccion': '720318',
    'remuneraciones_edificacion': '722235',
}

COLUMNS = ['periodo', *IDS.keys(), 'base', 'fuente']
API = ('https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/'
       'INDICATOR/{id}/es/00/false/BIE-BISE/2.0/{token}?type=json')
UA = 'Mozilla/5.0 (compatible; indicadores-vivienda/1.0)'
MONTH = re.compile(r'^((?:19|20)\d{2})[-/]?(0?[1-9]|1[0-2])$')


def get_series(indicator_id, token):
    url = API.format(id=indicator_id, token=quote(token, safe=''))
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not data.get('Series'):
        raise ValueError(f'{indicator_id}: respuesta sin Series')
    if len(data['Series']) != 1:
        raise ValueError(f'{indicator_id}: se esperaban una sola serie, hay {len(data["Series"])}')
    entry = data['Series'][0]
    result = {}
    for obs in entry.get('OBSERVATIONS') or []:
        m = MONTH.fullmatch(str(obs.get('TIME_PERIOD') or '').strip())
        if not m:
            continue
        raw = obs.get('OBS_VALUE')
        if raw in (None, '', 'N/E', 'NA'):
            continue
        try:
            value = float(str(raw).replace(',', ''))
        except ValueError:
            continue
        if not (0 < value < 10000):
            continue
        period = f'{m.group(1)}-{int(m.group(2)):02d}'
        if period >= '2016-01':
            result[period] = value
    if len(result) < 24:
        raise ValueError(f'{indicator_id}: insuficiente histórico mensual ({len(result)})')
    return result, {'id':indicator_id, 'descripcion':entry.get('INDICADOR'),
                    'unidad':entry.get('UNIT'), 'frecuencia':entry.get('FREQ'),
                    'primero':min(result), 'ultimo':max(result), 'observaciones':len(result)}


def previous_rows():
    if not OUT.exists():
        return {}
    with OUT.open(encoding='utf-8-sig', newline='') as f:
        return {r['periodo']:r for r in csv.DictReader(f) if r.get('periodo')}


def check_overlap(series, old):
    """Rechaza cambios de escala o serie de otro concepto (comparación 2018+)."""
    checks = {}
    for column, observations in series.items():
        errors = []
        for period, row in old.items():
            if period not in observations:
                continue
            try:
                prior = float(row[column])
            except (ValueError, KeyError, TypeError):
                continue
            if prior > 0:
                errors.append(abs(observations[period] / prior - 1))
        median = statistics.median(errors) if errors else None
        checks[column] = {'comparaciones':len(errors), 'error_relativo_mediano':median}
        # No asumimos que todo histórico es idéntico: las revisiones estadísticas existen.
        if len(errors) >= 6 and median > 0.15:
            raise ValueError(f'{column}: divergencia mediana {median:.1%} contra histórico; no se sobrescribe')
    return checks


def update_enec():
    token = os.environ.get('INEGI_API_TOKEN', '').strip()
    if not token:
        raise RuntimeError('Falta INEGI_API_TOKEN en Secrets de GitHub')
    report = {'fuente':'INEGI ENEC 2018, índices originales',
              'fecha_utc':datetime.now(timezone.utc).isoformat(), 'series':{},
              'estado':'error'}
    try:
        series = {}
        for column, indicator_id in IDS.items():
            series[column], report['series'][column] = get_series(indicator_id, token)
        old = previous_rows()
        report['comparacion_historica'] = check_overlap(series, old)
        # Solo periodos con las seis observaciones: no completar huecos con valores inventados.
        periods = sorted(set.intersection(*(set(values) for values in series.values())))
        periods = [p for p in periods if p >= '2016-01']
        if len(periods) < 24:
            raise ValueError(f'Intersección insuficiente de seis series ({len(periods)})')
        if old and max(periods) < max(old):
            raise ValueError('La fuente tiene fecha final anterior al archivo actual')
        # Conservar observaciones históricas válidas anteriores al primer periodo común.
        output = {p:dict(row) for p,row in old.items() if p < min(periods)}
        for p in periods:
            output[p] = {'periodo':p, **{column:series[column][p] for column in IDS},
                         'base':'2018=100','fuente':'INEGI · ENEC (API BIE-BISE)'}
        tmp = OUT.with_suffix('.csv.tmp')
        with tmp.open('w',encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
            w.writeheader()
            w.writerows(output[p] for p in sorted(output))
        tmp.replace(OUT)
        report.update({'estado':'actualizado','ultimo_periodo':max(periods),
                       'primer_periodo':min(output), 'filas':len(output)})
        return {'ultimo':max(periods),'ids':IDS,'observaciones':len(output)}
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        STATUS.write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
        print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__ == '__main__':
    try:
        update_enec()
    except Exception as exc:
        print(f'ENEC: no actualizado, histórico conservado: {exc}',file=sys.stderr)
        sys.exit(1)
