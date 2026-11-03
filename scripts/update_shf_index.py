
#!/usr/bin/env python3
"""Índice SHF nacional (base 2017=100).

Consulta documentos oficiales PDF/XLSX, extrae la fila Nacional,
conserva el histórico y calcula la variación porcentual anual.
"""

import csv
import io
import json
import re
import sys
import unicodedata

from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

LEVEL = ROOT / "shf_indice_nivel_trimestral.csv"
YOY = ROOT / "shf_indice_trimestral.csv"
STATUS = ROOT / "shf_update_status.json"

PAGES = [
    "https://www.gob.mx/shf/documentos/"
    "indice-shf-de-precios-de-la-vivienda-en-mexico-2025-a-2026",

    "https://www.gob.mx/shf/documentos/"
    "indice-shf-de-precios-de-la-vivienda-en-mexico-2020-2024",

    "https://www.gob.mx/shf/documentos/"
    "indice-shf-de-precios-de-la-vivienda-en-mexico-2015-a-2019",
]

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
)

SEED = {
    "2015-T1": 82.6, "2015-T2": 85.6,
    "2015-T3": 88.2, "2015-T4": 89.4,
    "2016-T1": 90.5, "2016-T2": 92.2,
    "2016-T3": 93.6, "2016-T4": 94.6,
    "2017-T1": 97.1, "2017-T2": 99.1,
    "2017-T3": 101.0, "2017-T4": 102.7,
    "2018-T1": 105.4, "2018-T2": 107.7,
    "2018-T3": 110.1, "2018-T4": 112.4,
    "2019-T1": 115.0, "2019-T2": 117.6,
    "2019-T3": 119.4, "2019-T4": 121.0,
}


def normal(s):
    return (
        unicodedata.normalize("NFKD", str(s or ""))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def fetch(url):
    request = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "*/*",
        },
    )

    with urlopen(request, timeout=70) as response:
        return (
            response.read(),
            response.geturl(),
            response.headers.get("Content-Type", ""),
        )


def quarter(x):
    s = normal(x).upper().strip().replace(" ", "")

    return {
        "I": 1, "II": 2, "III": 3, "IV": 4,
        "1": 1, "2": 2, "3": 3, "4": 4,
        "T1": 1, "T2": 2, "T3": 3, "T4": 4,
    }.get(s)


def official_links(page_html, base):
    """Busca anexos oficiales y devuelve únicamente URLs completas."""

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(page_html, "html.parser")
    candidates = {}

    for a in soup.find_all("a", href=True):

        href = unescape(
            str(a.get("href") or "")
        ).strip()

        if not href or href.startswith(
            ("#", "javascript:", "mailto:")
        ):
            continue

        url = urljoin(base, href)
        parsed = urlparse(url)

        host = (parsed.hostname or "").lower()

        if parsed.scheme not in ("http", "https"):
            continue

        if not (
            host == "gob.mx"
            or host.endswith(".gob.mx")
        ):
            continue

        path = parsed.path.lower()

        if not any(
            x in path
            for x in (
                "/cms/uploads/attachment/",
                "/download",
                ".pdf",
                ".xlsx",
                ".xls",
            )
        ):
            continue

        parent_text = (
            a.parent.get_text(" ", strip=True)[:450]
            if a.parent
            else ""
        )

        context = " ".join(
            (
                a.get_text(" ", strip=True),
                parent_text,
            )
        )

        norm = normal(context)

        score = (
            (10 if "datos abiertos" in norm else 0)
            + (6 if path.endswith(".pdf") else 0)
            + (
                3
                if path.endswith((".xlsx", ".xls"))
                else 0
            )
            + (1 if "indice" in norm else 0)
        )

        if url not in candidates:
            candidates[url] = (
                score,
                len(candidates),
            )
        else:
            old_score, pos = candidates[url]
            candidates[url] = (
                max(score, old_score),
                pos,
            )

    ordered = sorted(
        candidates.items(),
        key=lambda item: (
            -item[1][0],
            item[1][1],
        ),
    )

    # Corrección: regresar la URL, no la puntuación.
    return [
        url
        for url, _ in ordered
    ]



def parse_excel(blob):
    """Lee Excel SHF horizontal, vertical o con encabezados fusionados.

    Si los encabezados no permiten asignar los periodos, utiliza
    coincidencias verificadas con el índice histórico nacional.
    """
    import openpyxl

    wb = openpyxl.load_workbook(
        io.BytesIO(blob),
        data_only=True,
        read_only=False
    )

    candidates = []
    diagnostics = []

    anchors = dict(SEED)

    # Valores de control oficiales de 2025 y 2026.
    anchors.update({
        "2025-T1": 186.9,
        "2025-T2": 191.9,
        "2025-T3": 195.9,
        "2025-T4": 199.0,
        "2026-T1": 202.9,
        "2026-T2": 205.9,
    })

    def num(value):
        if isinstance(value, bool) or value is None:
            return None

        try:
            v = float(
                str(value).replace(",", "").strip()
            )

            return v if 50 <= v <= 700 else None

        except (TypeError, ValueError):
            return None

    def year(value):
        s = str(value or "").strip()

        match = re.fullmatch(
            r"(20(?:0\d|1\d|2\d|3\d))(?:\.0)?",
            s
        )

        return int(match.group(1)) if match else None

    def periods_between(start, n):
        y, q = map(
            int,
            start.replace("-T", "-").split("-")
        )

        output = []

        for _ in range(n):
            output.append(f"{y}-T{q}")
            q += 1

            if q == 5:
                q = 1
                y += 1

        return output

    def put(candidate, method, sheet):
        if len(candidate) < 6:
            return

        overlaps = [
            p for p in candidate
            if p in anchors
        ]

        matching = [
            p for p in overlaps
            if abs(candidate[p] - anchors[p]) <= 0.17
        ]

        if overlaps:
            if len(matching) / len(overlaps) < 0.8:
                return

        ordered = [
            candidate[p]
            for p in sorted(candidate)
        ]

        # Proteger contra series de otra base o mal alineadas.
        if any(
            b < a - 3
            for a, b in zip(
                ordered, ordered[1:]
            )
        ):
            return

        candidates.append((
            len(matching),
            len(candidate),
            max(candidate),
            candidate,
            method,
            sheet
        ))

    for ws in wb.worksheets:
        rows = [
            list(r)
            for r in ws.iter_rows(
                values_only=True
            )
        ]

        locations = []

        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                if re.match(
                    r"^nacional(?:\b|\d|\s|\*)",
                    normal(value)
                ):
                    locations.append((i, j))

        diagnostics.append(
            f"{ws.title}: "
            f"{ws.max_row}x{ws.max_column}, "
            f"nacional={locations[:5]}"
        )

        for i, j in locations:

            # A. Tabla horizontal con fila Nacional.
            series = [
                (c, num(v))
                for c, v in enumerate(
                    rows[i][j + 1:],
                    j + 1
                )
            ]

            series = [
                (c, v)
                for c, v in series
                if v is not None
            ]

            # Buscar encabezados de año y trimestre.
            for h in range(max(0, i - 15), i):
                years = [
                    (c, year(v))
                    for c, v in enumerate(rows[h])
                    if year(v)
                ]

                if not years:
                    continue

                for k in range(h + 1, i):
                    qs = {
                        c: quarter(v)
                        for c, v in enumerate(rows[k])
                        if quarter(v)
                    }

                    if len(qs) < 4:
                        continue

                    aligned = {}

                    for c, v in series:
                        if c not in qs:
                            continue

                        prev = [
                            yr
                            for pos, yr in years
                            if pos <= c
                        ]

                        if prev:
                            aligned[
                                f"{prev[-1]}-T{qs[c]}"
                            ] = v

                    put(
                        aligned,
                        "encabezados",
                        ws.title
                    )

            # B. Alineación mediante valores históricos.
            # Útil cuando los encabezados están fusionados.
            values = [
                v for _, v in series
            ]

            if len(values) >= 6:
                best = []

                for sy in range(2005, 2027):
                    for sq in range(1, 5):

                        ps = periods_between(
                            f"{sy}-T{sq}",
                            len(values)
                        )

                        matches = [
                            p
                            for p, v in zip(ps, values)
                            if (
                                p in anchors
                                and abs(
                                    v - anchors[p]
                                ) <= 0.17
                            )
                        ]

                        conflicts = [
                            p
                            for p, v in zip(ps, values)
                            if (
                                p in anchors
                                and abs(
                                    v - anchors[p]
                                ) > 0.17
                            )
                        ]

                        if (
                            len(matches) >= 3
                            and not conflicts
                        ):
                            best.append((
                                len(matches),
                                sy,
                                sq,
                                ps
                            ))

                if best:
                    best.sort(reverse=True)

                    count, sy, sq, ps = best[0]

                    if (
                        len(best) == 1
                        or count > best[1][0]
                    ):
                        put(
                            dict(zip(ps, values)),
                            "anclajes",
                            ws.title
                        )

            # C. Formato vertical:
            # columnas Año, Trimestre e índice Nacional.
            if len(rows) > i + 6:

                header = [
                    normal(v)
                    for v in rows[i]
                ]

                for yr_col in range(len(header)):
                    if not any(
                        word in header[yr_col]
                        for word in ("ano", "year")
                    ):
                        continue

                    for q_col in range(len(header)):
                        if (
                            "trimestre" not in header[q_col]
                            and "quarter" not in header[q_col]
                        ):
                            continue

                        found = {}

                        for row in rows[i + 1:]:
                            if max(
                                j, yr_col, q_col
                            ) >= len(row):
                                continue

                            y = year(row[yr_col])
                            q = quarter(row[q_col])
                            v = num(row[j])

                            if (
                                y
                                and q
                                and v is not None
                            ):
                                found[
                                    f"{y}-T{q}"
                                ] = v

                        put(
                            found,
                            "vertical",
                            ws.title
                        )

    if not candidates:
        raise ValueError(
            "Excel sin serie Nacional verificable. "
            "Hojas: "
            + " | ".join(diagnostics)[:1500]
        )

    candidates.sort(
        key=lambda x: (
            x[0],
            x[1],
            x[2]
        ),
        reverse=True
    )

    score, count, last, data, method, sheet = (
        candidates[0]
    )

    if score < 3:
        raise ValueError(
            "Excel con menos de tres puntos "
            "históricos verificables"
        )

    print(
        f"SHF Excel: hoja={sheet}, "
        f"método={method}, "
        f"{count} trimestres, "
        f"{score} controles verificados, "
        f"último={last}",
        flush=True
    )

    return data


def parse_pdf(blob):
    """Extrae la fila Nacional de un PDF con texto seleccionable."""

    from pypdf import PdfReader

    reader = PdfReader(
        io.BytesIO(blob)
    )

    candidates = []

    for page in reader.pages:

        text = (
            page.extract_text(
                extraction_mode="layout"
            )
            or ""
        )

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for i, line in enumerate(lines):

            if not re.match(
                r"^nacional(?:\s|\d|[¹*])",
                normal(line),
            ):
                continue

            tail = re.sub(
                r"^nacional\s*(?:[¹*]|\d(?=\s))?\s*",
                "",
                line,
                flags=re.I,
            )

            values = [
                float(x)
                for x in re.findall(
                    r"(?<!\d)(?:\d{2,3})\.\d{1,3}(?!\d)",
                    tail,
                )
            ]

            values = [
                v for v in values
                if 50 <= v <= 700
            ]

            if len(values) < 6:

                for extra in lines[i + 1:i + 3]:

                    if re.match(
                        r"^[A-Za-zÁÉÍÓÚáéíóú]",
                        extra,
                    ):
                        break

                    values += [
                        float(x)
                        for x in re.findall(
                            r"(?<!\d)\d{2,3}\.\d{1,3}(?!\d)",
                            extra,
                        )
                        if 50 <= float(x) <= 700
                    ]

            if len(values) < 6:
                continue

            possible = []

            for header in lines[
                max(0, i - 7):i
            ]:

                yrs = [
                    int(x)
                    for x in re.findall(
                        r"(?<!\d)20(?:1\d|2\d|3\d)(?!\d)",
                        header,
                    )
                ]

                if (
                    len(set(yrs)) >= 2
                    and yrs == sorted(yrs)
                ):
                    possible.append(yrs)

            if not possible:
                continue

            years = max(
                possible,
                key=len,
            )

            n_prior = 4 * (
                len(years) - 1
            )

            last = len(values) - n_prior

            if not 1 <= last <= 4:
                continue

            got = {}
            idx = 0

            for year in years:

                limit = (
                    last
                    if year == years[-1]
                    else 4
                )

                for q in range(
                    1, limit + 1
                ):
                    got[
                        f"{year}-T{q}"
                    ] = values[idx]

                    idx += 1

            if len(got) >= 6:
                candidates.append(got)

    if not candidates:
        raise ValueError(
            "PDF sin tabla Nacional legible; "
            "se requiere PDF con texto seleccionable"
        )

    return max(
        candidates,
        key=lambda d: (
            max(d),
            len(d),
        ),
    )


def read_levels():
    out = dict(SEED)

    if LEVEL.exists():

        with LEVEL.open(
            newline="",
            encoding="utf-8-sig",
        ) as f:

            for r in csv.DictReader(f):

                try:
                    if re.fullmatch(
                        r"20\d\d-T[1-4]",
                        r["periodo"],
                    ):
                        out[
                            r["periodo"]
                        ] = float(
                            r["indice"]
                        )

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    pass

    return out


def validate(candidate, existing):

    if len(candidate) < 6:
        raise ValueError(
            "Menos de seis datos del índice nacional"
        )

    for p, v in candidate.items():

        if (
            not re.fullmatch(
                r"20\d\d-T[1-4]",
                p,
            )
            or not 50 <= v <= 700
        ):
            raise ValueError(
                f"Periodo/índice inválido: {p}={v}"
            )

    shared = [
        p
        for p in candidate
        if p in existing
    ]

    if shared and any(
        abs(candidate[p] - existing[p]) > 0.17
        for p in shared
    ):
        conflicts = [
            p
            for p in shared
            if abs(
                candidate[p] - existing[p]
            ) > 0.17
        ]

        raise ValueError(
            "No coincide con el histórico en "
            + ",".join(conflicts)[:140]
        )

    if not shared:
        raise ValueError(
            "No hay trimestres coincidentes "
            "con el histórico para validar base 2017=100"
        )

    return True


def write_csv(path, headers, rows):

    tmp = path.with_suffix(
        ".csv.tmp"
    )

    with tmp.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    tmp.replace(path)


def main():

    old = read_levels()
    combined = dict(old)

    diagnostics = []
    sources = []
    discovered = []

    # Buscar anexos en las páginas oficiales.
    for page in PAGES:

        try:
            html, base, _ = fetch(page)

            for url in official_links(
                html, base
            ):
                if url not in discovered:
                    discovered.append(url)

        except Exception as exc:
            diagnostics.append(
                f"Página {page}: {exc}"
            )

    print(
        f"SHF: {len(discovered)} anexos identificados",
        flush=True,
    )

    if not discovered:
        raise RuntimeError(
            "SHF: no se identificaron anexos "
            "en páginas oficiales. "
            + " | ".join(
                diagnostics[-2:]
            )
        )

    # Revisar documentos PDF/XLSX.
    for url in discovered[:20]:

        try:
            blob, final, ctype = fetch(url)

            if blob.startswith(b"%PDF"):
                data = parse_pdf(blob)
                fmt = "pdf"

            elif blob.startswith(
                b"PK\x03\x04"
            ):
                data = parse_excel(blob)
                fmt = "xlsx"

            else:
                continue

            validate(data, old)

            combined.update(data)

            sources.append({
                "url": final,
                "format": fmt,
                "periods": len(data),
                "last": max(data),
            })

            print(
                "SHF archivo validado: "
                f"{fmt}; "
                f"{min(data)} a {max(data)}",
                flush=True,
            )

        except Exception as exc:
            diagnostics.append(
                f"{url}: {str(exc)[:200]}"
            )

    if not sources:
        raise RuntimeError(
            "SHF: ningún anexo pudo validar "
            "la fila Nacional. "
            + " | ".join(
                diagnostics[-3:]
            )
        )

    newest = max(combined)

    new_periods = [
        p for p in combined
        if p >= "2020-T1"
    ]

    if len(new_periods) < 4:
        raise RuntimeError(
            "SHF: se requieren al menos "
            "cuatro observaciones posteriores a 2019"
        )

    levels_rows = [
        (
            p,
            round(v, 3),
            "2017=100",
            "SHF · Índice nacional oficial",
        )
        for p, v in sorted(
            combined.items()
        )
    ]

    yoy = []

    for p, v in sorted(
        combined.items()
    ):

        yr, q = p.split("-T")

        prev = combined.get(
            f"{int(yr) - 1}-T{q}"
        )

        if (
            prev is not None
            and prev > 0
            and int(yr) >= 2016
        ):
            yoy.append(
                (
                    p,
                    round(
                        (v / prev - 1) * 100,
                        3,
                    ),
                )
            )

    # Escribir los CSV solo después de validar.
    write_csv(
        LEVEL,
        [
            "periodo",
            "indice",
            "base",
            "fuente",
        ],
        levels_rows,
    )

    write_csv(
        YOY,
        [
            "periodo",
            "variacion_anual",
        ],
        yoy,
    )

    status = {
        "updated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "status": "ok",
        "latest_period": newest,
        "first_period": min(combined),
        "index_rows": len(combined),
        "variation_rows": len(yoy),
        "sources": sources,
    }

    STATUS.write_text(
        json.dumps(
            status,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        f"SHF automático: "
        f"{min(combined)} a {newest}; "
        f"{len(combined)} índices, "
        f"{len(yoy)} variaciones anuales",
        flush=True,
    )


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        STATUS.write_text(
            json.dumps(
                {
                    "status": "error",
                    "checked_at_utc": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        print(
            "ERROR SHF:",
            exc,
            file=sys.stderr,
        )

        sys.exit(1)
