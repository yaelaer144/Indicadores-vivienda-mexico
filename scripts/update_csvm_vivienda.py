
#!/usr/bin/env python3
"""Actualización defensiva de la Cuenta Satélite de Vivienda (INEGI).

Actualiza csvm_pib_vivienda_anual.csv cuando encuentra una tabla oficial
compatible y validada.

Variable opcional:
    CSVM_SOURCE_URL = URL HTTPS de una exportación oficial del INEGI.
"""

import csv
import io
import json
import os
import re
import sys
import urllib.request
import unicodedata

from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]

CSV = ROOT / "csvm_pib_vivienda_anual.csv"
STATUS = ROOT / "csvm_update_status.json"

COLUMNS = [
    "anio",
    "pib_total_mdp",
    "participacion_pib_pct",
    "edificacion_mdp",
    "adquisicion_mdp",
    "uso_mdp",
    "regulacion_fomento_mdp",
    "fuente",
]

METRICS = COLUMNS[1:-1]

DEFAULT_SOURCES = [
    "https://www.inegi.org.mx/temas/viviendasat/",
    (
        "https://www.inegi.org.mx/app/tabulados/default.aspx"
        "?cno=1&idrt=3268&in=28&opc=p&pr=24&tp=20&vr=1&wr=1"
    ),
]

SYNONYMS = {
    "pib_total_mdp": (
        "pib de la vivienda",
        "pib del sector de la vivienda",
        "producto interno bruto de la vivienda",
    ),
    "participacion_pib_pct": (
        "proporcion respecto al total nacional",
        "participacion en el pib",
        "participacion respecto al pib",
        "participacion del pib",
    ),
    "edificacion_mdp": ("edificacion",),
    "adquisicion_mdp": ("adquisicion",),
    "uso_mdp": (
        "uso",
        "uso de vivienda",
        "uso de la vivienda",
    ),
    "regulacion_fomento_mdp": (
        "regulacion y fomento",
        "regulacion, promocion y fomento",
        "regulacion promocion y fomento",
    ),
}

SOURCE_LABEL = "INEGI · Cuenta Satélite de Vivienda de México"


def normalize(value):
    s = unicodedata.normalize("NFKD", str(value))
    s = s.encode("ascii", "ignore").decode().lower()
    return re.sub(
        r"\s+", " ",
        re.sub(r"[^a-z0-9]+", " ", s)
    ).strip()


def num(value):
    if value is None:
        return None

    s = str(value)
    s = s.replace("\u00a0", " ")
    s = s.strip().replace(",", "").replace(" ", "")

    if not s or s in ("-", "N/D", "nan", "None"):
        return None

    try:
        return float(s.rstrip("%"))
    except ValueError:
        return None


def read_existing():
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows or not all(k in rows[0] for k in COLUMNS):
        raise ValueError(
            "CSV histórico ausente o columnas incompatibles"
        )

    return {
        int(r["anio"]): {
            k: num(r[k]) for k in METRICS
        }
        for r in rows
    }


class Tables(HTMLParser):
    """Extrae tablas HTML sin depender de un navegador."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table = []

        elif self.table is not None and tag == "tr":
            self.row = []

        elif self.row is not None and tag in ("td", "th"):
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join(self.cell).strip())
            self.cell = None

        elif tag == "tr" and self.row is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None

        elif tag == "table" and self.table is not None:
            if self.table:
                self.tables.append(self.table)
            self.table = None


def parse_matrix(matrix):
    """Identifica años en columnas o años en filas."""

    if not matrix:
        return {}

    matrix = [
        [str(x or "").strip() for x in r]
        for r in matrix if r
    ]

    results = {}

    # Caso A: años en columnas
    for header_idx, header in enumerate(matrix[:12]):
        yrs = {}

        for i, value in enumerate(header):
            match = re.search(r"\b(20\d{2})\b", value)

            if match:
                yrs[i] = int(match.group(1))

        if len(yrs) < 3:
            continue

        for row in matrix[header_idx + 1:]:
            label = normalize(
                " ".join(row[:min(2, min(yrs))])
            )

            for metric, aliases in SYNONYMS.items():
                if any(
                    label == normalize(a)
                    or label.startswith(normalize(a) + " ")
                    for a in aliases
                ):
                    for i, year in yrs.items():
                        if i < len(row):
                            value = num(row[i])

                            if value is not None:
                                results.setdefault(year, {})[
                                    metric
                                ] = value

        if results:
            return results

    # Caso B: años en filas
    for header_idx, header in enumerate(matrix[:8]):
        mapping = {}

        for i, value in enumerate(header):
            v = normalize(value)

            if v in ("anio", "ano", "year"):
                mapping["anio"] = i

            for metric in METRICS:
                if (
                    v == normalize(metric)
                    or any(v == normalize(a) for a in SYNONYMS[metric])
                ):
                    mapping[metric] = i

        if "anio" not in mapping or len(mapping) < 4:
            continue

        for row in matrix[header_idx + 1:]:
            if mapping["anio"] >= len(row):
                continue

            yr = num(row[mapping["anio"]])

            if yr is None or yr < 2003 or yr > 2100:
                continue

            year = int(yr)

            for key, idx in mapping.items():
                if key != "anio" and idx < len(row):
                    value = num(row[idx])

                    if value is not None:
                        results.setdefault(year, {})[
                            key
                        ] = value

        if results:
            return results

    return {}


def matrices_from_content(raw, url):
    """Convierte HTML, CSV o XLSX en matrices."""

    if (
        raw[:2] == b"PK"
        or url.lower().split("?")[0].endswith(".xlsx")
    ):
        from openpyxl import load_workbook

        wb = load_workbook(
            io.BytesIO(raw),
            read_only=True,
            data_only=True,
        )

        return [
            list(ws.values)
            for ws in wb.worksheets
        ]

    text = raw.decode("utf-8-sig", "replace")

    if "<table" in text.lower():
        parser = Tables()
        parser.feed(text)
        return parser.tables

    for separator in (",", ";", "\t"):
        parsed = list(
            csv.reader(
                io.StringIO(text),
                delimiter=separator,
            )
        )

        if parsed and len(parsed[0]) > 3:
            return [parsed]

    return []


def fetch(url):
    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname not in (
            "www.inegi.org.mx",
            "inegi.org.mx",
        )
    ):
        raise ValueError(
            "La fuente debe pertenecer al INEGI y usar HTTPS"
        )

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; vivienda-csvm/1.0)"
            ),
            "Accept": (
                "text/html,text/csv,"
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        },
    )

    with urllib.request.urlopen(req, timeout=40) as resp:
        return resp.read(15_000_001)


def merge_tables(tables):
    combined = {}

    for matrix in tables:
        subset = parse_matrix(matrix)

        for year, rec in subset.items():
            combined.setdefault(year, {}).update(rec)

    return combined


def validate(candidate, old):
    """Evita publicar datos incompletos o inconsistentes."""

    ready = {
        year: row
        for year, row in candidate.items()
        if all(row.get(k) is not None for k in METRICS)
    }

    if not ready:
        raise ValueError(
            "La fuente no publicó las 6 variables "
            "compatibles con el dashboard"
        )

    overlap = sorted(set(ready) & set(old))

    if len(overlap) < 3:
        raise ValueError(
            "No hay al menos tres años para validar "
            "contra el histórico"
        )

    for year in overlap[-3:]:
        for key in (
            "pib_total_mdp",
            "participacion_pib_pct",
        ):
            before = old[year].get(key)
            after = ready[year][key]

            if (
                before is None
                or abs(after - before)
                > max(abs(before) * 0.08, 0.25)
            ):
                raise ValueError(
                    "El dato oficial no coincide "
                    f"con el histórico: {year}/{key}"
                )

    for year, row in ready.items():
        total = row["pib_total_mdp"]

        subtotal = sum(
            row[k] for k in METRICS[2:]
        )

        if (
            total <= 0
            or abs(subtotal - total)
            > max(total * 0.015, 5)
        ):
            raise ValueError(
                f"Los componentes no suman el PIB total "
                f"en {year}: {subtotal} vs {total}"
            )

        participacion = row["participacion_pib_pct"]

        if not (0 < participacion < 30):
            raise ValueError(
                f"Participación fuera de rango en {year}"
            )

    if max(ready) < max(old):
        raise ValueError(
            "La fuente oficial es más antigua "
            "que el CSV existente"
        )

    # Conservar años no incluidos en la descarga
    merged = {
        year: dict(row)
        for year, row in old.items()
    }

    merged.update(ready)

    return merged, len(ready)


def write_csv(data):
    tmp = CSV.with_suffix(".csv.tmp")

    with tmp.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=COLUMNS,
        )

        writer.writeheader()

        for year in sorted(data):
            row = {
                "anio": year,
                "fuente": SOURCE_LABEL,
            }

            row.update({
                k: data[year].get(k, "")
                for k in METRICS
            })

            writer.writerow(row)

    tmp.replace(CSV)


def status(**kwargs):
    payload = {
        "updated_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        **kwargs,
    }

    STATUS.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main():
    previous = read_existing()

    urls = (
        [os.environ["CSVM_SOURCE_URL"]]
        if os.getenv("CSVM_SOURCE_URL")
        else []
    ) + DEFAULT_SOURCES

    errors = {}

    for url in dict.fromkeys(urls):
        try:
            content = fetch(url)

            tables = matrices_from_content(
                content, url
            )

            candidate = merge_tables(tables)

            merged, count = validate(
                candidate, previous
            )

            changed = merged != previous

            if changed:
                write_csv(merged)

            status(
                status=(
                    "actualizado"
                    if changed
                    else "sin_cambios"
                ),
                ultimo_anio=max(merged),
                anios_descargados=count,
                fuente_url=url,
                modifico_csv=changed,
            )

            print(
                f"CSVM: {max(merged)}; "
                f"{count} años fuente; "
                f"cambios={changed}"
            )

            return 0

        except Exception as exc:
            errors[url] = (
                f"{type(exc).__name__}: {exc}"
            )

    status(
        status="conservado_sin_cambio",
        ultimo_anio=max(previous),
        error="No se obtuvo una tabla oficial validada",
        intentos=errors,
    )

    print(
        "CSVM: NO actualizada; "
        "datos históricos conservados",
        file=sys.stderr,
    )

    print(
        json.dumps(
            errors,
            ensure_ascii=False,
            indent=2,
        ),
        file=sys.stderr,
    )

    return 1


if __name__ == "__main__":
    sys.exit(main())
