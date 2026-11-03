
#!/usr/bin/env python3
"""Descarga ENOE desde InfoLaboral usando una sesión nueva de navegador.

No requiere archivos XLS manuales ni IDs del Banco de Indicadores.
La tabla HTML 'reporte1' se valida antes de reemplazar el CSV (miles de personas).
Requiere playwright y beautifulsoup4, instalados en update-quarterly.yml.
"""
import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'enoe_construccion_trimestral.csv'
STATUS = ROOT / 'enoe_update_status.json'
URL = 'https://www.inegi.org.mx/sistemas/infoenoe/Default_15mas.aspx'


def read_existing():
    if not OUT.exists():
        return []
    with OUT.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def parse_table(html):
    """Acepta tanto HTML completo como respuesta parcial ASP.NET UpdatePanel."""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='reporte1')
    if table is None:
        raise ValueError('No se encontró reporte1 en respuesta del INEGI')
    rows = [[c.get_text(' ', strip=True).replace('\xa0', ' ') for c in tr.find_all(['td','th'], recursive=False)]
            for tr in table.find_all('tr')]
    header_idx = next((i for i, cells in enumerate(rows) if cells and cells[0] == 'Indicadores'), None)
    if header_idx is None or header_idx + 2 >= len(rows):
        raise ValueError('Cabeceras de años y trimestres no reconocidas')
    years, quarters = rows[header_idx], rows[header_idx+1]
    labels = {"Primer trimestre": 1, "Segundo trimestre": 2, "Tercer trimestre": 3, "Cuarto trimestre": 4}
    periods = []
    for year, quarter in zip(years[1:], quarters[1:]):
        if not re.fullmatch(r'20\d{2}', year) or quarter not in labels:
            raise ValueError(f'Cabecera no reconocida: {year!r}, {quarter!r}')
        periods.append(f'{year}-T{labels[quarter]}')
    if len(set(periods)) != len(periods) or periods != sorted(periods):
        raise ValueError('Los trimestres están repetidos o desordenados')

    def find_row(label):
        matches = [r for r in rows[header_idx+3:] if len(r) == len(periods)+1 and r[0].strip() == label]
        if len(matches) != 1:
            raise ValueError(f'Se esperó una sola fila {label}: {len(matches)}')
        values = {}
        for p, value in zip(periods, matches[0][1:]):
            n = value.replace(',', '').replace(' ', '')
            if not re.fullmatch(r'\d+', n):
                raise ValueError(f'Valor ENOE no numérico: {label} {p} = {value!r}')
            values[p] = int(n)
        return values

    national = find_row('Población ocupada')
    construction = find_row('Construcción')
    if len(periods) < 35 or periods[0] != '2016-T1' or '2020-T2' in periods:
        raise ValueError('La consulta no cubre 2016 o incluye incorrectamente 2020-T2')
    for p in periods:
        if not 30_000_000 <= national[p] <= 100_000_000:
            raise ValueError(f'Población ocupada nacional fuera de rango en {p}')
        if not 1_000_000 <= construction[p] <= 12_000_000 or construction[p] >= national[p]:
            raise ValueError(f'Construcción fuera de rango en {p}')
    if national['2016-T1'] != 50_029_049 or construction['2016-T1'] != 4_074_858:
        raise ValueError('No coincide con valores de control 2016-T1')
    return [{ 'periodo': p, 'total': f'{construction[p]/1000:.3f}',
              'ocupada_total': f'{national[p]/1000:.3f}', 'formal': '', 'informal': '' }
            for p in periods]


# Función sin dependencias de selectores ASP.NET variables.
# La página usa <label for="id"> o input + texto dentro de una celda.
SET_CHECKBOXES_JS = r'''({mode, fromYear}) => {
  const normalize = s => (s || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  const getLabel = el => {
    const associated = Array.from(document.querySelectorAll('label[for]')).find(l => l.htmlFor === el.id);
    if (associated && associated.textContent.trim()) return normalize(associated.textContent);
    let node = el.nextSibling;
    for (let i=0; node && i<5; i++,node=node.nextSibling) {
      if (node.textContent && node.textContent.trim()) return normalize(node.textContent);
    }
    return normalize(el.parentElement?.textContent || '');
  };
  const updated = [];
  const found = [];
  for (const el of inputs) {
    const label = getLabel(el);
    const value = (el.value || '').trim();
    let desired = null;
    let year = null;
    if (mode === 'variables') {
      if (/^3\.2\. sector de actividad economica/.test(label)) desired = true;
      if (/^poblacion ocupada$/.test(label)) desired = true;
      if (/^3\.1\. posicion en la ocupacion/.test(label)) desired = false;
    } else if (mode === 'years') {
      // ASP.NET puede presentar los años en el atributo value SIN texto de etiqueta.
      const fromValue = /^20\d{2}$/.test(value) ? Number(value) : null;
      const fromLabel = /^20\d{2}$/.test(label) ? Number(label) : null;
      year = fromValue !== null ? fromValue : fromLabel;
      if (year !== null && year >= 2005 && year <= 2099) desired = year >= fromYear;
    }
    if (desired !== null) {
      if (el.checked !== desired) {
        el.checked = desired;
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
      }
      updated.push({label, value, year, checked:el.checked, desired, id:el.id});
    }
    if (mode === 'years' && year !== null) found.push(year);
  }
  return {updated, yearsFound: found, checkboxCount: inputs.length};
}'''



def fetch_live():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox']
        )

        try:
            page = browser.new_page(
                locale='es-MX',
                viewport={'width': 1600, 'height': 1000}
            )
            page.set_default_timeout(35000)

            response = page.goto(
                URL,
                wait_until='domcontentloaded',
                timeout=90000
            )

            if response is None or response.status >= 400:
                raise RuntimeError(
                    f'InfoLaboral no abrió: HTTP '
                    f'{response.status if response else "sin respuesta"}'
                )

            # 1. Abrir los indicadores estratégicos.
            page.locator('#btngind').click()

            # 2. Seleccionar variables.
            page.locator('#btngind_ind').click()

            # Esperar a que ASP.NET termine de mostrar Variables.
            page.get_by_text(
                '3.2. Sector de actividad económica',
                exact=True
            ).wait_for(state='visible', timeout=60000)

            selected = page.evaluate(
                SET_CHECKBOXES_JS,
                {'mode': 'variables', 'fromYear': 2016}
            )

            if not any(
                '3.2.' in t['label'] and t['checked']
                for t in selected['updated']
            ):
                raise RuntimeError(
                    'No se pudo seleccionar sector de actividad económica'
                )

            print(
                'ENOE: variables seleccionadas correctamente',
                flush=True
            )

            # 3. Abrir Coberturas y sexo.
            page.locator('#btngind_cob').click()

            # IMPORTANTE:
            # InfoLaboral usa ASP.NET UpdatePanel.
            # Esperar a que termine la actualización parcial.
            page.get_by_text(
                'Cobertura temporal',
                exact=True
            ).wait_for(state='visible', timeout=60000)

            page.get_by_text(
                '2016',
                exact=True
            ).first.wait_for(state='visible', timeout=60000)

            print(
                'ENOE: sección Coberturas y sexo cargada',
                flush=True
            )

            # 4. Seleccionar años desde 2016.
            selected_years = page.evaluate(
                SET_CHECKBOXES_JS,
                {'mode': 'years', 'fromYear': 2016}
            )

            years_ok = any(
                t['year'] == 2016 and t['checked']
                for t in selected_years['updated']
            )

            print(
                'ENOE selección de años: ' + json.dumps(
                    {
                        'casillas': selected_years['checkboxCount'],
                        'años_detectados': selected_years['yearsFound'],
                        'años_marcados': [
                            t['year']
                            for t in selected_years['updated']
                            if t['checked']
                        ],
                    },
                    ensure_ascii=False
                ),
                flush=True
            )

            if not years_ok:
                raise RuntimeError(
                    'No se pudo marcar 2016. Diagnóstico: ' +
                    json.dumps(
                        selected_years,
                        ensure_ascii=False
                    )[:2500]
                )

            # 5. Ejecutar la consulta.
            page.locator('#btngind_con').click(timeout=90000)

            # Esperar a que aparezca la tabla oficial.
            page.locator('#reporte1').wait_for(
                state='attached',
                timeout=90000
            )

            # 6. Extraer directamente la tabla.
            content = page.locator('#reporte1').evaluate(
                '(el) => el.outerHTML'
            )

            return parse_table(content)

        finally:
            browser.close()



def main():
    status = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'source': 'INEGI ENOE InfoLaboral (consulta automática HTML)',
              'units': 'miles de personas', 'updated': False}
    try:
        rows = fetch_live()
        previous = read_existing()
        last_old = max((r.get('periodo','') for r in previous), default='')
        if rows[-1]['periodo'] < last_old:
            raise ValueError(f'Fuente retrocedió de {last_old} a {rows[-1]["periodo"]}')
        # No convertir una posible caída del sitio en un borrado de los datos existentes.
        old_map = {r['periodo']:r for r in previous}
        for row in rows:
            old = old_map.get(row['periodo'])
            if old:
                for field in ('formal', 'informal'):
                    row[field] = old.get(field,'')
        tmp = OUT.with_suffix('.csv.tmp')
        with tmp.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['periodo','total','ocupada_total','formal','informal'])
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(OUT)
        status.update(updated=True, first_quarter=rows[0]['periodo'], last_quarter=rows[-1]['periodo'],
                      observations=len(rows), gap_2020_T2=True)
        print(f'ENOE automática: {rows[0]["periodo"]} a {rows[-1]["periodo"]}; {len(rows)} observaciones')
    except Exception as exc:
        status['error'] = str(exc)
        print(f'ERROR ENOE InfoLaboral: {exc}', flush=True)
        raise
    finally:
        STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')


if __name__ == '__main__':
    main()
