#!/usr/bin/env python3
"""Actualiza SBC construcción consultando STPS Cognos con Playwright.

No requiere CSV manual. Preserva observaciones IMSS existentes; STPS
completa los meses desde julio de 2016 y agrega periodos nuevos.
El dashboard mensualiza el SBC diario multiplicando por 30.4.
"""
import csv
import json
import re
import tempfile
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SALARIOS = ROOT / 'imss_sbc_construccion_mensual.csv'
STATUS = ROOT / 'imss_salarios_stps_status.json'
BASE = 'http://siel.stps.gob.mx:303/ibmcognos/cgi-bin/cognos.cgi'
PATH = (
    "/content/folder[@name='Sitio STPS']"
    "/folder[@name='2. Salarios']"
    "/folder[@name='Salario asociado a trabajadores']"
    "/report[@name='Salario por Actividad Económica']"
)
MONTHS = {'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6,
          'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12,
          'ene':1, 'abr':4, 'ago':8, 'dic':12}
DATE_PATTERN = re.compile(
    r'(?<!\d)(20\d{2})/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|Ene|Abr|Ago|Dic)(?!\w)',
    re.IGNORECASE
)


def escape_cognos(s):
    out = []
    for b in s.encode('utf-8'):
        if 48 <= b <= 57 or 65 <= b <= 90 or 97 <= b <= 122 or b in (45,46,95):
            out.append(chr(b))
        else:
            out.append(f'*{b:02x}')
    return ''.join(out)


def url_reporte():
    params = {
        'b_action': 'cognosViewer', 'ui.action': 'run',
        'ui.object': 'XSSSTART' + escape_cognos(PATH) + 'XSSEND',
        'run.outputFormat': 'HTML', 'run.prompt': 'true',
    }
    return BASE + '?' + urllib.parse.urlencode(params, safe='*')


def decimal(s):
    s = str(s).strip().replace(' ', '').replace('\u00a0', '')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return Decimal(s)


def consultar_stps():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={'width':1440, 'height':1000})
            response = page.goto(url_reporte(), wait_until='domcontentloaded', timeout=90000)
            if not response or response.status != 200:
                raise RuntimeError(f'Cognos HTTP {response.status if response else "sin respuesta"}')
            if 'Error - IBM Cognos' in page.title():
                raise RuntimeError('Cognos devolvió error, no el visor')
            print('Cognos HTTP:', response.status, flush=True)
            years = page.locator('input[type=checkbox]')
            years.first.wait_for(timeout=30000)
            cantidad_anios = datetime.now(timezone.utc).year - 2016 + 1
            if years.count() < cantidad_anios:
                raise RuntimeError(f'Faltan casillas para 2016–{datetime.now(timezone.utc).year}: {years.count()}')
            # Primeras casillas: años descendentes, según el formulario verificado.
            for idx in range(cantidad_anios):
                item = page.locator('input[type=checkbox]').nth(idx)
                if not item.is_checked():
                    item.check(force=True, timeout=15000)
            if page.locator('input[type=checkbox]:checked').count() < cantidad_anios:
                raise RuntimeError('No quedaron seleccionados todos los años')
            selector = page.locator('select').first
            selector.wait_for(timeout=20000)
            # La primera opción es Nacional en el formulario probado.
            entidad = selector.locator('option').first.inner_text().strip()
            if 'nacional' not in entidad.lower():
                raise RuntimeError(f'La opción predeterminada no es Nacional: {entidad}')
            print('Entidad:', entidad, flush=True)
            boton = page.locator("button[onclick*='promptAction']")
            if boton.count() == 0:
                raise RuntimeError('No se encontró el botón Consultar')
            boton.first.click(timeout=25000)
            # Espera basada en que aparezcan meses del reporte; no solo etiquetas del formulario.
            page.wait_for_timeout(8000)
            filas = page.locator('tr').evaluate_all(
                """els => els.map(tr => [...tr.children]
                  .filter(e => e.tagName === 'TD' || e.tagName === 'TH')
                  .map(e => e.innerText.trim()))"""
            )
            print('Filas HTML:', len(filas), flush=True)
        finally:
            browser.close()
    salarios = {}
    auxiliares = 0
    for fila in filas:
        for i, celda in enumerate(fila):
            m = DATE_PATTERN.search(celda)
            if not m:
                continue
            periodo = f'{m.group(1)}-{MONTHS[m.group(2).lower()]:02d}'
            # Estructura verificada: Mes, Total, Agricultura,
            # Extractivas, Transformación, Construcción.
            pos = i + 5
            if pos >= len(fila):
                auxiliares += 1
                continue
            try:
                valor = decimal(fila[pos])
            except (InvalidOperation, ValueError):
                auxiliares += 1
                continue
            if not Decimal('50') < valor < Decimal('5000'):
                auxiliares += 1
                continue
            if periodo in salarios and salarios[periodo] != valor:
                raise RuntimeError(f'Salarios distintos para {periodo}')
            salarios[periodo] = valor
            break
    print('Filas auxiliares ignoradas:', auxiliares, flush=True)
    return salarios


def meses(inicio, fin):
    y, m = map(int, inicio.split('-'))
    yf, mf = map(int, fin.split('-'))
    while (y, m) <= (yf, mf):
        yield f'{y:04d}-{m:02d}'
        m += 1
        if m == 13:
            y += 1
            m = 1


def existentes():
    out = {}
    if SALARIOS.exists():
        with SALARIOS.open(encoding='utf-8-sig', newline='') as f:
            for fila in csv.DictReader(f):
                periodo = fila['periodo'].strip()
                if periodo in out:
                    raise RuntimeError(f'Periodo duplicado en CSV existente: {periodo}')
                out[periodo] = {
                    'periodo': periodo,
                    'sbc_diario_pesos': fila['sbc_diario_pesos'].strip(),
                    'fuente': fila.get('fuente', '').strip() or 'IMSS'
                }
    return out


def escribir_atomico(path, columns, rows):
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8-sig', newline='',
                                     dir=ROOT, delete=False, suffix='.tmp') as f:
        tmp = Path(f.name)
        wr = csv.DictWriter(f, fieldnames=columns)
        wr.writeheader()
        wr.writerows(rows)
    tmp.replace(path)


def main():
    nuevo = consultar_stps()
    if not nuevo:
        raise RuntimeError('Cognos no entregó salarios')
    print('STPS:', min(nuevo), 'a', max(nuevo), '| meses:', len(nuevo), flush=True)
    if '2016-07' not in nuevo or '2026-09' not in nuevo:
        raise RuntimeError('Falta algún mes ancla: 2016-07 o 2026-09')
    for p in meses('2016-07', max(nuevo)):
        if p not in nuevo:
            raise RuntimeError('Falta un mes de STPS: ' + p)
    if abs(nuevo['2026-06'] - Decimal('500.58')) > Decimal('1'):
        raise RuntimeError('Referencia junio 2026 no coincide con construcción')
    anterior = existentes()
    if anterior and max(nuevo) < max(anterior):
        raise RuntimeError('STPS no alcanza el último mes que ya tiene el dashboard')
    combinado = dict(anterior)
    insertados = []
    for periodo, valor in sorted(nuevo.items()):
        if periodo not in combinado:
            insertados.append(periodo)
            combinado[periodo] = {
                'periodo': periodo,
                'sbc_diario_pesos': f'{valor:.2f}',
                'fuente': 'STPS Cognos (IMSS)'
            }
    # Revisar compatibilidad con el dashboard antes de reemplazar el CSV.
    for periodo, fila in combinado.items():
        valor = decimal(fila['sbc_diario_pesos'])
        if not Decimal('50') < valor < Decimal('5000'):
            raise RuntimeError('Salario inválido en ' + periodo)
    orden = sorted(combinado)
    rows = [combinado[k] for k in orden]
    escribir_atomico(SALARIOS, ['periodo', 'sbc_diario_pesos', 'fuente'], rows)
    status = {
        'estado': 'actualizado',
        'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'fuente_nueva': 'STPS Cognos, salario diario construcción',
        'primer_mes': orden[0], 'ultimo_mes': orden[-1],
        'meses_totales': len(orden), 'meses_stps_consultados': len(nuevo),
        'meses_insertados': len(insertados),
        'ultimo_salario_diario': str(decimal(rows[-1]['sbc_diario_pesos'])),
        'ultimo_salario_mensual_30_4': str(
            (decimal(rows[-1]['sbc_diario_pesos']) * Decimal('30.4')).quantize(Decimal('0.01'))
        ),
        'nota': 'El dashboard mensualiza el salario diario multiplicando por 30.4.'
    }
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(status, indent=2, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
