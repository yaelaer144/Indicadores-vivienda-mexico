
#!/usr/bin/env python3
"""Actualización IMSS: empleo y salarios, con diagnóstico HTTP."""

import csv
import json
import os
import re
import time
import tempfile
import urllib.error
import urllib.request
from calendar import monthrange
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]
START = "2016-01"

CONS = ROOT / "imss_construccion_mensual.csv"
SBC = ROOT / "imss_sbc_construccion_mensual.csv"
TOTAL = ROOT / "imss_total_mensual.csv"
STATUS = ROOT / "imss_update_status.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 IMSS-Indicadores/3.0",
    "Accept": "text/csv,application/octet-stream,*/*"
}

BASES = [
    "https://datos.imss.gob.mx/sites/default/files/",
    "https://www2.imss.gob.mx/sites/default/files/"
]

PAGES = [
    "https://datos.imss.gob.mx/group/asegurados",
    "https://datos.imss.gob.mx/dataset/asegurados"
]


def request(url, target=None):
    """Descarga con reintentos. Guarda archivos grandes en disco."""
    last = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=120) as response:
                content_type = response.headers.get(
                    "Content-Type", ""
                )
                if target:
                    with open(target, "wb") as f:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                    return content_type, b""
                return content_type, response.read()
        except urllib.error.HTTPError as e:
            last = "HTTP " + str(e.code)
            if e.code not in (429, 500, 502, 503, 504):
                break
            delay = e.headers.get("Retry-After", "")
            delay = int(delay) if delay.isdigit() else 5 * (attempt + 1)
            time.sleep(min(delay, 60))
        except Exception as e:
            last = str(e)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(last or "Descarga fallida")


def months():
    now = datetime.now(timezone.utc)
    y, m = map(int, START.split("-"))
    end = (now.year, now.month - 1)
    if end[1] == 0:
        end = (now.year - 1, 12)
    while (y, m) <= end:
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def read_csv(path):
    if not path.exists():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        return {
            row["periodo"]: row
            for row in csv.DictReader(f)
            if re.fullmatch(r"\d{4}-\d{2}", row.get("periodo", ""))
        }


def save_csv(path, data, columns):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=columns, extrasaction="ignore"
        )
        writer.writeheader()
        for period in sorted(data):
            writer.writerow(data[period])
    temp.replace(path)


def discover():
    """Recupera las direcciones publicadas en páginas oficiales."""
    found = []
    for page in PAGES:
        try:
            _, raw = request(page)
            html = raw.decode("utf-8", "replace")
            urls = re.findall(
                r"""(?:href=["']([^"']+)["'])""", html, re.I
            )
            for href in urls:
                if re.search(r"asg-\d{4}-\d{2}-\d{2}", href, re.I):
                    found.append(urljoin(page, href.replace("&amp;", "&")))
        except Exception as e:
            print("No se pudo consultar catálogo:", page, e)
    return list(dict.fromkeys(found))


def urls_for(period, discovered):
    year, month = map(int, period.split("-"))
    day = monthrange(year, month)[1]
    filename = f"asg-{year:04d}-{month:02d}-{day:02d}.csv"

    urls = [u for u in discovered if filename.lower() in u.lower()]

    template = os.getenv("IMSS_URL_TEMPLATE", "").strip()
    if template:
        urls.insert(0, template.format(
            date=f"{year:04d}-{month:02d}-{day:02d}",
            year=year,
            month=f"{month:02d}"
        ))

    urls += [base + filename for base in BASES]
    return list(dict.fromkeys(urls))


def number(x):
    try:
        return float(str(x or "0").replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def process(path):
    """Procesa el archivo por filas, sin cargarlo todo en RAM."""
    total = 0.0
    cons = 0.0
    salaried = 0.0
    mass = 0.0
    count = 0

    with open(path, "r", encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f, delimiter="|")
        if not reader.fieldnames:
            raise ValueError("Sin encabezados")

        reader.fieldnames = [
            name.strip().lower().lstrip("\ufeff")
            for name in reader.fieldnames
        ]

        required = {
            "sector_economico_1", "ta",
            "ta_sal", "masa_sal_ta"
        }
        if not required.issubset(set(reader.fieldnames)):
            raise ValueError(
                "Columnas faltantes: " +
                str(required - set(reader.fieldnames))
            )

        for row in reader:
            count += 1
            ta = number(row["ta"])
            total += ta

            sector = row["sector_economico_1"].strip()
            try:
                sector = str(int(float(sector)))
            except ValueError:
                pass

            if sector == "4":
                cons += ta
                salaried += number(row["ta_sal"])
                mass += number(row["masa_sal_ta"])

    if count < 10 or cons < 1000 or salaried <= 0:
        raise ValueError("Agregados inválidos o archivo incompleto")

    sbc = mass / salaried
    if not 50 < sbc < 5000:
        raise ValueError("Salario promedio fuera de rango")

    return {
        "construccion": round(cons / 1000, 3),
        "puestos": round(total / 1000, 3),
        "sbc": round(sbc, 2),
        "filas": count
    }


def main():
    construction = read_csv(CONS)
    salaries = read_csv(SBC)
    national = read_csv(TOTAL)

    pending = [
        p for p in months()
        if not (
            p in construction and
            p in salaries and
            p in national
        )
    ]

    limit = max(1, int(os.getenv("IMSS_MAX_MONTHS_PER_RUN", "12")))
    offset = max(0, int(os.getenv("IMSS_BACKFILL_OFFSET", "0")))

    recent = sorted(pending, reverse=True)[:3]
    older = [p for p in sorted(pending) if p not in recent]

    if older:
        k = offset % len(older)
        older = older[k:] + older[:k]

    selected = (recent + older)[:limit]
    discovered = discover()
    results = []
    updated = 0

    for period in selected:
        errors = []
        print("Consultando:", period, flush=True)

        for url in urls_for(period, discovered):
            with tempfile.TemporaryDirectory() as folder:
                target = Path(folder) / "imss.csv"
                try:
                    ctype, _ = request(url, target)

                    with target.open("rb") as f:
                        prefix = f.read(500).lower()

                    if b"<html" in prefix or "text/html" in ctype.lower():
                        raise ValueError("Servidor devolvió HTML")

                    data = process(target)

                    construction[period] = {
                        "periodo": period,
                        "construccion": data["construccion"]
                    }
                    salaries[period] = {
                        "periodo": period,
                        "sbc_diario_pesos": data["sbc"],
                        "fuente": "IMSS Datos Abiertos"
                    }
                    national[period] = {
                        "periodo": period,
                        "puestos_miles": data["puestos"],
                        "fuente": "IMSS Datos Abiertos",
                        "nota": "Total nacional"
                    }

                    save_csv(
                        CONS, construction, ["periodo", "construccion"]
                    )
                    save_csv(
                        SBC, salaries,
                        ["periodo", "sbc_diario_pesos", "fuente"]
                    )
                    save_csv(
                        TOTAL, national,
                        ["periodo", "puestos_miles", "fuente", "nota"]
                    )

                    results.append({
                        "periodo": period,
                        "estado": "actualizado",
                        "url": url,
                        "filas": data["filas"]
                    })
                    updated += 1
                    break

                except Exception as e:
                    errors.append({
                        "url": url,
                        "error": str(e)
                    })
                    print("Fallo:", str(e), flush=True)

        if not any(
            r["periodo"] == period and r["estado"] == "actualizado"
            for r in results
        ):
            results.append({
                "periodo": period,
                "estado": "fallido",
                "errores": errors
            })

        time.sleep(2)

    status = {
        "fecha_ejecucion_utc":
            datetime.now(timezone.utc).isoformat(),
        "fuente": "IMSS Datos Abiertos",
        "inicio_historico": START,
        "meses_faltantes_al_inicio": len(pending),
        "meses_intentados": len(selected),
        "meses_actualizados": updated,
        "estado": (
            "actualizado" if updated else
            "sin_descargas_nuevas" if selected else
            "al_dia"
        ),
        "resultados": results
    }

    STATUS.write_text(
        json.dumps(status, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    print(json.dumps(status, indent=2, ensure_ascii=False))

    if selected and updated == 0:
        print(
            "::warning::IMSS no descargó archivos. "
            "Histórico conservado."
        )


if __name__ == "__main__":
    main()
