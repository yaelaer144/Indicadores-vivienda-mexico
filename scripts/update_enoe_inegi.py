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
  const normalize = s => (s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/\s+/g,' ').trim().toLowerCase();
  const inputs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
  const info = el => {
    const label = Array.from(document.querySelectorAll('label[for]')).find(l => l.htmlFor === el.id);
    let s = label ? label.textContent : '';
    if (!s) {
      let sib=el.nextSibling;
      for(let i=0; sib && i<4; i++,sib=sib.nextSibling) {
        if(sib.textContent && sib.textContent.trim()) {s=sib.textContent;break;}
      }
    }
    if (!s) s=(el.parentElement?.textContent||'').slice(0,110);
    return normalize(s);
  };
  let touched=[];
  for (const el of inputs) {
    const s=info(el);
    let desired=null;
    if(mode==='variables') {
      if (/^3\.2\. sector de actividad economica/.test(s)) desired=true;
      if (/^poblacion ocupada$/.test(s)) desired=true;
      if (/^3\.1\. posicion en la ocupacion/.test(s)) desired=false;
    } else if (mode==='years') {
      const y = /^20\d{2}$/.test(s) ? Number(s) : (/^20\d{2}$/.test(el.value)?Number(el.value):null);
      if(y!==null && y>=2005 && y<=2099) desired=y>=fromYear;
    }
    if (desired!==null){ el.checked=desired; touched.push([s,desired]); }
  }
  return touched;
}'''


def fetch_live():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        try:
            page = browser.new_page(locale='es-MX', viewport={'width': 1600, 'height': 1000})
            page.set_default_timeout(35000)
            response = page.goto(URL, wait_until='domcontentloaded', timeout=90000)
            if response is None or response.status >= 400:
                raise RuntimeError(f'InfoLaboral no abrió: HTTP {response.status if response else "sin respuesta"}')
            page.locator('#btngind').click()
            page.locator('#btngind_ind').click()
            selected = page.evaluate(SET_CHECKBOXES_JS, {'mode':'variables', 'fromYear':2016})
            if not any('3.2.' in t[0] for t in selected):
                raise RuntimeError('No se pudo identificar la casilla de sector de actividad económica')
            page.locator('#btngind_cob').click()
            selected_years = page.evaluate(SET_CHECKBOXES_JS, {'mode':'years', 'fromYear':2016})
            if not any('2016' in t[0] for t in selected_years):
                raise RuntimeError('No se pudieron seleccionar los años desde 2016')
            # La configuración predeterminada es Nacional / Total / Todos los trimestres / Absolutos.
            # Verificamos los resultados por estructura, cobertura y controles históricos.
            page.locator('#btngind_con').click(timeout=90000)
            page.locator('#reporte1').wait_for(state='attached', timeout=90000)
            content = page.locator('#reporte1').evaluate('(el) => el.outerHTML')
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
