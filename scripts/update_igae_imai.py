#!/usr/bin/env python3
"""Descarga tabulados IGAE/IMAI con navegador, valida y transforma de forma segura.

El flujo de Playwright requiere validación en GitHub Actions contra el portal real.
Prueba sin red: --local-igae archivo.csv --local-imai archivo.csv
"""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
TABULADOS = {
    'IGAE': 'https://www.inegi.org.mx/app/tabulados/default.aspx?pr=11&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3252&opc=p',
    'IMAI': 'https://www.inegi.org.mx/app/tabulados/default.aspx?pr=10&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3251&opc=p',
}
OUTPUTS = ('igae_construccion_mensual.csv', 'imai_construccion_mensual.csv',
           'imai_construccion_subsectores_mensual.csv')

def descargar(page, which, dest):
    url = TABULADOS[which]
    page.goto(url, wait_until='domcontentloaded', timeout=90000)
    page.wait_for_timeout(3000)
    # La sección "Series Originales" se solicita explícitamente; no seleccionar
    # automáticamente una tabla desestacionalizada si aparece como predeterminada.
    for frame in page.frames:
        candidates = frame.locator('a, button, input[type=button], [role=button]').filter(
            has_text=__import__('re').compile(r'CSV', __import__('re').I))
        alternatives = frame.locator('[title*="CSV"], [aria-label*="CSV"], [value="CSV"]')
        for locator in (candidates, alternatives):
            for i in range(min(locator.count(), 12)):
                el = locator.nth(i)
                if not el.is_visible():
                    continue
                try:
                    with page.expect_download(timeout=45000) as download_info:
                        el.click(timeout=10000)
                    download = download_info.value
                    download.save_as(dest)
                    if dest.stat().st_size < 500:
                        raise RuntimeError('La descarga CSV está vacía')
                    print(f'{which}: descargado {download.suggested_filename} ({dest.stat().st_size} bytes)')
                    return
                except Exception as exc:
                    print(f'{which}: control CSV no produjo descarga: {str(exc)[:160]}', flush=True)
    raise RuntimeError(f'{which}: no se detectó descarga CSV. Revisar selector/interacción del tabulado; se preservan los históricos.')

def get_last(path):
    if not path.exists():
        return None
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows=list(csv.DictReader(f))
    return max((r['periodo'] for r in rows if r.get('periodo')), default=None)

def validate(stage):
    for name in OUTPUTS:
        path=stage/name
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f'No se generó {name}')
        with path.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        periods=[r['periodo'] for r in rows]
        if len(periods)<90 or len(periods)!=len(set(periods)) or periods!=sorted(periods):
            raise RuntimeError(f'Histórico incompleto o duplicado: {name}')
        if periods[0] != '2016-01':
            raise RuntimeError(f'El histórico no inicia en enero de 2016: {name}')
        existing=ROOT/name
        if existing.exists():
            with existing.open(encoding='utf-8-sig', newline='') as f:
                previous_rows={r['periodo']:r for r in csv.DictReader(f)}
            with path.open(encoding='utf-8-sig', newline='') as f:
                current_rows={r['periodo']:r for r in csv.DictReader(f)}
            common=sorted(set(previous_rows)&set(current_rows))[-24:]
            values=[]
            field='indice' if name != 'imai_construccion_subsectores_mensual.csv' else 'construction'
            for period in common:
                try:
                    old=float(previous_rows[period][field]); new=float(current_rows[period][field])
                    if old > 0: values.append(abs(new-old)/old)
                except (KeyError,ValueError,TypeError):
                    continue
            if len(values)>=6 and sorted(values)[len(values)//2] > .02:
                raise RuntimeError(f'{name}: cambios excesivos respecto al histórico; posible serie incorrecta')
        previous=get_last(ROOT/name)
        if previous and periods[-1]<previous:
            raise RuntimeError(f'{name} retrocede de {previous} a {periods[-1]}')
        print(f'{name}: {len(periods)} meses, {periods[0]} a {periods[-1]}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--local-igae',type=Path)
    ap.add_argument('--local-imai',type=Path)
    args=ap.parse_args()
    if bool(args.local_igae) != bool(args.local_imai):
        ap.error('Se necesitan ambos CSV en modo local')
    with tempfile.TemporaryDirectory(prefix='inegi_igae_imai_') as td:
        temp=Path(td)
        if args.local_igae:
            shutil.copy2(args.local_igae,temp/'IGAE.csv')
            shutil.copy2(args.local_imai,temp/'IMAI.csv')
            metodo='prueba_local'
        else:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True, args=['--no-sandbox'])
                context=browser.new_context(accept_downloads=True, locale='es-MX')
                page=context.new_page()
                for which in ('IGAE','IMAI'):
                    descargar(page,which,temp/f'{which}.csv')
                browser.close()
            metodo='playwright_tabulados'
        subprocess.run([sys.executable,str(ROOT/'prepare_igae_imai.py'),
                        str(temp/'IGAE.csv'),str(temp/'IMAI.csv'),str(temp)],check=True)
        validate(temp)
        # El transformador produjo todas las salidas; solo entonces reemplazarlas.
        for name in OUTPUTS:
            os.replace(temp/name, ROOT/name)
        status={'fecha_utc':datetime.now(timezone.utc).isoformat(),
                'resultado':'ok','metodo':metodo,
                'fuentes':TABULADOS,
                'ultimo_igae':get_last(ROOT/OUTPUTS[0]),
                'ultimo_imai':get_last(ROOT/OUTPUTS[1])}
        (ROOT/'igae_imai_update_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Actualización verificada: archivos generados correctamente')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
