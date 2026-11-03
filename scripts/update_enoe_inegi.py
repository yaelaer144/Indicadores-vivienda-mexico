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
