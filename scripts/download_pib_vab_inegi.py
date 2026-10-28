#!/usr/bin/env python3
"""Prueba de descarga XLSX del tabulado INEGI mediante formulario ASP.NET.
No se ha validado aún contra el servidor en GitHub Actions.
"""
import argparse
import http.cookiejar
import io
import urllib.parse
import urllib.request
import zipfile
from html.parser import HTMLParser
from pathlib import Path

URL = 'https://www.inegi.org.mx/app/tabulados/default.aspx?pr=20&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3257&opc=p'

class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.current = None
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'form':
            self.current = {'action': a.get('action', ''), 'method': a.get('method', 'GET'), 'fields': {}}
            self.forms.append(self.current)
        elif tag == 'input' and self.current is not None:
            name = a.get('name')
            typ = a.get('type', 'text').lower()
            if name and typ not in ('submit', 'button', 'image', 'file', 'reset'):
                if typ not in ('checkbox','radio') or 'checked' in a:
                    self.current['fields'][name] = a.get('value', '')
    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None

def download(output):
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    headers = {'User-Agent':'Mozilla/5.0 (compatible; INEGI-PIBT-dashboard/1.0)', 'Accept-Language':'es-MX,es;q=0.9'}
    req = urllib.request.Request(URL, headers=headers)
    with opener.open(req, timeout=60) as response:
        raw = response.read(5_000_000)
        html = raw.decode('utf-8', errors='replace')
        final_url = response.url
    parser = FormParser()
    parser.feed(html)
    form = next((f for f in parser.forms if '__VIEWSTATE' in f['fields']), None)
    if not form:
        raise ValueError('No se encontró formulario ASP.NET con __VIEWSTATE; es posible que INEGI haya cambiado su página o entregue una versión distinta.')
    fields = form['fields']
    if '__EVENTVALIDATION' not in fields:
        raise ValueError('No se encontró __EVENTVALIDATION; no se realizará un POST incompleto.')
    fields['downloadjson_to_Xlsx'] = 'Descarga Excel'
    post_url = urllib.parse.urljoin(final_url, form['action'] or final_url)
    body = urllib.parse.urlencode(fields).encode('utf-8')
    post_headers = dict(headers)
    post_headers.update({'Content-Type':'application/x-www-form-urlencoded', 'Referer': final_url, 'Origin': 'https://www.inegi.org.mx'})
    with opener.open(urllib.request.Request(post_url, data=body, headers=post_headers, method='POST'), timeout=120) as response:
        content_type = response.headers.get('Content-Type','')
        data = response.read(25_000_001)
        print(f'POST INEGI: HTTP {response.status}; tipo={content_type}; bytes={len(data)}')
    if len(data)>25_000_000: raise ValueError('Descarga mayor a 25 MB')
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise ValueError('La respuesta NO es XLSX: puede ser HTML, bloqueo o error de formulario. Se conserva el CSV anterior.')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names=set(z.namelist())
        if '[Content_Types].xml' not in names or 'xl/workbook.xml' not in names:
            raise ValueError('El ZIP recibido no es un XLSX válido')
    output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_suffix(output.suffix+'.tmp')
    tmp.write_bytes(data)
    tmp.replace(output)
    print(f'XLSX INEGI descargado: {output}')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path,default=Path('PIBT_actualizado.xlsx'))
    args=p.parse_args()
    download(args.output)
