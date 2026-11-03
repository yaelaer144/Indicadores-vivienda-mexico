
#!/usr/bin/env python3
"""Actualización automática ENOE desde INEGI InfoLaboral.

Descarga población ocupada nacional y construcción desde 2016.
No requiere cargar archivos Excel manualmente.
"""

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "enoe_construccion_trimestral.csv"
STATUS = ROOT / "enoe_update_status.json"

URL = (
    "https://www.inegi.org.mx/sistemas/"
    "infoenoe/Default_15mas.aspx"
)


def read_existing():
    if not OUT.exists():
        return []

    with OUT.open(
        newline="",
        encoding="utf-8-sig"
    ) as f:
        return list(csv.DictReader(f))


def parse_table(html):
    """Extrae las series de la tabla oficial reporte1."""

    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="reporte1")

    if table is None:
        raise ValueError(
            "No se encontró reporte1 en la respuesta del INEGI"
        )

    rows = [
        [
            c.get_text(" ", strip=True).replace("\xa0", " ")
            for c in tr.find_all(
                ["td", "th"], recursive=False
            )
        ]
        for tr in table.find_all("tr")
    ]

    header_idx = next(
        (
            i for i, cells in enumerate(rows)
            if cells and cells[0] == "Indicadores"
        ),
        None
    )

    if header_idx is None or header_idx + 2 >= len(rows):
        raise ValueError(
            "Cabeceras de años y trimestres no reconocidas"
        )

    years = rows[header_idx]
    quarters = rows[header_idx + 1]

    labels = {
        "Primer trimestre": 1,
        "Segundo trimestre": 2,
        "Tercer trimestre": 3,
        "Cuarto trimestre": 4
    }

    periods = []

    for year, quarter in zip(
        years[1:], quarters[1:]
    ):
        if (
            not re.fullmatch(r"20\d{2}", year)
            or quarter not in labels
        ):
            raise ValueError(
                f"Cabecera no reconocida: {year}, {quarter}"
            )

        periods.append(
            f"{year}-T{labels[quarter]}"
        )

    if (
        len(set(periods)) != len(periods)
        or periods != sorted(periods)
    ):
        raise ValueError(
            "Trimestres repetidos o desordenados"
        )

    def find_row(label):
        matches = [
            r for r in rows[header_idx + 3:]
            if (
                len(r) == len(periods) + 1
                and r[0].strip() == label
            )
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Fila {label}: "
                f"se encontraron {len(matches)} coincidencias"
            )

        values = {}

        for period, value in zip(
            periods, matches[0][1:]
        ):
            n = value.replace(",", "").replace(" ", "")

            if not re.fullmatch(r"\d+", n):
                raise ValueError(
                    f"Valor no numérico: "
                    f"{label} {period} = {value}"
                )

            values[period] = int(n)

        return values

    national = find_row("Población ocupada")
    construction = find_row("Construcción")

    if (
        len(periods) < 35
        or periods[0] != "2016-T1"
        or "2020-T2" in periods
    ):
        raise ValueError(
            "La consulta no cubre correctamente "
            "los trimestres desde 2016"
        )

    for period in periods:
        if not (
            30_000_000 <= national[period] <= 100_000_000
        ):
            raise ValueError(
                f"Población nacional fuera de rango: {period}"
            )

        if not (
            1_000_000 <= construction[period] <= 12_000_000
        ):
            raise ValueError(
                f"Construcción fuera de rango: {period}"
            )

        if construction[period] >= national[period]:
            raise ValueError(
                f"Construcción supera población nacional: {period}"
            )

    if (
        national["2016-T1"] != 50_029_049
        or construction["2016-T1"] != 4_074_858
    ):
        raise ValueError(
            "No coinciden los valores de control de 2016-T1"
        )

    return [
        {
            "periodo": period,
            "total": f"{construction[period] / 1000:.3f}",
            "ocupada_total": f"{national[period] / 1000:.3f}",
            "formal": "",
            "informal": ""
        }
        for period in periods
    ]


SET_CHECKBOXES_JS = r'''({mode, fromYear}) => {

    const normalize = s =>
        (s || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();

    const inputs = Array.from(
        document.querySelectorAll('input[type="checkbox"]')
    );

    const getLabel = el => {

        const associated = Array.from(
            document.querySelectorAll("label[for]")
        ).find(l => l.htmlFor === el.id);

        if (
            associated
            && associated.textContent.trim()
        ) {
            return normalize(associated.textContent);
        }

        let node = el.nextSibling;

        for (
            let i = 0;
            node && i < 5;
            i++, node = node.nextSibling
        ) {
            if (
                node.textContent
                && node.textContent.trim()
            ) {
                return normalize(node.textContent);
            }
        }

        return normalize(
            el.parentElement?.textContent || ""
        );
    };

    const updated = [];
    const found = [];

    for (const el of inputs) {

        const label = getLabel(el);
        const value = (el.value || "").trim();

        let desired = null;
        let year = null;

        if (mode === "variables") {

            if (
                /^3\.2\. sector de actividad economica/.test(label)
            ) {
                desired = true;
            }

            if (/^poblacion ocupada$/.test(label)) {
                desired = true;
            }

            if (
                /^3\.1\. posicion en la ocupacion/.test(label)
            ) {
                desired = false;
            }

        } else if (mode === "years") {

            const fromValue = /^20\d{2}$/.test(value)
                ? Number(value) : null;

            const fromLabel = /^20\d{2}$/.test(label)
                ? Number(label) : null;

            year = fromValue !== null
                ? fromValue : fromLabel;

            if (
                year !== null
                && year >= 2005
                && year <= 2099
            ) {
                desired = year >= fromYear;
            }
        }

        if (desired !== null) {

            if (el.checked !== desired) {

                el.checked = desired;

                el.dispatchEvent(
                    new Event("input", {bubbles: true})
                );

                el.dispatchEvent(
                    new Event("change", {bubbles: true})
                );
            }

            updated.push({
                label,
                value,
                year,
                checked: el.checked,
                desired,
                id: el.id
            });
        }

        if (
            mode === "years"
            && year !== null
        ) {
            found.push(year);
        }
    }

    return {
        updated,
        yearsFound: found,
        checkboxCount: inputs.length
    };
}'''


def fetch_live():
    """Consulta InfoLaboral mediante Playwright."""

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        try:
            page = browser.new_page(
                locale="es-MX",
                viewport={
                    "width": 1600,
                    "height": 1000
                }
            )

            page.set_default_timeout(35000)

            response = page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=90000
            )

            if (
                response is None
                or response.status >= 400
            ):
                raise RuntimeError(
                    "InfoLaboral no abrió correctamente"
                )

            # 1. Abrir Indicadores estratégicos.
            page.locator("#btngind").click()

            # 2. Seleccionar variables.
            page.locator("#btngind_ind").click()

            page.get_by_text(
                "3.2. Sector de actividad económica",
                exact=True
            ).wait_for(
                state="visible",
                timeout=60000
            )

            variables = page.evaluate(
                SET_CHECKBOXES_JS,
                {
                    "mode": "variables",
                    "fromYear": 2016
                }
            )

            if not any(
                "3.2." in x["label"] and x["checked"]
                for x in variables["updated"]
            ):
                raise RuntimeError(
                    "No se seleccionó el sector construcción"
                )

            print(
                "ENOE: variables seleccionadas",
                flush=True
            )

            # 3. Abrir Coberturas y sexo.
            page.locator("#btngind_cob").click()

            page.locator(
                "#cblgind_ano_11"
            ).wait_for(
                state="visible",
                timeout=60000
            )

            # 4. Nacional - Total.
            nacional = page.locator(
                "#cblgind_nal_0"
            )

            if not nacional.is_checked():
                nacional.check(timeout=30000)

            print(
                "ENOE: Nacional - Total seleccionado",
                flush=True
            )

            # 5. Seleccionar años desde 2016.
            seleccion = page.evaluate(
                SET_CHECKBOXES_JS,
                {
                    "mode": "years",
                    "fromYear": 2016
                }
            )

            marcados = [
                x["year"]
                for x in seleccion["updated"]
                if x["checked"]
            ]

            if 2016 not in marcados:
                raise RuntimeError(
                    "No se pudo seleccionar 2016"
                )

            print(
                "ENOE años seleccionados: "
                + json.dumps(marcados),
                flush=True
            )

            # 6. Seleccionar los cuatro trimestres.
            # Usamos interacciones reales con Playwright.
            print(
                "ENOE: seleccionando cuatro trimestres",
                flush=True
            )

            page.locator(
                "#cblgind_tri_0"
            ).wait_for(
                state="visible",
                timeout=30000
            )

            for i in range(4):

                casilla = page.locator(
                    f"#cblgind_tri_{i}"
                )

                if not casilla.is_checked():
                    casilla.check(timeout=30000)

                if not casilla.is_checked():
                    raise RuntimeError(
                        f"No se pudo seleccionar trimestre {i + 1}"
                    )

            # 7. Validar todas las selecciones.
            estado = page.evaluate("""() => ({
                nacional: !!document.querySelector(
                    '#cblgind_nal_0'
                )?.checked,

                sexoTotal: !!document.querySelector(
                    '#rblgind_sex_0'
                )?.checked,

                absolutos: !!document.querySelector(
                    '#rblabs_rel_0'
                )?.checked,

                anio2016: !!document.querySelector(
                    '#cblgind_ano_11'
                )?.checked,

                trimestres: [0,1,2,3].map(i =>
                    !!document.querySelector(
                        '#cblgind_tri_' + i
                    )?.checked
                ),

                consultarHabilitado: !document.querySelector(
                    '#btngind_con'
                )?.disabled
            })""")

            print(
                "ENOE selección final: "
                + json.dumps(
                    estado,
                    ensure_ascii=False
                ),
                flush=True
            )

            if not all([
                estado["nacional"],
                estado["sexoTotal"],
                estado["absolutos"],
                estado["anio2016"],
                *estado["trimestres"]
            ]):
                raise RuntimeError(
                    "InfoLaboral no conservó todas "
                    "las selecciones: "
                    + json.dumps(
                        estado,
                        ensure_ascii=False
                    )
                )

            # 8. Esperar a que Consultar esté habilitado.
            if not estado["consultarHabilitado"]:

                try:
                    page.wait_for_function(
                        """() => {
                            const boton = document.querySelector(
                                '#btngind_con'
                            );
                            return boton && !boton.disabled;
                        }""",
                        timeout=10000
                    )

                except Exception:
                    raise RuntimeError(
                        "Consultar continúa deshabilitado "
                        "con cobertura, años y trimestres "
                        "seleccionados: "
                        + json.dumps(
                            estado,
                            ensure_ascii=False
                        )
                    )

            # 9. Ejecutar la consulta.
            print(
                "ENOE: ejecutando consulta InfoLaboral",
                flush=True
            )

            page.locator(
                "#btngind_con"
            ).click(
                timeout=30000
            )

            # 10. Esperar la tabla oficial.
            page.locator(
                "#reporte1"
            ).wait_for(
                state="attached",
                timeout=90000
            )

            content = page.locator(
                "#reporte1"
            ).evaluate(
                "(el) => el.outerHTML"
            )

            return parse_table(content)

        finally:
            browser.close()


def main():

    status = {
        "checked_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source": (
            "INEGI ENOE InfoLaboral "
            "(consulta automática HTML)"
        ),
        "units": "miles de personas",
        "updated": False
    }

    try:
        rows = fetch_live()
        previous = read_existing()

        last_old = max(
            (
                r.get("periodo", "")
                for r in previous
            ),
            default=""
        )

        if rows[-1]["periodo"] < last_old:
            raise ValueError(
                "Fuente retrocedió de "
                f"{last_old} a {rows[-1]['periodo']}"
            )

        old_map = {
            r["periodo"]: r
            for r in previous
        }

        # Conservar columnas históricas adicionales.
        for row in rows:

            old = old_map.get(
                row["periodo"]
            )

            if old:
                for field in (
                    "formal",
                    "informal"
                ):
                    row[field] = old.get(
                        field, ""
                    )

        tmp = OUT.with_suffix(
            ".csv.tmp"
        )

        with tmp.open(
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "periodo",
                    "total",
                    "ocupada_total",
                    "formal",
                    "informal"
                ]
            )

            writer.writeheader()
            writer.writerows(rows)

        tmp.replace(OUT)

        status.update(
            updated=True,
            first_quarter=rows[0]["periodo"],
            last_quarter=rows[-1]["periodo"],
            observations=len(rows),
            gap_2020_T2=True
        )

        print(
            "ENOE automática: "
            f"{rows[0]['periodo']} "
            f"a {rows[-1]['periodo']}; "
            f"{len(rows)} observaciones",
            flush=True
        )

    except Exception as exc:

        status["error"] = str(exc)

        print(
            f"ERROR ENOE InfoLaboral: {exc}",
            flush=True
        )

        raise

    finally:
        STATUS.write_text(
            json.dumps(
                status,
                ensure_ascii=False,
                indent=2
            ) + "\n",
            encoding="utf-8"
        )


if __name__ == "__main__":
    main()
