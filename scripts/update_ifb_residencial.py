
#!/usr/bin/env python3
"""Descarga y valida IMFBCF residencial, serie original, base 2018=100."""

import argparse
import csv
import io
import json
import re
import statistics
import urllib.parse
import urllib.request
import zipfile
import http.cookiejar
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

URL = (
    "https://www.inegi.org.mx/app/tabulados/default.aspx"
    "?pr=13&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3253&opc=p"
)

MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3,
    "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12
}


class Form(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.cur = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)

        if tag == "form":
            self.cur = {
                "action": a.get("action", ""),
                "fields": {}
            }
            self.forms.append(self.cur)

        if tag == "input" and self.cur is not None:
            n = a.get("name")
            t = a.get("type", "text").lower()

            if n and t not in (
                "submit", "button", "image", "file", "reset"
            ) and (
                t not in ("checkbox", "radio") or "checked" in a
            ):
                self.cur["fields"][n] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.cur = None


def download_xlsx():
    """Descarga XLSX oficial mediante formulario ASP.NET."""

    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(
            http.cookiejar.CookieJar()
        )
    )

    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Dashboard-IFB/1.0)",
        "Accept-Language": "es-MX,es;q=0.9"
    }

    with opener.open(
        urllib.request.Request(URL, headers=headers),
        timeout=90
    ) as resp:
        html = resp.read(6_000_000).decode("utf-8", "replace")
        page = resp.url

    parser = Form()
    parser.feed(html)

    form = next(
        (
            f for f in parser.forms
            if "__VIEWSTATE" in f["fields"]
            and "__EVENTVALIDATION" in f["fields"]
        ),
        None
    )

    if not form:
        raise ValueError(
            "INEGI no entregó formulario ASP.NET completo"
        )

    fields = dict(form["fields"])
    fields["downloadjson_to_Xlsx"] = "Descarga Excel"

    req = urllib.request.Request(
        urllib.parse.urljoin(page, form["action"] or page),
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            **headers,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": page,
            "Origin": "https://www.inegi.org.mx"
        },
        method="POST"
    )

    with opener.open(req, timeout=180) as resp:
        typ = resp.headers.get("Content-Type", "")
        raw = resp.read(30_000_001)

    print(
        f"POST INEGI IFB: Content-Type={typ}; bytes={len(raw)}"
    )

    if len(raw) > 30_000_000 or not zipfile.is_zipfile(
        io.BytesIO(raw)
    ):
        raise ValueError("INEGI no devolvió archivo XLSX válido")

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if (
            "[Content_Types].xml" not in z.namelist()
            or "xl/workbook.xml" not in z.namelist()
        ):
            raise ValueError("Respuesta ZIP no es un XLSX")

    return raw


def xlsx_to_csvtext(raw):
    """Extrae la tabla Excel sin depender de openpyxl."""

    N = {
        "m": (
            "http://schemas.openxmlformats.org/"
            "spreadsheetml/2006/main"
        )
    }

    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        shared = []

        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))

            for si in root.findall("m:si", N):
                shared.append(
                    "".join(
                        (t.text or "")
                        for t in si.findall(".//m:t", N)
                    )
                )

        sheets = sorted(
            (
                n for n in z.namelist()
                if re.fullmatch(
                    r"xl/worksheets/sheet\d+\.xml", n
                )
            ),
            key=lambda x: int(
                re.search(r"sheet(\d+)", x).group(1)
            )
        )

        for sheet in sheets:
            root = ET.fromstring(z.read(sheet))
            grid = []

            for row in root.findall(
                ".//m:sheetData/m:row", N
            ):
                cells = {}

                for c in row.findall("m:c", N):
                    ref = c.attrib.get("r", "")
                    col = re.match("[A-Z]+", ref)

                    if not col:
                        continue

                    ci = 0
                    for ch in col.group(0):
                        ci = ci * 26 + ord(ch) - 64

                    v = c.find("m:v", N)
                    inline = c.find("m:is", N)

                    if v is not None:
                        val = v.text or ""
                    elif inline is not None:
                        val = "".join(
                            t.text or ""
                            for t in inline.findall(".//m:t", N)
                        )
                    else:
                        val = ""

                    if c.attrib.get("t") == "s" and val:
                        val = shared[int(val)]

                    if val != "":
                        cells[ci - 1] = val

                if cells:
                    grid.append(cells)

            if not any(
                any(
                    "Índice de volumen físico" in v
                    for v in r.values()
                )
                for r in grid
            ):
                continue

            top = next(
                (
                    i for i, r in enumerate(grid)
                    if str(r.get(0, "")).strip() == "Concepto"
                ),
                None
            )

            if top is None:
                continue

            hdr = grid[top]
            nextrow = (
                grid[top + 1]
                if top + 1 < len(grid)
                else {}
            )

            col_labels = {}
            last_year = None

            for col in range(
                1,
                max(max(r.keys()) for r in grid) + 1
            ):
                a = str(hdr.get(col, "")).strip()
                b = str(nextrow.get(col, "")).strip()

                if re.fullmatch(r"20\d{2}|19\d{2}", a):
                    last_year = int(a)

                combined = re.match(
                    r"^(19\d{2}|20\d{2})\s*\|\s*"
                    r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)",
                    a
                )

                if combined:
                    col_labels[col] = (
                        f"{combined[1]} | {combined[2]}"
                    )
                    continue

                month = (
                    b if b.lower() in MONTHS
                    else a if a.lower() in MONTHS
                    else ""
                )

                if month and last_year:
                    col_labels[col] = (
                        f"{last_year} | {month}"
                    )

            if not col_labels:
                continue

            out = io.StringIO()
            writer = csv.writer(out)
            cols = sorted(col_labels)

            writer.writerow(
                ["Concepto"]
                + [col_labels[c] for c in cols]
            )

            for row in grid[top + 1:]:
                writer.writerow(
                    [row.get(0, "")]
                    + [row.get(c, "") for c in cols]
                )

            result = out.getvalue()

            if "Residencial" in result:
                return result

    raise ValueError(
        "No se identificó tabla IFB residencial en el XLSX"
    )


def _check_months(data):
    keys = sorted(data)

    if not keys:
        raise ValueError("No se encontraron meses válidos")

    for a, b in zip(keys, keys[1:]):
        ya, ma = map(int, a.split("-"))
        yb, mb = map(int, b.split("-"))

        if (yb * 12 + mb) - (ya * 12 + ma) != 1:
            raise ValueError(
                f"Hueco temporal entre {a} y {b}"
            )

    return keys


def parse(csvtext):
    """Extrae los meses del tabulado oficial."""

    rows = list(csv.reader(io.StringIO(csvtext)))

    if len(rows) < 7:
        raise ValueError("Archivo sin estructura INEGI")

    heads = rows[0]

    if "Concepto" not in heads[0]:
        raise ValueError(
            "Encabezado Concepto no encontrado"
        )

    section = next(
        (
            i for i, r in enumerate(rows)
            if r
            and "Índice de volumen físico" in r[0]
            and "2018" in r[0]
        ),
        None
    )

    if section is None:
        raise ValueError(
            "No se encontró índice de volumen físico base 2018"
        )

    origin = next(
        (
            i for i in range(section + 1, len(rows))
            if rows[i]
            and rows[i][0].strip()
            == "Por tipo de bien y origen"
        ),
        None
    )

    if origin is None:
        raise ValueError(
            "No se encontró desagregación por tipo de bien"
        )

    residential = next(
        (
            i for i in range(
                origin + 1,
                min(origin + 14, len(rows))
            )
            if rows[i]
            and rows[i][0].strip() == "Residencial"
        ),
        None
    )

    if residential is None:
        raise ValueError(
            "No se encontró Construcción → Residencial"
        )

    if not any(
        rows[i]
        and rows[i][0].strip() == "Construcción"
        for i in range(origin + 1, residential)
    ):
        raise ValueError(
            "Residencial no pertenece a Construcción"
        )

    data = {}

    for col, label in enumerate(heads[1:], 1):
        m = re.match(
            r"^\s*(\d{4})\s*\|\s*"
            r"([A-Za-zÁÉÍÓÚáéíóúñÑ]+)"
            r"(?:\s+[PR])?\s*$",
            str(label)
        )

        if not m:
            continue

        year = int(m[1])
        mon = MONTHS.get(m[2].lower())

        if not mon or year < 2016:
            continue

        val = (
            rows[residential][col]
            if col < len(rows[residential])
            else ""
        ).strip().replace(",", "")

        if not val or val in (
            "N/D", "NA", "-", "..."
        ):
            continue

        v = float(val)

        if not 0 < v < 1000:
            raise ValueError(
                f"Índice fuera de rango {label}: {v}"
            )

        data[f"{year:04d}-{mon:02d}"] = v

    if len(data) < 24:
        raise ValueError(
            f"INEGI entregó muy pocos meses: {len(data)}"
        )

    _check_months(data)
    return data


def _historico_anterior(path):
    if not path.exists():
        return {}

    with path.open(
        encoding="utf-8-sig",
        newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    data = {
        r["periodo"]: float(r["indice"])
        for r in rows
        if r.get("periodo") and r.get("indice")
    }

    if data:
        _check_months(data)

    return data


def integrar(descarga, previo):
    """Integra descarga e histórico sin inventar valores."""

    if not previo:
        integrado = dict(descarga)

        if min(integrado) > "2016-01":
            raise ValueError(
                "Sin histórico previo desde 2016; no se publica"
            )

    else:
        if max(descarga) < max(previo):
            raise ValueError(
                "La descarga es más antigua que el CSV; "
                "no se publica"
            )

        comunes = set(descarga) & set(previo)

        if len(comunes) < 12:
            raise ValueError(
                "Traslape insuficiente con el histórico"
            )

        divergencias = [
            p for p in comunes
            if abs(descarga[p] / previo[p] - 1) > 0.20
        ]

        if divergencias:
            raise ValueError(
                "Datos incompatibles con histórico: "
                + str(divergencias[:5])
            )

        integrado = {**previo, **descarga}

    keys = _check_months(integrado)

    if keys[0] > "2016-01" or len(keys) < 96:
        raise ValueError(
            "Histórico incompleto tras integrar: "
            f"{keys[0]} a {keys[-1]}"
        )

    vals2018 = [
        v for p, v in integrado.items()
        if p.startswith("2018-")
    ]

    if (
        len(vals2018) != 12
        or not (
            98 <= statistics.mean(vals2018) <= 102
        )
    ):
        raise ValueError(
            "Base 2018 no validada: promedio distinto de 100"
        )

    out = []

    for idx, p in enumerate(keys):
        v = integrado[p]

        mom = (
            (v / integrado[keys[idx - 1]] - 1) * 100
            if idx >= 1 else None
        )

        yoy = (
            (v / integrado[keys[idx - 12]] - 1) * 100
            if idx >= 12 else None
        )

        out.append({
            "periodo": p,
            "indice": f"{v:.8f}".rstrip("0").rstrip("."),
            "variacion_mensual": (
                f"{mom:.3f}" if mom is not None else ""
            ),
            "variacion_anual": (
                f"{yoy:.3f}" if yoy is not None else ""
            )
        })

    print(
        f"INEGI descargó {len(descarga)} meses "
        f"({min(descarga)} a {max(descarga)}). "
        f"Histórico integrado: {len(out)} meses "
        f"({keys[0]} a {keys[-1]})"
    )

    return out


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--input",
        type=Path,
        help="CSV o XLSX oficial local, solo para pruebas"
    )

    args = ap.parse_args()

    if args.input:
        if args.input.suffix.lower() == ".xlsx":
            content = xlsx_to_csvtext(
                args.input.read_bytes()
            )
        else:
            content = args.input.read_text(
                encoding="utf-8-sig"
            )
    else:
        content = xlsx_to_csvtext(
            download_xlsx()
        )


descarga = parse(content)
old = ROOT / "ifb_residencial_mensual.csv"

previo = _historico_anterior(old)

print(
    f"Descarga INEGI: {min(descarga)} a {max(descarga)}; "
    f"{len(descarga)} meses"
)

if previo:
    print(
        f"Histórico del dashboard: {min(previo)} a {max(previo)}; "
        f"{len(previo)} meses"
    )

if previo and max(descarga) < max(previo):
    print(
        "SIN CAMBIOS: INEGI devolvió una serie más antigua "
        "que el histórico del dashboard. "
        "Se conservan los datos existentes."
    )
    return

rows = integrar(descarga, previo)


    tmp = old.with_suffix(".csv.tmp")

    with tmp.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "periodo",
                "indice",
                "variacion_mensual",
                "variacion_anual"
            ]
        )

        writer.writeheader()
        writer.writerows(rows)

    tmp.replace(old)

    status = {
        "estado": "actualizado",
        "fuente": URL,
        "serie": "original",
        "base": 2018,
        "inicio": rows[0]["periodo"],
        "ultimo": rows[-1]["periodo"],
        "observaciones": len(rows),
        "observaciones_descarga": len(descarga),
        "fecha_consulta_utc": (
            datetime.now(timezone.utc).isoformat()
        )
    }

    (
        ROOT / "ifb_residencial_update_status.json"
    ).write_text(
        json.dumps(
            status,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    print(
        f"IFB residencial validado: "
        f"{status['inicio']} a {status['ultimo']}; "
        f"{len(rows)} meses; "
        f"índice último={rows[-1]['indice']}"
    )


if __name__ == "__main__":
    main()
