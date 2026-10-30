
#!/usr/bin/env python3
"""Integra salarios IMSS y STPS sin sobrescribir el original.

Prioridad: IMSS existente > STPS.
Genera serie diaria combinada y mensual equivalente.
"""

import csv
import json
import re
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IMSS = ROOT / "imss_sbc_construccion_mensual.csv"
STPS = ROOT / "stps_salarios_construccion.csv"

DIARIO = ROOT / "imss_stps_sbc_construccion_diario.csv"
MENSUAL = ROOT / "imss_stps_salario_construccion_mensual.csv"
STATUS = ROOT / "imss_stps_salarios_status.json"

FACTOR = Decimal("30.4")
CENTAVOS = Decimal("0.01")


def redondear(valor):
    return valor.quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )


def leer(path, fuente):
    registros = {}

    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path.name}"
        )

    with path.open(
        encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)

        columnas = set(reader.fieldnames or [])
        necesarias = {"periodo", "sbc_diario_pesos"}

        if not necesarias.issubset(columnas):
            raise ValueError(
                f"{path.name}: columnas requeridas: "
                f"{sorted(necesarias)}"
            )

        for fila in reader:
            periodo = fila["periodo"].strip()

            if not re.fullmatch(
                r"\d{4}-(0[1-9]|1[0-2])",
                periodo
            ):
                raise ValueError(
                    f"Periodo incorrecto: {periodo}"
                )

            if periodo < "2016-01":
                continue

            cadena = fila["sbc_diario_pesos"].strip()
            cadena = cadena.replace(",", "")

            if not cadena:
                continue

            valor = Decimal(cadena)

            if not Decimal("50") < valor < Decimal("5000"):
                raise ValueError(
                    f"Salario fuera de rango: {periodo}"
                )

            if periodo in registros:
                raise ValueError(
                    f"Periodo duplicado: {periodo}"
                )

            registros[periodo] = {
                "valor": valor,
                "fuente": fuente
            }

    return registros


def escribir(path, columnas, filas):
    temporal = path.with_suffix(".tmp")

    with temporal.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=columnas
        )
        writer.writeheader()
        writer.writerows(filas)

    temporal.replace(path)


def obtener_faltantes(periodos):
    if not periodos:
        return []

    inicio = (2016, 1)
    fin = tuple(map(int, max(periodos).split("-")))
    faltantes = []

    y, m = inicio

    while (y, m) <= fin:
        p = f"{y:04d}-{m:02d}"

        if p not in periodos:
            faltantes.append(p)

        m += 1
        if m == 13:
            y += 1
            m = 1

    return faltantes


def main():
    imss = leer(IMSS, "IMSS")
    stps = leer(STPS, "STPS")

    # STPS cubre faltantes e incorpora meses nuevos.
    # IMSS tiene prioridad si ambas fuentes coinciden.
    combinado = dict(stps)
    combinado.update(imss)

    periodos = sorted(combinado)

    if not periodos:
        raise ValueError("Sin salarios disponibles")

    faltantes = obtener_faltantes(periodos)

    filas_diarias = []
    filas_mensuales = []

    for periodo in periodos:
        item = combinado[periodo]

        diario = redondear(item["valor"])
        mensual = redondear(
            item["valor"] * FACTOR
        )

        filas_diarias.append({
            "periodo": periodo,
            "sbc_diario_pesos": str(diario),
            "fuente": item["fuente"]
        })

        filas_mensuales.append({
            "periodo": periodo,
            "salario_mensual_pesos": str(mensual),
            "fuente": item["fuente"],
            "factor": "30.4"
        })

    escribir(
        DIARIO,
        ["periodo", "sbc_diario_pesos", "fuente"],
        filas_diarias
    )

    escribir(
        MENSUAL,
        [
            "periodo",
            "salario_mensual_pesos",
            "fuente",
            "factor"
        ],
        filas_mensuales
    )

    reporte = {
        "fecha_utc":
            datetime.now(timezone.utc).isoformat(),
        "estado": (
            "completo" if not faltantes
            else "historico_incompleto"
        ),
        "inicio": periodos[0],
        "fin": periodos[-1],
        "meses": len(periodos),
        "meses_imss": sum(
            x["fuente"] == "IMSS"
            for x in combinado.values()
        ),
        "meses_stps": sum(
            x["fuente"] == "STPS"
            for x in combinado.values()
        ),
        "meses_faltantes": faltantes,
        "factor_mensual": "30.4"
    }

    STATUS.write_text(
        json.dumps(
            reporte,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    print(json.dumps(
        reporte, indent=2, ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
