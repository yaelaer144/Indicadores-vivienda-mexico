
#!/usr/bin/env python3
"""Actualiza la variación mensual real desestacionalizada
de Edificación, ENEC-INEGI, desde enero de 2016.
"""

import csv
import io
import re
import sys
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

DEST = ROOT / "enec_edificacion_variacion_mensual.csv"

URL = "https://www.inegi.org.mx/app/tabulados/default.html?nc=807"

MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "enero febrero marzo abril mayo junio julio "
            "agosto septiembre octubre noviembre diciembre"
        ).split(),
        1,
    )
}


def extract(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True).lower()

    if (
        "series desestacionalizadas" not in text
        or "variación porcentual mensual" not in text
    ):
        raise ValueError(
            "El archivo no corresponde al tabulado ENEC esperado"
        )

    table = next(
        (
            t for t in soup.select("table")
            if any(
                "edificación" in c.get_text(
                    " ", strip=True
                ).lower()
                for c in t.select("tr")[:12]
            )
        ),
        None,
    )

    if table is None:
        raise ValueError(
            "No se encontró la tabla de Edificación"
        )

    year = None
    position = None
    result = {}

    for tr in table.select("tr"):
        cells = [
            c.get_text(" ", strip=True)
            for c in tr.find_all(
                ["th", "td"],
                recursive=False,
            )
        ]

        if not cells:
            continue

        normalized = [c.lower() for c in cells]

        if "edificación" in normalized:
            position = normalized.index("edificación")
            continue

        if (
            len(cells) == 1
            and re.fullmatch(r"20\d{2}", cells[0])
        ):
            year = int(cells[0])
            continue

        if (
            year is None
            or position is None
            or len(cells) <= position
        ):
            continue

        label = re.sub(
            r"[^a-záéíóú]",
            "",
            cells[0].lower(),
        )

        month = next(
            (
                n for name, n in MONTHS.items()
                if label.startswith(name)
            ),
            None,
        )

        if month is None:
            continue

        period = f"{year}-{month:02d}"

        if period < "2016-01":
            continue

        try:
            value = float(
                cells[position].replace(",", "")
            )
        except ValueError as exc:
            raise ValueError(
                f"Dato no numérico: "
                f"{period}: {cells[position]!r}"
            ) from exc

        if not -100 < value < 100:
            raise ValueError(
                f"Variación fuera de rango: "
                f"{period}={value}"
            )

        if period in result:
            raise ValueError(
                f"Periodo duplicado: {period}"
            )

        result[period] = value

    periods = sorted(result)

    if (
        len(periods) < 100
        or periods[0] != "2016-01"
    ):
        raise ValueError(
            f"Histórico insuficiente: "
            f"{len(periods)} meses"
        )

    for a, b in zip(periods, periods[1:]):
        ay, am = map(int, a.split("-"))
        by, bm = map(int, b.split("-"))

        if (
            by * 12 + bm
        ) - (
            ay * 12 + am
        ) != 1:
            raise ValueError(
                f"Falta un periodo entre {a} y {b}"
            )

    if periods[-1] > datetime.now().strftime("%Y-%m"):
        raise ValueError(
            "La fuente reporta un periodo futuro"
        )

    return result


def choose_year(select, year):
    options = select.locator("option").evaluate_all(
        """els => els.map(e => ({
            value: e.value,
            text: e.textContent.trim()
        }))"""
    )

    option = next(
        (
            x for x in options
            if re.search(
                rf"\b{year}\b",
                x["text"],
            )
        ),
        None,
    )

    if option is None:
        raise ValueError(
            f"No se ofrece el año {year}"
        )

    select.select_option(option["value"])


def download_html(folder):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            accept_downloads=True,
            locale="es-MX",
        )

        try:
            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=90000,
            )

            status = (
                response.status
                if response
                else "sin respuesta"
            )

            print(
                f"ENEC desestacionalizada: "
                f"HTTP {status}",
                flush=True,
            )

            page.get_by_text(
                "Series desestacionalizadas",
                exact=False,
            ).first.wait_for(timeout=30000)

            selects = []

            for select in page.locator("select").all():
                if not select.is_visible():
                    continue

                choices = (
                    select.locator("option")
                    .all_text_contents()
                )

                if any(
                    "2016" in x
                    for x in choices
                ):
                    selects.append(select)

            if len(selects) < 2:
                raise RuntimeError(
                    "No se localizaron los "
                    "dos selectores de periodo"
                )

            choose_year(selects[0], 2016)
            choose_year(
                selects[1],
                datetime.now().year,
            )

            page.get_by_role(
                "button",
                name="Consultar",
            ).click(timeout=15000)

            page.wait_for_timeout(2500)

            export = page.locator(
                'img[alt*="Excel"], '
                'img[title*="Excel"], '
                'a[title*="XLS"], '
                'a[title*="Excel"]'
            ).first

            if export.count() == 0:
                raise RuntimeError(
                    "No se identificó "
                    "el control XLS"
                )

            with page.expect_download(
                timeout=90000
            ) as task:
                export.click(timeout=15000)

            path = Path(folder) / "tabulado.xls"

            task.value.save_as(path)

            print(
                "ENEC desestacionalizada: "
                f"exportación recibida "
                f"({path.stat().st_size} bytes)",
                flush=True,
            )

            raw = path.read_bytes()

            for encoding in (
                "utf-8-sig",
                "cp1252",
                "latin1",
            ):
                try:
                    return raw.decode(encoding)
                except UnicodeDecodeError:
                    continue

            raise ValueError(
                "No se pudo leer la exportación"
            )

        except Exception:
            page.screenshot(
                path=str(
                    ROOT /
                    "diagnostico_enec_desestacionalizada.png"
                ),
                full_page=True,
            )

            (
                ROOT /
                "diagnostico_enec_desestacionalizada.html"
            ).write_text(
                page.content(),
                encoding="utf-8",
            )

            raise

        finally:
            browser.close()


def main():
    with TemporaryDirectory() as folder:
        html = download_html(folder)

    values = extract(html)

    if DEST.exists():
        with DEST.open(
            encoding="utf-8-sig",
            newline="",
        ) as file:
            old = list(csv.DictReader(file))

        old_periods = [
            row["periodo"]
            for row in old
            if row.get("periodo")
        ]

        if (
            old_periods
            and max(old_periods) > max(values)
        ):
            raise ValueError(
                "INEGI devolvió menos meses "
                "que el archivo existente"
            )

    output = io.StringIO(newline="")

    writer = csv.writer(
        output,
        lineterminator="\n",
    )

    writer.writerow([
        "periodo",
        "variacion_mensual_real",
    ])

    for period in sorted(values):
        writer.writerow([
            period,
            f"{values[period]:.6f}",
        ])

    temporary = DEST.with_suffix(
        ".csv.tmp"
    )

    temporary.write_text(
        output.getvalue(),
        encoding="utf-8",
    )

    temporary.replace(DEST)

    print(
        "ENEC Edificación mensual actualizada: "
        f"{min(values)} a {max(values)}; "
        f"{len(values)} meses",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as error:
        print(
            "ENEC desestacionalizada: "
            f"sin cambios por error: {error}",
            file=sys.stderr,
        )

        sys.exit(1)
