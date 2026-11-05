
#!/usr/bin/env python3
"""Actualización del PIB de vivienda desde el INEGI.

Cuenta Satélite de Vivienda de México (CSVM).
Valores corrientes, sin alquiler imputado.

Descarga el XLSX mediante Playwright, valida los datos
y actualiza csvm_pib_vivienda_anual.csv.

CSVM_LOCAL_XLSX es opcional y solo sirve para pruebas.
"""

import csv
import io
import json
import os
import re
import sys
import unicodedata

from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]

OUTPUT = ROOT / "csvm_pib_vivienda_anual.csv"
STATUS = ROOT / "csvm_update_status.json"

FIELDS = [
    "anio",
    "pib_total_mdp",
    "participacion_pib_pct",
    "edificacion_mdp",
    "adquisicion_mdp",
    "uso_mdp",
    "regulacion_fomento_mdp",
    "fuente",
]

SOURCE = "INEGI · Cuenta Satélite de Vivienda de México"

TABULADO_URL = (
    "https://www.inegi.org.mx/app/tabulados/default.aspx"
    "?pr=24&vr=1&in=5&tp=20&wr=1&cno=1&idrt=3268&opc=p"
)


def norm(x):
    x = unicodedata.normalize(
        "NFKD", str(x or "")
    )

    return re.sub(
        r"\s+",
        " ",
        x.encode("ascii", "ignore").decode().lower()
    ).strip()


def number(x):
    if x is None or str(x).strip() in (
        "", "-", "N/D"
    ):
        raise ValueError(
            f"Valor numérico faltante: {x!r}"
        )

    return float(
        str(x).replace(",", "").strip()
    )


def parse_xlsx(content):
    """Extrae los datos del tabulado oficial."""

    wb = load_workbook(
        io.BytesIO(content),
        read_only=True,
        data_only=True,
    )

    if "Tabulado" in wb.sheetnames:
        ws = wb["Tabulado"]
    else:
        ws = wb.worksheets[0]

    # El INEGI utiliza ocho columnas por año.
    # La tercera contiene el VAB total.
    years = {}

    for cells in ws.iter_rows(
        min_row=1,
        max_row=min(ws.max_row, 15),
        values_only=True,
    ):
        for col, value in enumerate(cells):

            match = re.fullmatch(
                r"\s*(20\d{2})(?:\s*[PpRr])?\s*",
                str(value or ""),
            )

            if match:
                years[col] = int(match.group(1))

        if len(years) >= 3:
            break

    if len(years) < 3:
        raise ValueError(
            "No se detectaron suficientes años"
        )

    # Buscar filas por nombre, no por posición.
    rows = {}

    required = {
        "total nacional",
        "total vivienda",
        "edificacion",
        "adquisicion",
        "uso",
        "alquiler imputado",
        "regulacion y fomento",
    }

    for cells in ws.iter_rows(values_only=True):

        label = norm(cells[0])

        if label in required:

            if label in rows:
                raise ValueError(
                    "Etiqueta duplicada: " + label
                )

            rows[label] = cells

    missing = required - rows.keys()

    if missing:
        raise ValueError(
            "Faltan filas: "
            + ", ".join(sorted(missing))
        )

    result = {}

    for col, year in sorted(years.items()):

        vab_col = col + 2

        if vab_col >= ws.max_column:
            raise ValueError(
                f"No existe columna VAB para {year}"
            )

        def vab(label):
            return number(
                rows[label][vab_col]
            )

        # Valores corrientes con alquiler imputado
        national = vab("total nacional")
        housing = vab("total vivienda")
        imputed = vab("alquiler imputado")

        # PIB de vivienda sin alquiler imputado
        total = housing - imputed

        # Componentes
        ed = vab("edificacion")
        ad = vab("adquisicion")
        use = vab("uso") - imputed
        reg = vab("regulacion y fomento")

        if (
            national <= 0
            or total <= 0
            or min(ed, ad, use, reg) < 0
        ):
            raise ValueError(
                f"Valores inválidos en {year}"
            )

        subtotal = ed + ad + use + reg

        if abs(subtotal - total) > max(
            2, total * 0.0001
        ):
            raise ValueError(
                f"Los componentes no suman "
                f"el PIB total en {year}"
            )

        participation = 100 * total / national

        if not 0 < participation < 30:
            raise ValueError(
                f"Participación inválida en {year}"
            )

        result[year] = {
            "anio": year,
            "pib_total_mdp": round(total),
            "participacion_pib_pct": round(
                participation, 1
            ),
            "edificacion_mdp": round(ed),
            "adquisicion_mdp": round(ad),
            "uso_mdp": round(use),
            "regulacion_fomento_mdp": round(reg),
            "fuente": SOURCE,
        }

    return result


def old_rows():
    """Lee la información histórica del dashboard."""

    if not OUTPUT.exists():
        return {}

    with OUTPUT.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:

        return {
            int(r["anio"]): r
            for r in csv.DictReader(f)
        }


def read_source():
    """Descarga automáticamente desde el INEGI."""

    local = os.environ.get(
        "CSVM_LOCAL_XLSX", ""
    ).strip()

    if local:
        path = Path(local)

        if not path.is_absolute():
            path = ROOT / path

        return path.read_bytes(), str(path)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:

        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox"],
        )

        try:
            context = browser.new_context(
                accept_downloads=True,
                locale="es-MX",
                viewport={
                    "width": 1440,
                    "height": 900,
                },
            )

            page = context.new_page()

            page.goto(
                TABULADO_URL,
                wait_until="domcontentloaded",
                timeout=90000,
            )

            page.wait_for_timeout(3500)

            # Buscar el botón de exportación XLSX.
            selectors = [
                "a:has(img[src*='xlsx'])",
                "a:has(img[alt*='XLSX'])",
                "a:has(img[title*='XLSX'])",
                "img[src*='xlsx']",
                "img[alt*='XLSX']",
                "img[title*='XLSX']",
                "a[title*='XLSX']",
                "a[title*='Excel']",
            ]

            candidates = []

            for frame in page.frames:

                for selector in selectors:

                    locator = frame.locator(selector)

                    try:
                        if (
                            locator.count()
                            and locator.first.is_visible()
                        ):
                            candidates.append(
                                (frame, selector)
                            )

                    except Exception:
                        pass

            if not candidates:
                raise RuntimeError(
                    "No se encontró el botón XLSX "
                    "en el tabulado del INEGI"
                )

            download_errors = []

            for frame, selector in candidates:

                try:
                    with page.expect_download(
                        timeout=30000
                    ) as item:

                        frame.locator(
                            selector
                        ).first.click(
                            timeout=12000
                        )

                    download = item.value

                    failure = download.failure()

                    if failure:
                        raise RuntimeError(
                            "Descarga fallida: " + failure
                        )

                    data = Path(
                        download.path()
                    ).read_bytes()

                    if not data.startswith(
                        b"PK\x03\x04"
                    ):
                        raise ValueError(
                            "La exportación no devolvió "
                            "un XLSX válido"
                        )

                    return data, TABULADO_URL

                except Exception as exc:
                    download_errors.append(
                        f"{selector}: "
                        f"{type(exc).__name__}: {exc}"
                    )

            raise RuntimeError(
                "El INEGI mostró el botón XLSX "
                "pero no generó una descarga. "
                + " | ".join(download_errors[:4])
            )

        finally:
            browser.close()


def write_status(state, **kwargs):
    """Registra el estado de la actualización."""

    payload = {
        "status": state,
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

    try:
        data, origin = read_source()

        fresh = parse_xlsx(data)
        previous = old_rows()

        if previous and max(fresh) < max(previous):
            raise ValueError(
                "El Excel es anterior al último "
                "año publicado"
            )

        # Comprobar revisiones históricas.
        for year in set(fresh) & set(previous):

            old = float(
                previous[year]["pib_total_mdp"]
            )

            new = float(
                fresh[year]["pib_total_mdp"]
            )

            if (
                old
                and abs(new - old) / abs(old) > 0.10
            ):
                raise ValueError(
                    f"Revisión superior al 10% "
                    f"en {year}"
                )

        # Conservar el histórico y actualizar.
        combined = {
            **previous,
            **fresh,
        }

        before = (
            OUTPUT.read_text(
                encoding="utf-8-sig"
            )
            if OUTPUT.exists()
            else ""
        )

        output = io.StringIO()

        writer = csv.DictWriter(
            output,
            fieldnames=FIELDS,
            lineterminator="\n",
        )

        writer.writeheader()

        for year in sorted(combined):
            writer.writerow({
                k: combined[year].get(k, "")
                for k in FIELDS
            })

        after = output.getvalue()

        changed = after != before

        if changed:
            OUTPUT.write_text(
                after,
                encoding="utf-8",
            )

        write_status(
            "actualizado"
            if changed
            else "sin_cambios",
            fuente=origin,
            primer_anio=min(combined),
            ultimo_anio=max(combined),
            anios_descargados=len(fresh),
        )

        print(
            f"CSVM: validado "
            f"{min(fresh)}-{max(fresh)}; "
            f"cambios={changed}"
        )

        return 0

    except Exception as exc:

        write_status(
            "conservado_sin_cambio",
            error=(
                f"{type(exc).__name__}: {exc}"
            ),
        )

        print(
            "CSVM: NO actualizada; "
            f"históricos conservados: {exc}",
            file=sys.stderr,
        )

        return 1


if __name__ == "__main__":
    sys.exit(main())
