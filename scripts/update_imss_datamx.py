
#!/usr/bin/env python3
"""Actualiza puestos de trabajo IMSS desde DataMX.

Conserva los CSV que consume el dashboard.
No modifica salarios.
"""

import csv
import io
import json
import re
import tempfile
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

URL = (
    "https://datamx.io/dataset/"
    "924b0ba9-38cf-46d9-a152-c31779a424f6/"
    "resource/"
    "382fbd94-4047-437d-9c59-54cd601dfa33/"
    "download/data.csv"
)

CSV_CONS = ROOT / "imss_construccion_mensual.csv"
CSV_TOTAL = ROOT / "imss_total_mensual.csv"
STATUS = ROOT / "imss_datamx_update_status.json"

INICIO = "2016-01"


def escribir_csv(ruta, columnas, registros):
    """Escribe CSV y reemplaza de forma atomica."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8-sig",
        newline="",
        dir=ROOT,
        suffix=".tmp",
        delete=False,
    ) as f:
        temporal = Path(f.name)
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(registros)

    temporal.replace(ruta)


def meses_entre(inicio, fin):
    y, m = map(int, inicio.split("-"))
    yf, mf = map(int, fin.split("-"))

    while (y, m) <= (yf, mf):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y += 1
            m = 1


def ultimo_periodo_existente():
    if not CSV_TOTAL.exists():
        return None

    with CSV_TOTAL.open(
        encoding="utf-8-sig", newline=""
    ) as f:
        periodos = [
            row["periodo"]
            for row in csv.DictReader(f)
            if re.fullmatch(
                r"\d{4}-\d{2}",
                row.get("periodo", "")
            )
        ]

    return max(periodos) if periodos else None


def descargar_agregados():
    """Procesamiento en streaming, sin guardar 356 MB en RAM."""
    nacional = defaultdict(int)
    construccion = defaultdict(int)
    filas_periodo = defaultdict(int)
    codigos_sexo = set()
    entidades = set()
    registros = 0

    req = urllib.request.Request(
        URL,
        headers={
            "User-Agent": "Indicadores-Vivienda/1.0",
            "Accept": "text/csv,*/*",
        },
    )

    with urllib.request.urlopen(
        req, timeout=180
    ) as response:
        if response.status != 200:
            raise RuntimeError(
                f"HTTP inesperado: {response.status}"
            )

        print(
            "Descarga DataMX HTTP:",
            response.status,
            flush=True,
        )

        text = io.TextIOWrapper(
            response,
            encoding="utf-8-sig",
            errors="replace",
            newline="",
        )

        reader = csv.DictReader(text)

        requeridas = {
            "PERIODO",
            "CVE_ENT",
            "SEXO",
            "SECTOR",
            "TOTAL",
        }

        faltantes = requeridas - set(
            reader.fieldnames or []
        )

        if faltantes:
            raise ValueError(
                f"Columnas faltantes: {faltantes}"
            )

        for row in reader:
            periodo = row["PERIODO"].strip()

            if not re.fullmatch(
                r"\d{4}-(0[1-9]|1[0-2])",
                periodo,
            ):
                continue

            if periodo < INICIO:
                continue

            puestos = int(row["TOTAL"])

            if puestos < 0:
                raise ValueError(
                    f"Puestos negativos: {periodo}"
                )

            nacional[periodo] += puestos
            filas_periodo[periodo] += 1

            sector = row["SECTOR"].strip()
            sexo = row["SEXO"].strip()
            entidad = row["CVE_ENT"].strip()

            codigos_sexo.add(sexo)
            entidades.add(entidad)

            if sector == "4":
                construccion[periodo] += puestos

            registros += 1

            if registros % 500000 == 0:
                print(
                    "Registros procesados:",
                    registros,
                    flush=True,
                )

    return {
        "nacional": dict(nacional),
        "construccion": dict(construccion),
        "filas": dict(filas_periodo),
        "sexos": sorted(codigos_sexo),
        "entidades": sorted(entidades),
        "registros": registros,
    }


def validar(datos):
    nacional = datos["nacional"]
    construccion = datos["construccion"]
    filas = datos["filas"]

    periodos = sorted(nacional)

    if not periodos or periodos[0] != INICIO:
        raise ValueError(
            "El historico no comienza en enero de 2016"
        )

    esperados = list(
        meses_entre(INICIO, periodos[-1])
    )

    if periodos != esperados:
        raise ValueError(
            "El historico presenta meses faltantes"
        )

    for p in periodos:
        n = nacional[p]
        c = construccion.get(p, 0)

        if not (10000000 < n < 40000000):
            raise ValueError(
                f"Total nacional fuera de rango: {p}"
            )

        if not (500000 < c < 4000000):
            raise ValueError(
                f"Construccion fuera de rango: {p}"
            )

        if c >= n:
            raise ValueError(
                f"Construccion supera total: {p}"
            )

        if filas[p] < 10000:
            raise ValueError(
                f"Mes posiblemente incompleto: {p}"
            )

    previo = ultimo_periodo_existente()

    if previo and periodos[-1] < previo:
        raise ValueError(
            "La fuente alternativa es mas antigua "
            "que los CSV existentes"
        )

    return periodos


def publicar(datos, periodos):
    nacional = datos["nacional"]
    construccion = datos["construccion"]

    registros_cons = []
    registros_total = []

    for periodo in periodos:
        # El dashboard utiliza miles de puestos.
        cons_miles = round(
            construccion[periodo] / 1000, 3
        )
        total_miles = round(
            nacional[periodo] / 1000, 3
        )

        registros_cons.append({
            "periodo": periodo,
            "construccion": cons_miles,
        })

        registros_total.append({
            "periodo": periodo,
            "puestos_miles": total_miles,
            "fuente": "IMSS via DataMX",
            "nota": "Total nacional",
        })

    escribir_csv(
        CSV_CONS,
        ["periodo", "construccion"],
        registros_cons,
    )

    escribir_csv(
        CSV_TOTAL,
        ["periodo", "puestos_miles", "fuente", "nota"],
        registros_total,
    )


def guardar_status(estado, **kwargs):
    reporte = {
        "fecha_ejecucion_utc":
            datetime.now(timezone.utc).isoformat(),
        "fuente": "IMSS via DataMX",
        "estado": estado,
        **kwargs,
    }

    STATUS.write_text(
        json.dumps(
            reporte,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def main():
    try:
        datos = descargar_agregados()
        periodos = validar(datos)

        # Solo publicar cuando toda la lectura
        # y la validacion terminaron correctamente.
        publicar(datos, periodos)

        guardar_status(
            "actualizado",
            inicio=periodos[0],
            fin=periodos[-1],
            meses=len(periodos),
            filas=datos["registros"],
            codigos_sexo=datos["sexos"],
            entidades=datos["entidades"],
            ultimo_nacional=datos["nacional"][periodos[-1]],
            ultimo_construccion=datos["construccion"][periodos[-1]],
            salarios_actualizados=False,
        )

        print("\nIMSS actualizado correctamente")
        print("Periodo:", periodos[0], "a", periodos[-1])
        print("Meses:", len(periodos))
        print(
            "Ultimo nacional:",
            datos["nacional"][periodos[-1]],
        )
        print(
            "Ultimo construccion:",
            datos["construccion"][periodos[-1]],
        )

    except Exception as e:
        guardar_status(
            "error",
            mensaje=str(e),
            historico_conservado=True,
        )
        raise


if __name__ == "__main__":
    main()
