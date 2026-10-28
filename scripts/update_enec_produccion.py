
#!/usr/bin/env python3
"""Actualización ENEC mediante el servicio PxWeb de INEGI."""

import csv
import itertools
import json
import re
import statistics
import sys
import urllib.request
import urllib.error

from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEST = ROOT / "enec_actividad_historica.csv"
STATUS = ROOT / "enec_produccion_update_status.json"

URL = "https://www.inegi.org.mx/app/tabulados/pxwebapi/api/datatable"

START = "2016-01"

CODES = {
    "29": "edificacion_indice",
    "28": "publico_indice",
    "21": "privado_indice",
}

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def payload():
    return {
        "query": {
            "query": [
                {
                    "code": "Variable",
                    "selection": {
                        "filter": "item",
                        "values": list(CODES),
                    },
                },
                {
                    "code": "Tipo de dato",
                    "selection": {
                        "filter": "item",
                        "values": ["0"],
                    },
                },
                {
                    "code": "Sector SCIAN",
                    "selection": {
                        "filter": "item",
                        "values": ["0"],
                    },
                },
                {
                    "code": "Año",
                    "selection": {
                        "filter": "all",
                        "values": ["*"],
                    },
                },
                {
                    "code": "Mes",
                    "selection": {
                        "filter": "all",
                        "values": ["*"],
                    },
                },
            ],
            "response": {
                "format": "json-stat",
            },
        },
        "lang": "es",
        "file": "ENEC/ENEC_NACIONAL_36",
        "stub": [
            "Variable",
            "Tipo de dato",
            "Sector SCIAN",
        ],
        "heading": [
            "Año",
            "Mes",
        ],
    }



def fetch():
    """Consulta ENEC y examina la estructura real del tabulado."""

    body = json.dumps(
        payload(),
        ensure_ascii=False
    ).encode("utf-8")

    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )

    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read()
        print(
            f"INEGI: HTTP {response.status}; "
            f"bytes={len(raw)}",
            flush=True
        )

    result = json.loads(raw)

    print("=== ESTRUCTURA DE RESPUESTA ENEC ===", flush=True)
    print("Claves:", list(result.keys()), flush=True)
    print("rowCount:", result.get("rowCount"), flush=True)
    print("colCount:", result.get("colCount"), flush=True)
    print("matrixSize:", result.get("matrixSize"), flush=True)

    for field in ("heading", "stub", "notes"):
        print(
            f"{field}:",
            json.dumps(
                result.get(field),
                ensure_ascii=False,
                default=str
            )[:5000],
            flush=True
        )

    values = result.get("data", [])

    print(
        "Cantidad de elementos data:",
        len(values),
        flush=True
    )

    print(
        "Primeros 12 elementos data:",
        json.dumps(
            values[:12],
            ensure_ascii=False,
            default=str
        ),
        flush=True
    )

    print("=== FIN DEL DIAGNÓSTICO ===", flush=True)

    return result



def unwrap_jsonstat(data):
    """Reconoce JSON-stat directo o envuelto."""

    for level in range(4):

        if (
            isinstance(data, dict)
            and "dimension" in data
            and "value" in data
        ):
            return data

        if isinstance(data, dict):

            next_data = next(
                (
                    data[key]
                    for key in (
                        "dataset",
                        "data",
                        "result",
                        "results",
                    )
                    if key in data
                    and isinstance(data[key], dict)
                ),
                None,
            )

            if next_data is not None:
                data = next_data
                continue

        break

    if isinstance(data, dict):

        keys = list(data)[:18]

        preview = json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        )[:900]

        raise ValueError(
            f"JSON recibido sin dimension/value. "
            f"Claves={keys}; "
            f"fragmento={preview}"
        )

    raise ValueError(
        f"Formato JSON no compatible: "
        f"{type(data).__name__}; "
        f"fragmento={str(data)[:500]}"
    )


def categories(d):

    c = d["category"]
    ix = c["index"]

    if isinstance(ix, dict):
        pairs = sorted(
            ix.items(),
            key=lambda kv: kv[1],
        )
    else:
        pairs = list(enumerate(ix))

    labels = c.get("label", {})

    return [
        (str(k), str(labels.get(k, k)))
        for k, _ in pairs
    ]


def month_num(code, label):

    for s in (label, code):

        n = str(s).strip().lower()

        if n in MONTHS:
            return MONTHS[n]

        if n.isdigit() and 1 <= int(n) <= 12:
            return int(n)

        m = re.match(r"^([01]?\d)[-/.]", n)

        if m and 1 <= int(m.group(1)) <= 12:
            return int(m.group(1))

    raise ValueError(
        f"Mes no reconocido: {code!r} / {label!r}"
    )



def extract(data):
    """
    Lee la respuesta real de INEGI PxWeb /datatable.

    La matriz contiene:
    - 3 filas: edificación, público y privado
    - 252 columnas: enero 2006 a diciembre 2026
    - Valores con formato '116.6||'

    Conserva desde enero de 2016 los meses
    con las tres observaciones disponibles.
    """

    if not isinstance(data, dict):
        raise ValueError("INEGI no devolvió un objeto JSON")

    required = {
        "data", "heading", "stub",
        "rowCount", "colCount"
    }

    if not required.issubset(data):
        raise ValueError(
            "Respuesta incompleta: "
            + str(list(data.keys()))
        )

    headings = data["heading"]
    stubs = data["stub"]
    values = data["data"]

    years = next(
        x["label"] for x in headings
        if x["code"] == "Año"
    )

    months = next(
        x["label"] for x in headings
        if x["code"] == "Mes"
    )

    variables = next(
        x["label"] for x in stubs
        if x["code"] == "Variable"
    )

    sector = next(
        x["label"] for x in stubs
        if x["code"] == "Sector SCIAN"
    )

    tipo = next(
        x["label"] for x in stubs
        if x["code"] == "Tipo de dato"
    )

    if sector != ["23 Construcción"]:
        raise ValueError(
            f"Sector SCIAN inesperado: {sector}"
        )

    if tipo != ["Dato"]:
        raise ValueError(
            f"Tipo de dato inesperado: {tipo}"
        )

    expected_variables = [
        ("edificacion_indice", "edificación"),
        ("publico_indice", "público"),
        ("privado_indice", "privado"),
    ]

    if len(variables) != 3:
        raise ValueError(
            f"Se esperaban 3 variables: {variables}"
        )

    import unicodedata

    def normalize(value):
        value = unicodedata.normalize(
            "NFD", str(value).lower()
        )
        return "".join(
            c for c in value
            if unicodedata.category(c) != "Mn"
        )

    for i, (_, expected) in enumerate(expected_variables):
        if normalize(expected) not in normalize(variables[i]):
            raise ValueError(
                f"Variable inesperada en fila {i}: "
                f"{variables[i]}"
            )

    if len(months) != 12:
        raise ValueError("No se recibieron los 12 meses")

    if len(set(map(str, years))) != len(years):
        raise ValueError("Años duplicados")

    for year in years:
        if not str(year).isdigit() or len(str(year)) != 4:
            raise ValueError(f"Año inválido: {year}")

    ncols = len(years) * len(months)
    nrows = len(variables)

    if data["rowCount"] != nrows:
        raise ValueError("Número de filas incorrecto")

    if data["colCount"] != ncols:
        raise ValueError("Número de columnas incorrecto")

    if len(values) != nrows * ncols:
        raise ValueError(
            f"Matriz incompleta: {len(values)} valores; "
            f"esperados {nrows * ncols}"
        )

    result = {}

    for row_idx, (column, _) in enumerate(
        expected_variables
    ):

        for col_idx in range(ncols):

            year_idx = col_idx // 12
            month_idx = col_idx % 12

            year = str(years[year_idx])
            month = month_idx + 1

            period = f"{year}-{month:02d}"

            if period < START:
                continue

            position = row_idx * ncols + col_idx
            raw = values[position]

            if raw is None:
                continue

            # INEGI devuelve por ejemplo "116.6||".
            number = str(raw).split("|")[0].strip()

            if number in ("", ".", "..", "...", "N/D"):
                continue

            try:
                value = float(number.replace(",", ""))

            except ValueError:
                raise ValueError(
                    f"Valor no numérico en {period}, "
                    f"{column}: {raw}"
                )

            import math

            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"Valor inválido en {period}: {value}"
                )

            result.setdefault(period, {})[column] = value

    expected_columns = set(CODES.values())

    complete = {
        period: row
        for period, row in result.items()
        if set(row) == expected_columns
    }

    if not complete:
        raise ValueError("INEGI no devolvió meses completos")

    periods = sorted(complete)

    # Exigir histórico desde enero de 2016.
    if periods[0] != "2016-01":
        raise ValueError(
            f"El histórico comienza en {periods[0]}, "
            "no en 2016-01"
        )

    # Comprobar continuidad mensual.
    for previous, following in zip(
        periods, periods[1:]
    ):

        year, month = map(int, previous.split("-"))

        next_year = year + (month == 12)
        next_month = month % 12 + 1

        expected = f"{next_year}-{next_month:02d}"

        if following != expected:
            raise ValueError(
                f"Faltan observaciones entre "
                f"{previous} y {following}"
            )

    if len(periods) < 96:
        raise ValueError(
            "Cobertura insuficiente desde 2016"
        )

    print("=== ENEC: CONSULTA INTERPRETADA ===")
    print("Variables oficiales:", variables)
    print("Sector:", sector)
    print("Primer periodo:", periods[0])
    print("Último periodo:", periods[-1])
    print("Meses completos:", len(periods))

    print("Primer registro:", complete[periods[0]])
    print("Último registro:", complete[periods[-1]])

    print("=== VALIDACIÓN COMPLETADA ===")

    return complete



def prior_rows():

    if not DEST.exists():
        return []

    with DEST.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def save(rows):

    fields = [
        "periodo",
        "edificacion_indice",
        "publico_indice",
        "privado_indice",
        "unidad",
        "fuente",
        "nota",
    ]

    tmp = DEST.with_suffix(".csv.tmp")

    with tmp.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()

        for period, vals in sorted(
            rows.items()
        ):

            writer.writerow({
                "periodo": period,
                **{
                    k: f"{v:.6f}"
                    for k, v in vals.items()
                },
                "unidad": "índice 2018=100",
                "fuente": (
                    "INEGI - ENEC; "
                    "ENEC_NACIONAL_36"
                ),
                "nota": (
                    "Índices del sector 23: "
                    "edificación, sector público "
                    "y sector privado"
                ),
            })

    tmp.replace(DEST)


def create_excel(rows):
    """Genera Excel a partir de los datos oficiales."""

    try:
        from artifact_tool import (
            Workbook,
            SpreadsheetFile,
        )

        book = Workbook.create()

        ws = book.worksheets.add(
            "ENEC_indices"
        )

        headers = [
            "Periodo",
            "Índice de edificación",
            "Índice sector público",
            "Índice sector privado",
        ]

        data = [headers] + [
            [
                period,
                float(values[
                    "edificacion_indice"
                ]),
                float(values[
                    "publico_indice"
                ]),
                float(values[
                    "privado_indice"
                ]),
            ]
            for period, values in sorted(
                rows.items()
            )
        ]

        ws.get_range_by_indexes(
            0, 0, len(data), 4
        ).values = data

        outfile = (
            ROOT /
            "enec_produccion_inegi.xlsx"
        )

        temporary = (
            ROOT /
            "enec_produccion_inegi.tmp.xlsx"
        )

        SpreadsheetFile.export_xlsx(
            book
        ).save(str(temporary))

        temporary.replace(outfile)

        return "generado"

    except ImportError:

        print(
            "Aviso: artifact_tool no disponible; "
            "CSV y JSON oficiales conservados.",
            file=sys.stderr,
        )

        return "biblioteca_no_disponible"


def main():

    report = {
        "consultado_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "fuente": URL,
        "tabla": "ENEC/ENEC_NACIONAL_36",
        "estado": "sin_validar",
    }

    try:

        response = fetch()

        data = extract(response)

        existing = prior_rows()

        prev_latest = max(
            (
                r["periodo"]
                for r in existing
            ),
            default="",
        )

        latest = max(data)

        if latest < prev_latest:
            raise ValueError(
                f"La fuente termina en {latest}; "
                f"el histórico actual llega "
                f"a {prev_latest}"
            )

        differences = {}

        previous_by_period = {
            r["periodo"]: r
            for r in existing
        }

        for key in CODES.values():

            discrepancies = []

            for period, row in data.items():

                old = previous_by_period.get(
                    period
                )

                if not old or not old.get(key):
                    continue

                old_num = float(old[key])
                new_num = row[key]

                discrepancies.append(
                    abs(old_num - new_num)
                    / max(abs(old_num), 1.0)
                )

            if discrepancies:

                differences[key] = round(
                    statistics.median(
                        discrepancies
                    ),
                    5,
                )

        report.update(
            ultimo=latest,
            primero=min(data),
            meses=len(data),
            error_relativo_mediano_vs_csv=differences,
        )

        changed = (
            len(existing) != len(data)
        ) or any(
            old is None or any(
                abs(
                    float(
                        old.get(k, "nan")
                    ) - row[k]
                ) > 1e-7
                for k in CODES.values()
            )
            for period, row in data.items()
            for old in [
                previous_by_period.get(
                    period
                )
            ]
        )

        # Sustituir histórico por la fuente oficial.
        if changed:

            save(data)

            report["estado"] = (
                "actualizado_fuente_oficial"
            )

        else:

            report["estado"] = (
                "sin_cambios"
            )

        # Guardar respuesta original.
        raw_path = (
            ROOT /
            "enec_produccion_inegi_original.json"
        )

        raw_tmp = raw_path.with_suffix(
            ".json.tmp"
        )

        raw_tmp.write_text(
            json.dumps(
                response,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        raw_tmp.replace(raw_path)

        excel_status = create_excel(data)

        report["archivo_excel"] = (
            excel_status
        )

        print(
            f"ENEC {report['estado']}: "
            f"{min(data)} a {latest}; "
            f"diferencias={differences}"
        )

        return 0

    except Exception as exc:

        report.update(
            estado="conservado_sin_cambio",
            error=str(exc),
        )

        print(
            f"ENEC producción: {exc}",
            file=sys.stderr,
        )

        return 1

    finally:

        STATUS.write_text(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    sys.exit(main())
