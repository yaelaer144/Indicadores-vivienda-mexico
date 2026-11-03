#!/usr/bin/env python3
"""ENOE trimestral nacional: valida la fuente oficial antes de actualizar el CSV.

INEGI_API_TOKEN: token de la API del Banco de Indicadores.
INEGI_ID_ENOE_CONSTRUCCION / INEGI_ID_ENOE_OCUPADA_TOTAL: IDs opcionales
identificados en el constructor del INEGI (tienen prioridad).
Todos los valores CSV se expresan en MILES de personas.
"""
import csv
import json
import os
import re
import statistics
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'enoe_construccion_trimestral.csv'
RES = ROOT / 'inegi_resolved_ids.json'
STATUS = ROOT / 'enoe_update_status.json'
TOKEN = os.getenv('INEGI_API_TOKEN', '').strip().strip('"').strip("'")
BASE = 'https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml'
UA = 'Indicadores-vivienda-mexico/ENOE-1.0'


def norm(value):
    value = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def request_json(path):
    url = f'{BASE}/{path}/{urllib.parse.quote(TOKEN)}?type=json'
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def period(value):
    s = str(value or '').strip().upper().replace(' ', '')
    patterns = [r'^(20\d{2})[-/]?[TQ]([1-4])$', r'^(20\d{2})[-/]?([1-4])$',
                r'^(20\d{2})[-/](0?[369]|12)$']
    for index, pat in enumerate(patterns):
        m = re.fullmatch(pat, s)
        if m:
            q = (int(m[2]) // 3) if index == 2 else int(m[2])
            return f'{m[1]}-T{q}'
    return None


def numeric(value):
    try:
        x = float(str(value).replace(',', '').strip())
        return x if x == x and abs(x) != float('inf') else None
    except (ValueError, TypeError):
        return None


def read_existing():
    if not OUT.exists():
        return []
    with OUT.open(encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def get_indicator(identifier, source):
    payload = request_json(f'INDICATOR/{identifier}/es/00/false/{source}/2.0')
    series = payload.get('Series') or []
    if not series:
        raise ValueError('La API no devolvió series')
    chosen = series[0]
    values = {}
    for observation in chosen.get('OBSERVATIONS') or []:
        p = period(observation.get('TIME_PERIOD'))
        val = numeric(observation.get('OBS_VALUE'))
        if p and val is not None and val >= 0:
            values[p] = val
    if not values:
        raise ValueError('No hay observaciones trimestrales nacionales')
    return values


def median_error(series, existing, field, scale):
    errors = []
    for row in existing:
        original = numeric(row.get(field))
        current = series.get(row.get('periodo'))
        if original is not None and original > 0 and current is not None:
            errors.append(abs(current / scale - original) / original)
    return (statistics.median(errors), len(errors)) if len(errors) >= 4 else (None, len(errors))


def candidates(field, existing_ids, catalog):
    setting = 'INEGI_ID_ENOE_CONSTRUCCION' if field == 'total' else 'INEGI_ID_ENOE_OCUPADA_TOTAL'
    key = 'enoe_construccion' if field == 'total' else 'enoe_ocupada_total'
    results = []
    for identifier in [os.getenv(setting, '').strip(), str(existing_ids.get(key) or '')]:
        if identifier.isdigit():
            results.append(identifier)
    scored = []
    for item in catalog:
        desc = norm(item.get('Description'))
        identifier = str(item.get('value') or '')
        if not identifier.isdigit() or not ('ocupad' in desc and 'poblacion' in desc):
            continue
        if any(x in desc for x in ('porcentaje', 'tasa', 'hombres', 'mujeres', 'entidad federativa', 'participacion')):
            continue
        if field == 'total':
            if 'construccion' not in desc:
                continue
            score = 20 + (5 if 'sector' in desc else 0)
        else:
            if 'construccion' in desc:
                continue
            score = 20 if ('total' in desc or 'nacional' in desc) else 8
        scored.append((score, identifier))
    results.extend(i for _, i in sorted(scored, reverse=True)[:35])
    return list(dict.fromkeys(results)), key


def resolve(field, existing, existing_ids, catalog):
    ids, key = candidates(field, existing_ids, catalog)
    if not ids:
        raise RuntimeError(f'No hay IDs candidatos para {field}; configure INEGI_ID_ENOE_* o compruebe catálogo')
    matches = []
    for identifier in ids:
        for source in ('BISE', 'BIE-BISE'):
            try:
                data = get_indicator(identifier, source)
                for scale in (1, 1000):
                    err, overlap = median_error(data, existing, 'total' if field == 'total' else 'ocupada_total', scale)
                    if err is not None:
                        matches.append((err, -overlap, identifier, source, scale, data))
            except (ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                continue
    if not matches:
        raise RuntimeError(f'{field}: ningún indicador pudo compararse con al menos 4 trimestres históricos')
    matches.sort(key=lambda x: (x[0], x[1]))
    error, neg_overlap, identifier, source, scale, data = matches[0]
    if error > 0.04:
        raise RuntimeError(f'{field}: discrepancia con serie existente: {error:.1%} (límite 4%); no se reemplazan datos')
    return {p: v / scale for p, v in data.items()}, {'id': identifier, 'source': source,
                                                        'scale': scale, 'median_relative_error': round(error, 6),
                                                        'overlap_quarters': -neg_overlap}, key


def write_json(path, obj):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    temporary.replace(path)


def main():
    status = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'source': 'INEGI ENOE / Banco de Indicadores',
              'units': 'miles de personas', 'updated': False}
    try:
        if not TOKEN:
            raise RuntimeError('Falta el secret INEGI_API_TOKEN en GitHub Actions')
        old = read_existing()
        try:
            resolved = json.loads(RES.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            resolved = {}
        try:
            catalog = request_json('CL_INDICATOR/null/es/BIE-BISE/2.0').get('CODE') or []
        except Exception as ex:
            print(f'AVISO: Catálogo no disponible ({type(ex).__name__}); se probarán IDs conocidos', flush=True)
            catalog = []
        cons, cmeta, ckey = resolve('total', old, resolved, catalog)
        national, nmeta, nkey = resolve('occupied_total', old, resolved, catalog)
        common = sorted(p for p in set(cons) & set(national) if p >= '2016-T1')
        if len(common) < 8:
            raise RuntimeError('Menos de 8 trimestres comunes; se conserva el CSV previo')
        # No publicar datos que pierdan el último trimestre disponible.
        previous_last = max((r.get('periodo', '') for r in old), default='')
        if common[-1] < previous_last:
            raise RuntimeError(f'La fuente retrocede de {previous_last} a {common[-1]}; se conserva el histórico')
        # Un indicador debe tener órdenes de magnitud plausibles y ser subconjunto del nacional.
        for p in common:
            if not (500 <= cons[p] <= 12000 and 30000 <= national[p] <= 100000 and cons[p] < national[p]):
                raise RuntimeError(f'Unidades/valores ENOE no plausibles en {p}; se conserva el CSV')
        result = []
        for p in common:
            result.append({'periodo': p, 'total': f'{cons[p]:.3f}', 'ocupada_total': f'{national[p]:.3f}',
                           'formal': '', 'informal': ''})
        temp = OUT.with_suffix('.csv.tmp')
        with temp.open('w', encoding='utf-8-sig', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=['periodo', 'total', 'ocupada_total', 'formal', 'informal'])
            writer.writeheader()
            writer.writerows(result)
        temp.replace(OUT)
        resolved[ckey], resolved[nkey] = cmeta['id'], nmeta['id']
        write_json(RES, resolved)
        status.update(updated=True, first_quarter=common[0], last_quarter=common[-1], observations=len(common),
                      construction=cmeta, national=nmeta,
                      historical_2016_complete=(common[0] == '2016-T1'),
                      note='No hay estimaciones de trimestres faltantes; formal/informal no se inventan.')
        print(f"ENOE validada: {common[0]} a {common[-1]}; {len(common)} trimestres; "
              f"construcción {result[-1]['total']} mil; nacional {result[-1]['ocupada_total']} mil")
    except Exception as exc:
        status.update(error=str(exc))
        print(f'ERROR ENOE: {exc}', flush=True)
        raise
    finally:
        write_json(STATUS, status)


if __name__ == '__main__':
    main()
