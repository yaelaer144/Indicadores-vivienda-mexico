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
    import re
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    url = TABULADOS[which]
    respuestas = []
    descargas = []

    def registrar_respuesta(response):
        headers = response.headers
        content_type = headers.get("content-type", "")
        disposition = headers.get("content-disposition", "")

        if (
            "csv" in content_type.lower()
            or "attachment" in disposition.lower()
            or ".csv" in response.url.lower()
        ):
            respuestas.append(response)

    def registrar_descarga(download):
        descargas.append(download)

    page.on("response", registrar_respuesta)
    page.on("download", registrar_descarga)

    try:
        respuesta = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=90000
        )

        page.wait_for_timeout(5000)

        print(
            f"{which}: HTTP "
            f"{respuesta.status if respuesta else 'sin respuesta'}"
        )

        print(f"{which}: página = {page.title()}")

        if respuesta and respuesta.status != 200:
            raise RuntimeError(
                f"{which}: error HTTP {respuesta.status}"
            )

        

        controles = []

        for frame in page.frames:
            locator = frame.locator(
                'button, a, input, [role="button"], '
                '[title], [aria-label]'
            )

            for i in range(min(locator.count(), 200)):
                elemento = locator.nth(i)

                try:
                    if not elemento.is_visible():
                        continue

                    atributos = [
                        elemento.inner_text(timeout=1000),
                        elemento.get_attribute("title"),
                        elemento.get_attribute("aria-label"),
                        elemento.get_attribute("value")
                    ]

                    nombre = " ".join(
                        str(x) for x in atributos if x
                    )

                    if re.search(
                        r"(descarga\s*)?csv",
                        nombre,
                        re.IGNORECASE
                    ):
                        print(
                            f"{which}: control encontrado: "
                            f"{nombre[:150]}"
                        )
                        controles.append(elemento)

                except Exception as exc:
                    print(
                        f"{which}: error examinando control: {exc}"
                    )


        for frame in page.frames:
            elementos = frame.locator(selector)

            for i in range(min(elementos.count(), 300)):
                elemento = elementos.nth(i)

                try:
                    if not elemento.is_visible():
                        continue

                    texto = " ".join([
                        elemento.inner_text(timeout=1000) or "",
                        elemento.get_attribute("title") or "",
                        elemento.get_attribute("value") or "",
                        elemento.get_attribute("aria-label") or ""
                    ])

                    if re.search(
                        r"descarga\s*csv|csv",
                        texto,
                        re.IGNORECASE
                    ):
                        controles.append(elemento)
                        print(
                            f"{which}: control encontrado: "
                            f"{texto[:150]}"
                        )

                except Exception:
                    continue

        print(
            f"{which}: controles CSV visibles = "
            f"{len(controles)}"
        )

        if not controles:
            raise RuntimeError(
                f"{which}: no se encontró un control CSV visible"
            )

        for numero, control in enumerate(controles, 1):
            try:
                print(
                    f"{which}: probando control CSV {numero}"
                )

                control.click(timeout=10000)
                page.wait_for_timeout(12000)

                for download in descargas:
                    try:
                        download.save_as(dest)

                        if dest.stat().st_size >= 500:
                            print(
                                f"{which}: descarga de navegador correcta"
                            )
                            return
                    except Exception as exc:
                        print(
                            f"{which}: error al guardar descarga: "
                            f"{exc}"
                        )

                for response in respuestas:
                    try:
                        if response.status != 200:
                            continue

                        body = response.body()

                        if len(body) < 500:
                            continue

                        encabezado = body[:300].lower()

                        if b"<html" in encabezado:
                            continue

                        if not (
                            b"," in encabezado
                            or b";" in encabezado
                        ):
                            continue

                        dest.write_bytes(body)

                        print(
                            f"{which}: CSV recibido mediante HTTP "
                            f"({len(body)} bytes)"
                        )
                        return

                    except Exception as exc:
                        print(
                            f"{which}: respuesta no utilizable: "
                            f"{exc}"
                        )

            except PlaywrightTimeout:
                print(
                    f"{which}: tiempo agotado al pulsar CSV"
                )

            except Exception as exc:
                print(
                    f"{which}: error del control: {exc}"
                )

        raise RuntimeError(
            f"{which}: no se obtuvo CSV válido. "
            "Revisar interacción del tabulado, "
            "selección de series y posible reCAPTCHA."
        )

    finally:
        page.remove_listener(
            "response", registrar_respuesta
        )
        page.remove_listener(
            "download", registrar_descarga
        )


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
