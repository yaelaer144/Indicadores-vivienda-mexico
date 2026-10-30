
#!/usr/bin/env python3
"""Actualizacion automatica de salarios IMSS mediante STPS Cognos."""

import csv
import io
import json
import os
import re
import urllib.parse
import urllib.request
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DIARIO = ROOT / "imss_sbc_construccion_mensual.csv"
MENSUAL = ROOT / "imss_salario_construccion_mensual.csv"
STATUS = ROOT / "imss_salarios_stps_status.json"

GATEWAY = (
    "http://siel.stps.gob.mx:303/"
    "ibmcognos/cgi-bin/cognos.cgi"
)

REPORT = (
    "/content/folder[@name='Sitio STPS']"
    "/folder[@name='2. Salarios']"
    "/folder[@name='Salario asociado a trabajadores']"
    "/report[@name='Salario por Actividad Económica']"
)

MONTHS = {
    "jan": 1, "ene": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4, "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8, "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12, "dic": 12,
}

FACTOR = Decimal("30.4")


def normalizar(s):
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(
        c for c in s if not unicodedata.combining(c)
    ).lower().strip()


def fecha(s):
    s = str(s).strip()
    match = re.fullmatch(
        r"(\d{4})[/.-]([A-Za-z]{3})", s
    )
    if match:
        month = MONTHS.get(match.group(2).lower())
        if month:
            return f"{match.group(1)}-{month:02d}"

    match = re.fullmatch(
        r"(\d{4})-(0[1-9]|1[0-2])", s
    )
    return s if match else None


def decimal(s):
    s = str(s).strip().replace(" ", "")
    if not s or s in ("-", "N/A"):
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    return Decimal(s)


def construir_url():
    params = {
        "b_action": "cognosViewer",
        "ui.action": "run",
        "ui.object": REPORT,
        "run.outputFormat": "CSV",
        "run.prompt": "false",
    }
    return GATEWAY + "?" + urllib.parse.urlencode(params)


def descargar():
    url = (
    os.getenv("STPS_COGNOS_URL") or construir_url()
).strip()

if not url.startswith(("http://", "https://")):
    raise ValueError(
        f"URL de STPS no válida: {url!r}"
    )

print("Consultando STPS:", url, flush=True)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,text/plain,*/*",
        },
    )

    with urllib.request.urlopen(
        req, timeout=180
    ) as response:
        raw = response.read(15 * 1024 * 1024)
        ctype = response.headers.get(
            "Content-Type", ""
        )
        print("HTTP:", response.status)
        print("Tipo:", ctype)
        print("Bytes:", len(raw))

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        texto = raw.decode("utf-16")
    else:
        texto = raw.decode("utf-8-sig", errors="replace")

    inicio = texto[:1000].lower()

    if (
        "<html" in inicio
        or "<!doctype" in inicio
        or "application/xhtml" in ctype.lower()
    ):
        raise RuntimeError(
            "Cognos devolvio HTML en lugar de datos. "
            "Puede requerir parametros o sesion."
        )

    if "\t" in texto[:3000]:
        separador = "\t"
    else:
        primera = texto.splitlines()[0]
        separador = (
            ";" if primera.count(";") > primera.count(",")
            else ","
        )

    return list(csv.reader(
        io.StringIO(texto), delimiter=separador
    ))


def extraer_construccion(filas):
    """Localiza la columna de construccion en el reporte."""
    encabezado = None
    posicion = None

    for i, fila in enumerate(filas[:30]):
        for j, campo in enumerate(fila):
            nombre = normalizar(campo)
            if (
                "construccion" in nombre
                and ("industria" in nombre or "div-" in nombre)
            ):
                encabezado = i
                posicion = j
                break
        if posicion is not None:
            break

    if posicion is None:
        raise ValueError(
            "No se encontro columna de construccion. "
            "Revisar formato del CSV Cognos."
        )

    datos = {}

    for fila in filas[encabezado + 1:]:
        if len(fila) <= posicion:
            continue

        periodo = None
        for celda in fila[:3]:
            periodo = fecha(celda)
            if periodo:
                break

        if not periodo or periodo < "2016-01":
            continue

        valor = decimal(fila[posicion])

        if valor is None:
            continue

        if not Decimal("50") < valor < Decimal("5000"):
            raise ValueError(
                f"Salario fuera de rango: {periodo}"
            )

        if periodo in datos:
            if datos[periodo] != valor:
                raise ValueError(
                    f"Periodo duplicado: {periodo}"
                )
        else:
            datos[periodo] = valor

    if not datos:
        raise ValueError(
            "Cognos no devolvio observaciones mensuales"
        )

    return datos


def leer_imss():
    datos = {}

    if not DIARIO.exists():
        return datos

    with DIARIO.open(
        encoding="utf-8-sig", newline=""
    ) as f:
        for row in csv.DictReader(f):
            p = row["periodo"]
            v = row.get("sbc_diario_pesos", "")
            if fecha(p) and v:
                datos[p] = {
                    "valor": decimal(v),
                    "fuente": row.get("fuente") or "IMSS",
                }

    return datos


def escribir(ruta, columnas, filas):
    temporal = ruta.with_suffix(".tmp")

    with temporal.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        w.writerows(filas)

    temporal.replace(ruta)


def centavos(valor):
    return str(valor.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    ))


def main():
    nuevos = extraer_construccion(descargar())
    existentes = leer_imss()

    print("STPS:", min(nuevos), "a", max(nuevos))
    print("Meses STPS:", len(nuevos))

    # Control: contrastar un mes conocido.
    referencia = nuevos.get("2026-06")
    if referencia is not None:
        if abs(referencia - Decimal("500.58")) > Decimal("1"):
            raise ValueError(
                "La serie no coincide con la referencia "
                "de construccion de junio de 2026"
            )

    if "2026-06" not in nuevos:
        raise ValueError(
            "El reporte no contiene junio de 2026; "
            "no se puede validar la consulta"
        )

    # Solo completar faltantes.
    # Nunca reemplazar los meses existentes del IMSS.
    combinados = dict(existentes)

    for periodo, valor in nuevos.items():
        if periodo not in combinados:
            combinados[periodo] = {
                "valor": valor,
                "fuente": "STPS",
            }

    periodos = sorted(combinados)
    if not periodos:
        raise RuntimeError("Sin registros salariales")

    if min(periodos) > "2016-07":
        raise ValueError(
            "La nueva consulta perdio cobertura historica"
        )

    diario = []
    mensual = []

    for p in periodos:
        item = combinados[p]
        v = item["valor"]

        diario.append({
            "periodo": p,
            "sbc_diario_pesos": centavos(v),
            "fuente": item["fuente"],
        })

        mensual.append({
            "periodo": p,
            "salario_mensual_pesos":
                centavos(v * FACTOR),
            "fuente": item["fuente"],
            "factor": "30.4",
        })

    # Ambos archivos se generan automaticamente.
    escribir(
        DIARIO,
        ["periodo", "sbc_diario_pesos", "fuente"],
        diario,
    )
    escribir(
        MENSUAL,
        [
            "periodo", "salario_mensual_pesos",
            "fuente", "factor",
        ],
        mensual,
    )

    status = {
        "estado": "actualizado",
        "fecha_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "fuente": "STPS Cognos + IMSS",
        "inicio": periodos[0],
        "fin": periodos[-1],
        "meses": len(periodos),
        "meses_consultados_stps": len(nuevos),
        "meses_nuevos": len(
            set(combinados) - set(existentes)
        ),
        "factor_mensual": 30.4,
    }

    STATUS.write_text(
        json.dumps(
            status, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        status, ensure_ascii=False, indent=2
    ))


if __name__ == "__main__":
    main()
