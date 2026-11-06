#!/usr/bin/env python3
"""Genera auditoría del dashboard a partir de archivos de estado y series."""
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS_LABELS = {
    'igae_imai_update_status.json': ('IGAE e IMAI construcción', 'INEGI'),
    'ifb_residencial_update_status.json': ('IFB construcción residencial', 'INEGI'),
    'icc_inpp_update_status.json': ('ICC e INPP construcción', 'INEGI'),
    'enoe_update_status.json': ('Empleo en construcción', 'INEGI ENOE'),
    'imss_datamx_update_status.json': ('Puestos IMSS construcción', 'IMSS / DataMX'),
    'imss_update_status.json': ('Indicadores IMSS', 'IMSS'),
    'shf_update_status.json': ('Índice SHF de precios de vivienda', 'SHF'),
    'pib_vab_update_status.json': ('PIB y VAB de construcción', 'INEGI'),
    'pvb_update_status.json': ('Avance del Programa de Vivienda para el Bienestar', 'Sedatu / Presidencia'),
    'conditions_update_status.json': ('Condiciones habitacionales', 'INEGI / SNIIV'),
    'enec_indices_update_status.json': ('Índices laborales ENEC', 'INEGI'),
    'enec_produccion_update_status.json': ('Producción ENEC', 'INEGI'),
    'ruv_update_status.json': ('Flujo de vivienda RUV', 'RUV / SNIIV'),
    'ruv_produccion_update_status.json': ('Producción de vivienda RUV', 'RUV / SNIIV'),
    'sniiv_kpis_update_status.json': ('Indicadores SNIIV', 'Sedatu'),
    'csvm_update_status.json': ('PIB de vivienda', 'INEGI · Cuenta Satélite de Vivienda'),
}
TIME_KEYS = {
    'checked_at_utc', 'fecha_consulta_utc', 'fecha_actualizacion_utc',
    'updated_at_utc', 'generated_at', 'run_at_utc', 'fecha_utc',
    'consultado_utc', 'procesado_utc', 'updated_at', 'timestamp'
}
PERIOD_KEYS = {
    'ultimo_periodo', 'ultimo', 'last_period', 'latest_period',
    'last_quarter', 'last_month', 'anio', 'year', 'ultimo_igae',
    'ultimo_imai', 'mes_final', 'ultimo_trimestre', 'last_quarter'
}

def walk(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in TIME_KEYS and isinstance(value, str):
                yield 'time', value
            if key in PERIOD_KEYS and isinstance(value, (str, int)):
                yield 'period', str(value)
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

def period_key(value):
    s = str(value).strip()
    patterns = [
        (r'(20\d{2})-(\d{2})-(\d{2})', lambda m: (int(m[1]), int(m[2]), int(m[3]), 4)),
        (r'(20\d{2})-(\d{2})', lambda m: (int(m[1]), int(m[2]), 0, 3)),
        (r'(20\d{2})-T([1-4])', lambda m: (int(m[1]), int(m[2])*3, 0, 2)),
        (r'(20\d{2})', lambda m: (int(m[1]), 0, 0, 1)),
    ]
    for pattern, fn in patterns:
        match = re.fullmatch(pattern, s)
        if match:
            return fn(match)
    return None

def classify(data):
    states, errors, flags = [], [], []
    def visit(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in ('status', 'estado', 'resultado') and isinstance(value, (str, bool)):
                    states.append(str(value).lower())
                if key in ('error', 'errores_consulta', 'failed') and value:
                    errors.append(value)
                if key == 'updated' and isinstance(value, bool):
                    flags.append(value)
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)
    visit(data)
    flat_errors = bool(errors)
    if flat_errors:
        return 'error / revisar'
    if any(any(token in s for token in ('conservado', 'pendiente', 'error')) for s in states):
        if any(any(token in s for token in ('actualizado', 'success', 'ok')) for s in states) or True in flags:
            return 'actualización parcial'
        return 'conservado / pendiente'
    if any(any(token in s for token in ('sin_nuevo', 'sin_novedad', 'sin_cambios')) for s in states):
        return 'consultado sin novedades'
    if any(any(token in s for token in ('actualizado', 'success', 'ok')) for s in states) or True in flags:
        return 'actualizado / verificado'
    return 'revisar estado'

def main():
    sources, verifications = [], []
    for filename, (label, provider) in STATUS_LABELS.items():
        path = ROOT / filename
        if not path.exists():
            sources.append({'label': label, 'provider': provider, 'published_latest_period': None,
                            'last_verification': None, 'status': 'sin archivo de estado', 'status_file': filename})
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except Exception as exc:
            sources.append({'label': label, 'provider': provider, 'published_latest_period': None,
                            'last_verification': None, 'status': f'error al leer estado: {exc}', 'status_file': filename})
            continue
        vals = list(walk(data))
        times = [v for kind, v in vals if kind == 'time']
        periods = [v for kind, v in vals if kind == 'period' and period_key(v)]
        last_time = max(times) if times else None
        if last_time:
            verifications.append(last_time)
        latest = max(periods, key=period_key) if periods else None
        sources.append({'label': label, 'provider': provider, 'published_latest_period': latest,
                        'last_verification': last_time, 'status': classify(data), 'status_file': filename})

    candidates = []
    csv_period_files = {
        'csvm_pib_vivienda_anual.csv': ['anio'],
        'enoe_construccion_trimestral.csv': ['periodo', 'period'],
        'shf_indice_trimestral.csv': ['periodo', 'period'],
        'igae_construccion_mensual.csv': ['periodo', 'period'],
        'ifb_residencial_mensual.csv': ['periodo', 'period'],
        'icc_incevis_base2025_mensual.csv': ['periodo', 'period'],
        'inpp_construccion_edificacion_base2025_mensual.csv': ['periodo', 'period'],
        'imss_construccion_mensual.csv': ['periodo', 'period'],
        'pvb_avance.csv': ['periodo', 'period'],
    }
    for filename, keys in csv_period_files.items():
        path = ROOT / filename
        if not path.exists():
            continue
        with path.open(encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                for key in keys:
                    value = row.get(key)
                    if value and period_key(value):
                        candidates.append(value)
    candidates.extend(s['published_latest_period'] for s in sources if s['published_latest_period'])
    latest = max(candidates, key=period_key) if candidates else None
    latest_verification = max(verifications) if verifications else None
    payload = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'latest_data_period': latest,
        'last_verification': latest_verification,
        'sources': sources,
        'audit_note': 'El periodo estadístico y la verificación técnica son fechas distintas. Los estados se clasifican desde los archivos de resultado; una ejecución de grupo exitosa no certifica por sí sola cada fuente.'
    }
    temporary = ROOT / 'updates.js.tmp'
    temporary.write_text('window.DashboardUpdates=' + json.dumps(payload, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    temporary.replace(ROOT / 'updates.js')
    print(json.dumps({'latest_data_period': latest, 'last_verification': latest_verification,
                      'sources': len(sources), 'statuses': {s['label']: s['status'] for s in sources}},
                     ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
