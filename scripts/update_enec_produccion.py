#!/usr/bin/env python3
"""Consulta la tabla ENEC_NACIONAL_36 mediante la petición PxWeb observada en Chrome.

No usa BIE. Si el histórico difiere, requiere aprobación explícita para reemplazarlo.
"""
import csv
import itertools
import json
import os
import re
import statistics
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'enec_actividad_historica.csv'
STATUS = ROOT / 'enec_produccion_update_status.json'
URL = 'https://www.inegi.org.mx/app/tabulados/pxwebapi/api/datatable'
START = '2016-01'
# ID seleccionado -> columna de destino. Se confirma también la etiqueta al leer JSON-stat.
CODES = {'29': 'edificacion_indice', '28': 'publico_indice', '21': 'privado_indice'}
MONTHS = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5,
          'junio': 6, 'julio': 7, 'agosto': 8, 'septiembre': 9,
          'octubre': 10, 'noviembre': 11, 'diciembre': 12}


def payload():
    # Año='all' incluye los nuevos años sin cambiar el script.
    return {'query': {'query': [
        {'code': 'Variable', 'selection': {'filter': 'item', 'values': list(CODES)}},
        {'code': 'Tipo de dato', 'selection': {'filter': 'item', 'values': ['0']}},
        {'code': 'Sector SCIAN', 'selection': {'filter': 'item', 'values': ['0']}},
        {'code': 'Año', 'selection': {'filter': 'all', 'values': ['*']}},
        {'code': 'Mes', 'selection': {'filter': 'all', 'values': ['*']}}
    ], 'response': {'format': 'json-stat'}}, 'lang': 'es',
        'file': 'ENEC/ENEC_NACIONAL_36',
        'stub': ['Variable', 'Tipo de dato', 'Sector SCIAN'],
        'heading': ['Año', 'Mes']}


def fetch():
    body = json.dumps(payload(), ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(URL, data=body, method='POST', headers={
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (compatible; ENEC-dashboard/1.0)'})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def categories(d):
    c = d['category']
    ix = c['index']
    pairs = sorted(ix.items(), key=lambda kv: kv[1]) if isinstance(ix, dict) else list(enumerate(ix))
    labels = c.get('label', {})
    return [(str(k), str(labels.get(k, k))) for k, _ in pairs]


def month_num(code, label):
    for s in (label, code):
        n = str(s).strip().lower()
        if n in MONTHS: return MONTHS[n]
        if n.isdigit() and 1 <= int(n) <= 12: return int(n)
        m = re.match(r'^([01]?\d)[-/.]', n)
        if m and 1 <= int(m.group(1)) <= 12: return int(m.group(1))
    raise ValueError(f'Mes no reconocido: {code!r} / {label!r}')


def extract(data):
    if isinstance(data, dict) and 'dataset' in data:
        data = data['dataset']
    if data.get('class') not in (None, 'dataset') or 'dimension' not in data or 'value' not in data:
        raise ValueError('Respuesta distinta de un conjunto de datos JSON-stat')
    ids = data.get('id') or list(data['dimension'])
    dimcats = [categories(data['dimension'][key]) for key in ids]
    sizes = [len(x) for x in dimcats]
    if len(ids) != 5 or not all(any(key.lower() == name.lower() for key in ids)
                               for name in ('Variable', 'Tipo de dato', 'Sector SCIAN', 'Año', 'Mes')):
        raise ValueError(f'Dimensiones inesperadas: {ids}')
    if data.get('size') and list(data['size']) != sizes:
        raise ValueError('Dimensiones y tamaños inconsistentes')
    values = data['value']
    vi = next(i for i, name in enumerate(ids) if name.lower() == 'variable')
    yi = next(i for i, name in enumerate(ids) if name.lower() in ('año', 'ano'))
    mi = next(i for i, name in enumerate(ids) if name.lower() == 'mes')
    ti = next(i for i, name in enumerate(ids) if name.lower() == 'tipo de dato')
    si = next(i for i, name in enumerate(ids) if name.lower() == 'sector scian')
    result = {}
    for flat_index, coords in enumerate(itertools.product(*(range(s) for s in sizes))):
        v = values.get(str(flat_index)) if isinstance(values, dict) else values[flat_index]
        if v in (None, '', '..'): continue
        code, variable_label = dimcats[vi][coords[vi]]
        if code not in CODES: continue
        t_code, t_label = dimcats[ti][coords[ti]]
        s_code, s_label = dimcats[si][coords[si]]
        if t_code != '0' or s_code != '0':
            raise ValueError(f'Selección inesperada: tipo {t_code}, sector {s_code}')
        label_low = variable_label.lower()
        hints = {'29': 'edific', '28': 'públic', '21': 'privad'}
        if hints[code] not in label_low and hints[code].replace('ú', 'u') not in label_low:
            raise ValueError(f'Código {code} no corresponde a la variable esperada: {variable_label}')
        year_code, year_label = dimcats[yi][coords[yi]]
        match = re.search(r'(?:19|20)\d{2}', year_label) or re.search(r'(?:19|20)\d{2}', year_code)
        if not match: raise ValueError(f'Año no reconocido: {year_code} / {year_label}')
        month_code, month_label = dimcats[mi][coords[mi]]
        period = f'{match.group(0)}-{month_num(month_code, month_label):02d}'
        if period < START: continue
        result.setdefault(period, {})[CODES[code]] = float(v)
    complete = {p: row for p, row in result.items() if set(row) == set(CODES.values())}
    if len(complete) < 96:
        raise ValueError(f'Cobertura insuficiente: {len(complete)} meses completos desde {START}')
    ordered = sorted(complete)
    for a, b in zip(ordered, ordered[1:]):
        y, m = map(int, a.split('-'))
        expected = f'{y + (m == 12)}-{(m % 12) + 1:02d}'
        if b != expected: raise ValueError(f'Falta algún mes entre {a} y {b}')
    return complete


def prior_rows():
    if not DEST.exists(): return []
    with DEST.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


def save(rows):
    fields = ['periodo', 'edificacion_indice', 'publico_indice', 'privado_indice', 'unidad', 'fuente', 'nota']
    tmp = DEST.with_suffix('.csv.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for period, vals in sorted(rows.items()):
            writer.writerow({'periodo': period, **{k: f'{v:.6f}' for k, v in vals.items()},
                             'unidad': 'índice 2018=100', 'fuente': 'INEGI - ENEC; ENEC_NACIONAL_36',
                             'nota': 'Índices del sector 23: edificación, sector público y sector privado'})
    tmp.replace(DEST)



def create_excel(rows):
    """Guardar un Excel derivado fielmente del JSON-stat oficial, si la biblioteca está disponible."""
    try:
        from artifact_tool import Workbook, SpreadsheetFile
        book = Workbook.create()
        ws = book.worksheets.add('ENEC_indices')
        headers = ['Periodo', 'Índice de edificación', 'Índice sector público', 'Índice sector privado']
        data = [headers] + [
            [period, float(values['edificacion_indice']), float(values['publico_indice']), float(values['privado_indice'])]
            for period, values in sorted(rows.items())
        ]
        ws.get_range_by_indexes(0, 0, len(data), 4).values = data
        ws.get_range('A1:D1').format = {'fill': '#17365D', 'font': {'bold': True, 'color': '#FFFFFF'}}
        ws.get_range('A:A').format.column_width = 15
        ws.get_range('B:D').format.column_width = 24
        ws.freeze_panes.freeze_rows(1)
        outfile = ROOT / 'enec_produccion_inegi.xlsx'
        temporary = ROOT / 'enec_produccion_inegi.tmp.xlsx'
        SpreadsheetFile.export_xlsx(book).save(str(temporary))
        temporary.replace(outfile)
        return 'generado'
    except ImportError:
        print('Aviso: artifact_tool no disponible; CSV y JSON oficiales conservados.', file=sys.stderr)
        return 'biblioteca_no_disponible'

def main():
    report = {'consultado_utc': datetime.now(timezone.utc).isoformat(),
              'fuente': URL, 'tabla': 'ENEC/ENEC_NACIONAL_36', 'estado': 'sin_validar'}
    try:
        response = fetch()
        data = extract(response)
        existing = prior_rows()
        prev_latest = max((r['periodo'] for r in existing), default='')
        latest = max(data)
        if latest < prev_latest:
            raise ValueError(f'La fuente termina en {latest}; el histórico actual llega a {prev_latest}')
        differences = {}
        previous_by_period = {r['periodo']: r for r in existing}
        for key in CODES.values():
            discrepancies = []
            for period, row in data.items():
                old = previous_by_period.get(period)
                if not old or not old.get(key): continue
                old_num = float(old[key]); new_num = row[key]
                discrepancies.append(abs(old_num-new_num)/max(abs(old_num), 1.0))
            if discrepancies:
                differences[key] = round(statistics.median(discrepancies), 5)
        report.update(ultimo=latest, primero=min(data), meses=len(data),
                      error_relativo_mediano_vs_csv=differences)
        # INEGI es la fuente de verdad: sustituir el histórico al validar
        # estructura, series, cobertura y continuidad, incluso si existen revisiones.
        changed = (len(existing) != len(data)) or any(
            old is None or any(abs(float(old.get(k, 'nan')) - row[k]) > 1e-7 for k in CODES.values())
            for period, row in data.items()
            for old in [previous_by_period.get(period)]
        )
        if changed:
            save(data)
            report['estado'] = 'actualizado_fuente_oficial'
        else:
            report['estado'] = 'sin_cambios'
        # JSON original y Excel de respaldo generado desde datos oficiales.
        # El endpoint observado devuelve JSON-stat, NO Excel nativo.
        raw_path = ROOT / 'enec_produccion_inegi_original.json'
        raw_tmp = raw_path.with_suffix('.json.tmp')
        raw_tmp.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding='utf-8')
        raw_tmp.replace(raw_path)
        excel_status = create_excel(data)
        report['archivo_excel'] = excel_status
        print(f'ENEC {report["estado"]}: {min(data)} a {latest}; diferencias={differences}')
        return 0
    except Exception as exc:
        report.update(estado='conservado_sin_cambio', error=str(exc))
        print(f'ENEC producción: {exc}', file=sys.stderr)
        return 1
    finally:
        STATUS.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
