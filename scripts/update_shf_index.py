
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
    """Extrae SHF de bloques verticales trimestrales.

    Reconoce filas Nacional repetidas y determina la columna,
    periodo inicial y orden con controles históricos oficiales.
    """
    import openpyxl
    from collections import Counter

    wb = openpyxl.load_workbook(
        io.BytesIO(blob),
        read_only=True,
        data_only=True
    )

    anchors = dict(SEED)
    anchors.update({
        "2025-T1": 186.9,
        "2025-T2": 191.9,
        "2025-T3": 195.9,
        "2025-T4": 199.0,
        "2026-T1": 202.9,
        "2026-T2": 205.9,
    })

    def number(value):
        if isinstance(value, bool) or value is None:
            return None

        try:
            n = float(str(value).strip().replace(",", ""))
        except (ValueError, TypeError):
            return None

        return round(n, 3) if 50 <= n <= 700 else None

    def from_index(index):
        year = index // 4
        quarter = index % 4 + 1
        return f"{year}-T{quarter}"

    candidates = []
    diagnostics = []

    for ws in wb.worksheets:
        national = []

        for rownum, row in enumerate(
            ws.iter_rows(values_only=True),
            start=1
        ):
            values = list(row)

            if any(
                normal(v).startswith("nacional")
                for v in values
            ):
                national.append((rownum, values))

        positions = [r[0] for r in national]

        distances = [
            b - a
            for a, b in zip(positions, positions[1:])
        ]

        stride, frequency = (
            Counter(distances).most_common(1)[0]
            if distances else (0, 0)
        )

        diagnosis = (
            f"{ws.title}: {ws.max_row}x{ws.max_column}; "
            f"Nacional={len(national)}; "
            f"primeros={positions[:5]}; "
            f"paso={stride} ({frequency} repeticiones)"
        )

        diagnostics.append(diagnosis)

        print(
            "SHF estructura: " + diagnosis,
            flush=True
        )

        if len(national) < 8:
            continue

        # Examinar las columnas de las filas Nacional.
        for col in range(ws.max_column):
            values = [
                number(row[col])
                if col < len(row)
                else None
                for _, row in national
            ]

            if sum(v is not None for v in values) < 8:
                continue

            # Determinar el periodo inicial y el orden
            # mediante coincidencias históricas verificadas.
            for direction in (1, -1):
                for start_year in range(2000, 2027):
                    for start_quarter in range(1, 5):

                        start = (
                            start_year * 4
                            + start_quarter - 1
                        )

                        series = {
                            from_index(start + direction * i): v
                            for i, v in enumerate(values)
                            if (
                                v is not None
                                and start + direction * i >= 0
                            )
                        }

                        shared = [
                            p for p in series
                            if p in anchors
                        ]

                        matched = [
                            p for p in shared
                            if abs(
                                series[p] - anchors[p]
                            ) <= 0.17
                        ]

                        conflicts = [
                            p for p in shared
                            if abs(
                                series[p] - anchors[p]
                            ) > 0.17
                        ]

                        if conflicts or len(matched) < 5:
                            continue

                        if len({
                            p[:4] for p in matched
                        }) < 3:
                            continue

                        cleaned = {
                            p: v
                            for p, v in series.items()
                            if p >= "2015-T1"
                        }

                        if len(cleaned) < 20:
                            continue

                        score = (
                            len(matched),
                            len(cleaned),
                            max(cleaned)
                        )

                        candidates.append((
                            score,
                            cleaned,
                            ws.title,
                            col + 1,
                            direction,
                            from_index(start)
                        ))

    if not candidates:
        raise ValueError(
            "No se pudo identificar la columna "
            "del índice nacional. "
            + " | ".join(diagnostics)[:1400]
        )

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    score, result, sheet, col, direction, first = (
        candidates[0]
    )

    if (
        len(candidates) > 1
        and candidates[1][0] == score
        and candidates[1][1] != result
    ):
        raise ValueError(
            "Hay más de una interpretación posible "
            "de los periodos SHF"
        )

    print(
        f"SHF Excel validado: hoja={sheet}; "
        f"columna={col}; "
        f"primer bloque={first}; "
        f"orden={'ascendente' if direction == 1 else 'descendente'}; "
        f"controles={score[0]}; "
        f"periodo={min(result)} a {max(result)}",
        flush=True
    )

    return result


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
