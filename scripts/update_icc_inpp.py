
#!/usr/bin/env python3
"""Actualiza ICC e INPP desde los CSV oficiales de INEGI.

También permite validar archivos descargados manualmente:
python scripts/update_icc_inpp.py --icc-csv ICC.csv --inpp-csv INPP.csv
"""

import argparse
import csv
import io
import json
import math
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "2016-01"

URLS = {
    "icc": (
        "https://www.inegi.org.mx/app/indicesdepreciosv2/"
        "Estructura.aspx?idEstructura=1120019000100010"
    ),
    "inpp": (
        "https://www.inegi.org.mx/app/indicesdepreciosv2/"
        "Estructura.aspx?idEstructura=112001900050"
    ),
}

SPECS = {
    "icc": {
        "file": "icc_incevis_base2025_mensual.csv",
        "columns": {
            "1660002": "general",
            "1660003": "materiales",
            "1660004": "maquinaria",
            "1660005": "mano_obra",
        },
        "labels": [
            "Nacional",
            "Materiales de construcción",
            "Alquiler de maquinaria",
            "Mano de obra",
        ],
        "anchor": {
            "1660002": 156.246,
            "1660003": 157.178,
            "1660004": 129.501,
            "1660005": 152.941,
        },
    },
    "inpp": {
        "file": "inpp_construccion_edificacion_base2025_mensual.csv",
        "columns": {
            "1700226": "construccion",
            "1700227": "edificacion",
            "1700228": "edificacion_residencial",
            "1700232": "edificacion_no_residencial",
        },
        "labels": [
            "23 Construcción",
            "236 Edificación",
            "2361 Edificación residencial",
            "2362 Edificación no residencial",
        ],
        "anchor": {
            "1700226": 153.495,
            "1700227": 154.904,
            "1700228": 156.246,
            "1700232": 152.507,
        },
    },
}

MONTHS = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4,
    "may": 5, "jun": 6, "jul": 7, "ago": 8,
    "sep": 9, "oct": 10, "nov": 11, "dic": 12,
}


def norm(value):
    return (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def parse_month(value):
    value = norm(value)

    match = re.fullmatch(
        r"(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
        r"[a-z]*\s+(20\d{2})",
        value,
    )
    if match:
        return f"{match.group(2)}-{MONTHS[match.group(1)]:02d}"

    match = re.fullmatch(
        r"(20\d{2})[-/](0?[1-9]|1[0-2])",
        value,
    )
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"

    return None


def load_inegi_csv(path, kind):
    raw = Path(path).read_bytes()

    if len(raw) < 200:
        raise ValueError(f"{kind}: CSV vacío o incompleto")

    for encoding in ("utf-8-sig", "cp1252", "latin1"):
        try:
            lines = list(
                csv.reader(io.StringIO(raw.decode(encoding)))
            )
            break
        except UnicodeError:
            continue
    else:
        raise ValueError(f"{kind}: codificación desconocida")

    header = next(
        (
            i for i, row in enumerate(lines)
            if row
            and norm(row[0]) == "fecha"
            and any(v.strip().isdigit() for v in row[1:])
        ),
        None,
    )

    if header is None:
        raise ValueError(
            f"{kind}: no se encontró encabezado Fecha con IDs"
        )

    ids = [v.strip() for v in lines[header][1:]]
    columns = SPECS[kind]["columns"]

    missing = set(columns) - set(ids)
    if missing:
        raise ValueError(
            f"{kind}: faltan identificadores {sorted(missing)}"
        )

    base_row = next(
        (
            row for row in lines[:header]
            if row and norm(row[0]) == "base"
        ),
        None,
    )

    if base_row is None:
        raise ValueError(f"{kind}: no se identificó la base")

    for identifier in columns:
        position = ids.index(identifier) + 1
        if position >= len(base_row):
            raise ValueError(f"{kind}: falta información de base")

        base = norm(base_row[position]).replace("base ", "")

        if "julio 2025=100" not in base:
            raise ValueError(
                f"{kind}: base diferente de julio 2025=100"
            )

    positions = {
        identifier: ids.index(identifier) + 1
        for identifier in columns
    }

    data = {}

    for row in lines[header + 1:]:
        if not row:
            continue

        period = parse_month(row[0])

        if not period or period < START:
            continue

        values = {}

        for identifier, name in columns.items():
            try:
                value = float(
                    row[positions[identifier]]
                    .strip()
                    .replace(",", "")
                )
            except (ValueError, IndexError):
                raise ValueError(
                    f"{kind}: valor inválido {period}/{name}"
                )

            if not math.isfinite(value) or not 20 <= value <= 500:
                raise ValueError(
                    f"{kind}: índice fuera de rango {period}/{name}"
                )

            values[name] = value

        if period in data:
            raise ValueError(f"{kind}: mes duplicado {period}")

        data[period] = values

    if not data or min(data) > START or len(data) < 120:
        raise ValueError(
            f"{kind}: histórico insuficiente ({len(data)} meses)"
        )

    periods = sorted(data)

    for previous, current in zip(periods, periods[1:]):
        year_a, month_a = map(int, previous.split("-"))
        year_b, month_b = map(int, current.split("-"))

        if year_b * 12 + month_b - year_a * 12 - month_a != 1:
            raise ValueError(
                f"{kind}: falta información entre "
                f"{previous} y {current}"
            )

    if "2025-07" not in data:
        raise ValueError(f"{kind}: falta julio de 2025")

    if "2026-09" in data:
        for identifier, expected in SPECS[kind]["anchor"].items():
            name = columns[identifier]
            actual = data["2026-09"][name]

            if abs(actual - expected) > 0.5:
                raise ValueError(
                    f"{kind}: discrepancia en septiembre 2026, "
                    f"serie {name}"
                )

    print(
        f"{kind.upper()}: validado {min(data)} a {max(data)}; "
        f"{len(data)} meses",
        flush=True,
    )

    return data


def export_browser(kind, output):
    from playwright.sync_api import sync_playwright

    diagnostic = ROOT / "icc_inpp_diagnostico"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        page = browser.new_page(
            accept_downloads=True,
            locale="es-MX",
            viewport={"width": 1450, "height": 1000},
        )

        try:
            response = page.goto(
                URLS[kind],
                wait_until="domcontentloaded",
                timeout=90000,
            )

            status = response.status if response else "sin respuesta"

            print(
                f"{kind.upper()}: INEGI HTTP {status}",
                flush=True,
            )

            if response and response.status >= 400:
                raise RuntimeError(
                    f"{kind}: INEGI respondió HTTP {status}"
                )

            page.wait_for_timeout(5000)

            # Buscar filas tanto en la página como en sus frames.
            # Comparar únicamente la primera celda de cada fila.
            javascript = r"""
            (label) => {
                const clean = s => (s || '')
                    .normalize('NFD')
                    .replace(/[\u0300-\u036f]/g, '')
                    .replace(/\s+/g, ' ')
                    .trim()
                    .toLowerCase();

                const desired = clean(label);

                return Array.from(document.querySelectorAll('tr'))
                    .filter(tr => {
                        const cell = tr.querySelector('td');
                        const checkbox = tr.querySelector(
                            'input[type="checkbox"]'
                        );

                        if (!cell || !checkbox) return false;

                        const text = clean(
                            cell.innerText || cell.textContent
                        ).replace(/^[+\-−]\s*/, '');

                        return (
                            text === desired ||
                            text.startsWith(desired + ' ')
                        );
                    })
                    .map(tr => ({
                        label: clean(
                            tr.querySelector('td').innerText ||
                            tr.querySelector('td').textContent
                        )
                    }));
            }
            """

            for label in SPECS[kind]["labels"]:
                matches = []

                for frame in page.frames:
                    try:
                        result = frame.evaluate(javascript, label)

                        for item in result:
                            matches.append((frame, item))

                    except Exception:
                        continue

                
                if not matches:
                    raise RuntimeError(
                        f"{kind}: no se encontró la serie {label!r}"
                    )

                frame, _ = matches[0]

                if len(matches) > 1:
                    print(
                        f"{kind.upper()}: {label!r} tiene "
                        f"{len(matches)} coincidencias; "
                        "se utilizará la primera",
                        flush=True,
                    )



                # Localizar la fila por la primera celda.
                index = frame.evaluate(
                    r"""
                    (label) => {
                        const clean = s => (s || '')
                            .normalize('NFD')
                            .replace(/[\u0300-\u036f]/g, '')
                            .replace(/\s+/g, ' ')
                            .trim()
                            .toLowerCase();

                        return Array.from(
                            document.querySelectorAll('tr')
                        ).findIndex(tr => {
                            const cell = tr.querySelector('td');
                            const checkbox = tr.querySelector(
                                'input[type="checkbox"]'
                            );

                            if (!cell || !checkbox) return false;

                            const text = clean(
                                cell.innerText || cell.textContent
                            ).replace(/^[+\-−]\s*/, '');
                            return (
                            text === clean(label) ||
                            text.startsWith(clean(label) + ' ')
                            );

                        });
                    }
                    """,
                    label,
                )

                if index < 0:
                    raise RuntimeError(
                        f"{kind}: no se pudo localizar {label}"
                    )

                row = frame.locator("tr").nth(index)
                checkbox = row.locator(
                    'input[type="checkbox"]'
                ).first

                if not checkbox.is_checked():
                    checkbox.check(
                        force=True,
                        timeout=15000,
                    )

                print(
                    f"{kind.upper()}: seleccionada {label}",
                    flush=True,
                )


            controls = []

            for frame in page.frames:
                for selector in (
                    'img[src*="ico_csv.png"]',
                    'img[onclick*="ExportaFormatoPopUp"]',
                    'a:has-text("CSV")',
                    'button:has-text("CSV")',
                    'input[value="CSV"]',
                ):
                    locator = frame.locator(selector)

                    for i in range(min(locator.count(), 10)):
                        if locator.nth(i).is_visible():
                            controls.append(locator.nth(i))

            if not controls:
                raise RuntimeError(
                    f"{kind}: no se encontró botón CSV"
                )

            with page.expect_download(timeout=120000) as download:
                controls[0].click(timeout=15000)

            download.value.save_as(str(output))

            print(
                f"{kind.upper()}: CSV descargado "
                f"({output.stat().st_size} bytes)",
                flush=True,
            )

        except Exception as error:
            diagnostic.mkdir(exist_ok=True)

            try:
                page.screenshot(
                    path=str(diagnostic / f"{kind}.png"),
                    full_page=True,
                    timeout=15000,
                )
            except Exception:
                pass

            try:
                (diagnostic / f"{kind}.html").write_text(
                    page.content(),
                    encoding="utf-8",
                )
            except Exception:
                pass

            frames = []

            for frame in page.frames:
                try:
                    frames.append({
                        "url": frame.url,
                        "rows": frame.locator("tr").count(),
                        "examples": frame.locator(
                            "tr"
                        ).all_text_contents()[:25],
                    })
                except Exception as exc:
                    frames.append({"error": str(exc)})

            (diagnostic / f"{kind}.json").write_text(
                json.dumps(
                    {
                        "error": str(error),
                        "url": page.url,
                        "frames": frames,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            raise RuntimeError(
                f"{kind}: {error}. "
                "Revisar carpeta icc_inpp_diagnostico"
            ) from error

        finally:
            browser.close()


def build_rows(data, kind):
    columns = list(SPECS[kind]["columns"].values())
    records = []

    for period in sorted(data):
        record = {"periodo": period}

        for column in columns:
            record[column] = (
                f"{data[period][column]:.12f}"
                .rstrip("0")
                .rstrip(".")
            )

        previous = f"{int(period[:4]) - 1}-{period[5:]}"

        for column in columns:
            if previous in data:
                variation = (
                    data[period][column] /
                    data[previous][column] - 1
                ) * 100

                record[column + "_yoy"] = f"{variation:.9f}"
            else:
                record[column + "_yoy"] = ""

        records.append(record)

    fields = (
        ["periodo"]
        + columns
        + [column + "_yoy" for column in columns]
    )

    return records, fields


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--icc-csv", type=Path)
    parser.add_argument("--inpp-csv", type=Path)

    args = parser.parse_args()

    if bool(args.icc_csv) != bool(args.inpp_csv):
        parser.error("Debes indicar ambos CSV")

    with tempfile.TemporaryDirectory() as directory:
        sources = {}

        for kind in SPECS:
            supplied = getattr(args, kind + "_csv")

            path = (
                supplied
                if supplied
                else Path(directory) / (kind + ".csv")
            )

            if not supplied:
                export_browser(kind, path)

            sources[kind] = load_inegi_csv(path, kind)

    icc = sources["icc"]
    inpp = sources["inpp"]

    common = sorted(set(icc) & set(inpp))

    if len(common) < 120:
        raise ValueError("Histórico común insuficiente")

    for period in common:
        difference = abs(
            icc[period]["general"] -
            inpp[period]["edificacion_residencial"]
        )

        if difference > 0.0001:
            raise ValueError(
                f"ICC e INPP residencial no coinciden en {period}"
            )

    outputs = {}

    status = {
        "estado": "actualizado",
        "fuente": "INEGI",
        "base": "julio 2025=100",
        "fecha_actualizacion_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "series": {},
    }

    for kind, data in sources.items():
        filename = SPECS[kind]["file"]
        rows, fields = build_rows(data, kind)

        with io.StringIO(newline="") as buffer:
            writer = csv.DictWriter(
                buffer,
                fieldnames=fields,
                lineterminator="\n",
            )

            writer.writeheader()
            writer.writerows(rows)

            outputs[filename] = buffer.getvalue()

        status["series"][kind] = {
            "mes_inicial": min(data),
            "mes_final": max(data),
            "meses": len(data),
        }

    # Escribir únicamente después de validar ambas series.
    for filename, content in outputs.items():
        destination = ROOT / filename
        temporary = destination.with_suffix(".csv.tmp")

        temporary.write_text(
            content,
            encoding="utf-8",
        )

        temporary.replace(destination)

    (ROOT / "icc_inpp_update_status.json").write_text(
        json.dumps(
            status,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(status, ensure_ascii=False, indent=2),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(
            f"ICC/INPP: error, archivos existentes intactos: {error}",
            file=sys.stderr,
        )
        sys.exit(1)
