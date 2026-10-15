#!/usr/bin/env python3
import csv, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    data={}
    for p in sorted(ROOT.glob('*.csv')):
        try:
            with p.open(encoding='utf-8-sig',newline='') as f:
                data[p.name]=list(csv.DictReader(f))
        except Exception as e:
            raise RuntimeError(f'No se pudo incorporar {p.name}: {e}')
    (ROOT/'local-data.js').write_text(
        'window.LOCAL_CSV_DATA='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';',
        encoding='utf-8'
    )
if __name__=='__main__': main()
