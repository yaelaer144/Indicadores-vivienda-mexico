
#!/usr/bin/env python3
"""Actualiza el respaldo persistente de Producción SNIIV/RUV.

Conserva el respaldo previo si la API falla o cambia su esquema.
No modifica el flujo de registro, verificación y terminación.
"""

import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "ruv-produccion.js"
JSON = ROOT / "ruv_produccion_caracteristicas.json"
STATUS = ROOT / "ruv_produccion_update_status.json"

API = "https://sniiv.sedatu.gob.mx/api/CuboAPI/GetProduccion"
START = 2016
END = datetime.now().year

CATS = [
    "Económica",
    "Popular B1",
    "Popular B2",
    "Popular B3",
    "Tradicional",
    "Media-residencial",
]


def norm(value):
    s = unicodedata.normalize(
        "NFKD", str(value or "").strip().lower()
    )
    return "".join(
        c for c in s if not unicodedata.combining(c)
    )


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
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def integer(value, label):
    if isinstance(value, str):
        value = value.replace(",", "").strip()

    number = float(value)

    if (
        not math.isfinite(number)
        or number < 0
        or abs(number - round(number)) > 1e-6
    ):
        raise ValueError(
            f"{label} inválido: {value}"
        )

    return int(round(number))


def parse_month(value):
    """Acepta meses numéricos y nombres en español."""

    if isinstance(value, str):
        label = norm(value).strip().rstrip(".")

        if label in MONTHS:
            return MONTHS[label]

        abbreviations = {
            k[:3]: v for k, v in MONTHS.items()
        }

        if label in abbreviations:
            return abbreviations[label]

    return integer(value, "mes")


def segment(value):
    s = norm(value)

    if s == "economica":
        return "Económica"

    if "popular" in s:
        if "128" in s or s in ("popular b1", "b1"):
            return "Popular B1"

        if "158" in s or s in ("popular b2", "b2"):
            return "Popular B2"

        if "200" in s or s in ("popular b3", "b3"):
            return "Popular B3"

    if s == "tradicional":
        return "Tradicional"

    if s in (
        "media",
        "residencial",
        "residencial plus",
        "media-residencial",
        "media residencial",
    ):
        return "Media-residencial"

    return None


def load_old():
    if JSON.exists():
        return json.loads(
            JSON.read_text(encoding="utf-8-sig")
        )

    if JS.exists():
        content = JS.read_text(
            encoding="utf-8-sig"
        )

        content = re.sub(
            r"^\s*window\.RUV_PRODUCTION\s*=\s*",
            "",
            content,
        )

        return json.loads(
            content.strip().rstrip(";")
        )

    raise FileNotFoundError(
        "No existe respaldo RUV de producción"
    )


def main():
    old = load_old()

    url = (
        f"{API}/{START},{END}/00/000/"
        "anio,mes,segmento"
    )

    req = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(compatible; vivienda-dashboard/1.0)"
            ),
            "Accept": "application/json",
        },
    )

    with urlopen(req, timeout=90) as resp:
        if resp.status != 200:
            raise RuntimeError(
                f"HTTP {resp.status}"
            )

        rows = json.load(resp)

    if not isinstance(rows, list) or len(rows) < 10:
        raise RuntimeError(
            "Respuesta SNIIV vacía o formato inesperado"
        )

    annual = defaultdict(
        lambda: defaultdict(int)
    )
    monthly = defaultdict(set)
    max_period = None

    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError(
                "Fila no tabular"
            )

        y = integer(
            row.get(
                "anio",
                row.get("año", row.get("year"))
            ),
            "año",
        )

        m = parse_month(
            row.get("mes", row.get("month"))
        )

        if (
            not START <= y <= END
            or not 1 <= m <= 12
        ):
            raise RuntimeError(
                f"Periodo inválido: {y}-{m}"
            )

        category = segment(
            row.get("segmento")
        )

        if category is None:
            raise RuntimeError(
                "Segmento desconocido: "
                f"{row.get('segmento')!r}; "
                "no se sobrescribe el respaldo"
            )

        qty = integer(
            row.get("viviendas"),
            "viviendas",
        )

        annual[y][category] += qty
        monthly[y].add(m)

        if qty:
            max_period = max(
                max_period or (y, m),
                (y, m),
            )

    if (
        len(annual) < 3
        or not any(y >= END - 1 for y in annual)
    ):
        raise RuntimeError(
            "La API no devolvió cobertura "
            "reciente suficiente"
        )

    new_segment = {}
    new_total = {}

    for y in sorted(annual):
        months = monthly[y]

        values = {
            cat: annual[y].get(cat, 0)
            for cat in CATS
        }

        total = sum(values.values())

        if total <= 0:
            continue

        partial = len(months) < 12

        new_segment[y] = {
            "year": y,
            "months_observed": max(months),
            "partial": partial,
            "total": total,
            "values": values,
        }

        new_total[y] = {
            "year": y,
            "months_observed": max(months),
            "partial": partial,
            "total": total,
        }

    def merge(existing, incoming):
        result = {
            int(x["year"]): x
            for x in existing
        }

        for y, item in incoming.items():
            previous = result.get(y)

            if (
                previous
                and not previous.get("partial", False)
                and item.get("partial", False)
            ):
                continue

            result[y] = item

        return [
            result[y] for y in sorted(result)
        ]

    output = dict(old)

    output.update({
        "source": "SEDATU / SNIIV / RUV",
        "endpoint": API,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "fallback": False,
        "fallback_note": (
            "Respaldo actualizado automáticamente "
            "con API SNIIV; años históricos "
            "previos conservados."
        ),
    })

    output["segment"] = {
        "categories": CATS,
        "annual": merge(
            old.get("segment", {}).get("annual", []),
            new_segment,
        ),
    }

    output["total"] = {
        "annual": merge(
            old.get("total", {}).get("annual", []),
            new_total,
        ),
    }

    if max_period:
        output["latest_period"] = (
            f"{max_period[0]}-{max_period[1]:02d}"
        )

    for rec in output["segment"]["annual"]:
        if sum(rec["values"].values()) != rec["total"]:
            raise RuntimeError(
                "Desglose inconsistente "
                f"en {rec['year']}"
            )

    if (
        not output["segment"]["annual"]
        or not output["total"]["annual"]
    ):
        raise RuntimeError(
            "Histórico insuficiente"
        )

    encoded = (
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    JSON.write_text(
        encoded,
        encoding="utf-8",
    )

    JS.write_text(
        "window.RUV_PRODUCTION = "
        + encoded.rstrip()
        + ";\n",
        encoding="utf-8",
    )

    STATUS.write_text(
        json.dumps(
            {
                "status": "ok",
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "latest_period": output.get(
                    "latest_period"
                ),
                "source_url": url,
                "years_received": sorted(new_segment),
                "rows_received": len(rows),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"Producción RUV: {len(rows)} filas, "
        f"{len(new_segment)} años; "
        f"última observación "
        f"{output.get('latest_period')}"
    )


if __name__ == "__main__":
    try:
        main()

    except Exception as exc:
        STATUS.write_text(
            json.dumps(
                {
                    "status": "error",
                    "updated_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        raise
