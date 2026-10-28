
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
    """Consulta INEGI y muestra información de diagnóstico."""

    body = json.dumps(
        payload(),
        ensure_ascii=False,
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

    try:
        with urllib.request.urlopen(
            req,
            timeout=90,
        ) as response:

            raw = response.read()

            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            print(
                f"INEGI PxWeb: HTTP {response.status}; "
                f"Content-Type={content_type}; "
                f"bytes={len(raw)}",
                flush=True,
            )

    except urllib.error.HTTPError as exc:

        excerpt = exc.read(1000).decode(
            "utf-8",
            errors="replace",
        )

        raise ValueError(
            f"INEGI PxWeb HTTP {exc.code}; "
            f"respuesta inicial: {excerpt[:500]!r}"
        ) from exc

    try:
        parsed = json.loads(raw)

    except (ValueError, UnicodeDecodeError) as exc:

        snippet = raw[:700].decode(
            "utf-8",
            errors="replace",
        )

        raise ValueError(
            f"INEGI devolvió respuesta no JSON "
            f"(Content-Type={content_type}): "
            f"{snippet!r}"
        ) from exc

    print(
        f"INEGI PxWeb: tipo={type(parsed).__name__}; "
        f"claves="
        f"{list(parsed)[:15] if isinstance(parsed, dict) else 'no es objeto'}",
        flush=True,
    )

    return parsed


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

    data = unwrap_jsonstat(data)

    if (
        data.get("class") not in (None, "dataset")
        or "dimension" not in data
        or "value" not in data
    ):
        raise ValueError(
            "Respuesta distinta de un conjunto "
            "de datos JSON-stat"
        )

    ids = data.get("id") or list(data["dimension"])

    dimcats = [
        categories(data["dimension"][key])
        for key in ids
    ]

    sizes = [len(x) for x in dimcats]

    expected_dims = [
        "Variable",
        "Tipo de dato",
        "Sector SCIAN",
        "Año",
        "Mes",
    ]

    if len(ids) != 5 or not all(
        any(
            key.lower() == name.lower()
            for key in ids
        )
        for name in expected_dims
    ):
        raise ValueError(
            f"Dimensiones inesperadas: {ids}"
        )

    if (
        data.get("size")
        and list(data["size"]) != sizes
    ):
        raise ValueError(
            "Dimensiones y tamaños inconsistentes"
        )

    values = data["value"]

    vi = next(
        i for i, name in enumerate(ids)
        if name.lower() == "variable"
    )

    yi = next(
        i for i, name in enumerate(ids)
        if name.lower() in ("año", "ano")
    )

    mi = next(
        i for i, name in enumerate(ids)
        if name.lower() == "mes"
    )

    ti = next(
        i for i, name in enumerate(ids)
        if name.lower() == "tipo de dato"
    )

    si = next(
        i for i, name in enumerate(ids)
        if name.lower() == "sector scian"
    )

    result = {}

    for flat_index, coords in enumerate(
        itertools.product(
            *(range(s) for s in sizes)
        )
    ):

        if isinstance(values, dict):
            v = values.get(str(flat_index))
        else:
            v = values[flat_index]

        if v in (None, "", ".."):
            continue

        code, variable_label = dimcats[vi][
            coords[vi]
        ]

        if code not in CODES:
            continue

        t_code, t_label = dimcats[ti][
            coords[ti]
        ]

        s_code, s_label = dimcats[si][
            coords[si]
        ]

        if t_code != "0" or s_code != "0":
            raise ValueError(
                f"Selección inesperada: "
                f"tipo {t_code}, sector {s_code}"
            )

        label_low = variable_label.lower()

        hints = {
            "29": "edific",
            "28": "públic",
            "21": "privad",
        }

        if (
            hints[code] not in label_low
            and hints[code].replace(
                "ú", "u"
            ) not in label_low
        ):
            raise ValueError(
                f"Código {code} no corresponde "
                f"a la variable esperada: "
                f"{variable_label}"
            )

        year_code, year_label = dimcats[yi][
            coords[yi]
        ]

        match = (
            re.search(
                r"(?:19|20)\d{2}",
                year_label,
            )
            or re.search(
                r"(?:19|20)\d{2}",
                year_code,
            )
        )

        if not match:
            raise ValueError(
                f"Año no reconocido: "
                f"{year_code} / {year_label}"
            )

        month_code, month_label = dimcats[mi][
            coords[mi]
        ]

        period = (
            f"{match.group(0)}-"
            f"{month_num(month_code, month_label):02d}"
        )

        if period < START:
            continue

        result.setdefault(period, {})[
            CODES[code]
        ] = float(v)

    complete = {
        p: row
        for p, row in result.items()
        if set(row) == set(CODES.values())
    }

    if len(complete) < 96:
        raise ValueError(
            f"Cobertura insuficiente: "
            f"{len(complete)} meses completos "
            f"desde {START}"
        )

    ordered = sorted(complete)

    for a, b in zip(
        ordered,
        ordered[1:],
    ):

        y, m = map(
            int,
            a.split("-"),
        )

        expected = (
            f"{y + (m == 12)}-"
            f"{(m % 12) + 1:02d}"
        )

        if b != expected:
            raise ValueError(
                f"Falta algún mes entre {a} y {b}"
            )

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
