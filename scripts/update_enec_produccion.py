#!/usr/bin/env python3
"""Actualiza índices ENEC desde el tabulado PxWeb oficial de INEGI."""
import csv
import json
import math
import re
import statistics
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "enec_actividad_historica.csv"
STATUS = ROOT / "enec_produccion_update_status.json"
ORIGINAL = ROOT / "enec_produccion_inegi_original.json"
EXCEL = ROOT / "enec_produccion_inegi.xlsx"
URL = "https://www.inegi.org.mx/app/tabulados/pxwebapi/api/datatable"
START = "2016-01"
COLUMNS = [
    ("29", "edificacion_indice", "indice de edificacion"),
    ("28", "publico_indice", "indice de sector publico"),
    ("21", "privado_indice", "indice de sector privado"),
]
MONTH_NAMES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
FIELDS = ["periodo", "edificacion_indice", "publico_indice", "privado_indice", "unidad", "fuente", "nota"]


def normalize(value):
    value = unicodedata.normalize("NFD", str(value).casefold())
    return "".join(c for c in value if unicodedata.category(c) != "Mn")


def make_payload():
    def select(code, values, filt="item"):
        return {"code": code, "selection": {"filter": filt, "values": values}}

    return {
        "query": {
            "query": [
                select("Variable", [item[0] for item in COLUMNS]),
                select("Tipo de dato", ["0"]),
                select("Sector SCIAN", ["0"]),
                select("Año", ["*"], "all"),
                select("Mes", ["*"], "all"),
            ],
            "response": {"format": "json-stat"},
        },
        "lang": "es",
        "file": "ENEC/ENEC_NACIONAL_36",
        "stub": ["Variable", "Tipo de dato", "Sector SCIAN"],
        "heading": ["Año", "Mes"],
    }


def fetch():
    body = json.dumps(make_payload(), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        URL, data=body, method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read()
            print(f"INEGI PxWeb: HTTP {response.status}; bytes={len(raw)}", flush=True)
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise ValueError(f"INEGI HTTP {exc.code}: {detail}") from exc
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError("La respuesta de INEGI no es un objeto JSON")
    print(f"INEGI: campos={list(result)}; filas={result.get('rowCount')}; columnas={result.get('colCount')}", flush=True)
    return result


def get_labels(items, code):
    matches = [entry.get("label") for entry in items if entry.get("code") == code]
    if len(matches) != 1 or not isinstance(matches[0], list):
        raise ValueError(f"No se encontraron etiquetas para {code}")
    return matches[0]


def extract(response):
    required = {"data", "heading", "stub", "rowCount", "colCount"}
    if not required.issubset(response):
        raise ValueError(f"Respuesta sin campos requeridos: {list(response)}")
    years = get_labels(response["heading"], "Año")
    months = get_labels(response["heading"], "Mes")
    variables = get_labels(response["stub"], "Variable")
    sector = get_labels(response["stub"], "Sector SCIAN")
    data_type = get_labels(response["stub"], "Tipo de dato")
    if [normalize(m) for m in months] != MONTH_NAMES:
        raise ValueError(f"Orden mensual inesperado: {months}")
    if sector != ["23 Construcción"] or data_type != ["Dato"]:
        raise ValueError(f"Selección inesperada: sector={sector}, tipo={data_type}")
    if len(variables) != len(COLUMNS):
        raise ValueError(f"Se esperaban tres variables; recibido={variables}")
    for label, (_, _, expected) in zip(variables, COLUMNS):
        if expected not in normalize(label):
            raise ValueError(f"Orden o nombre de variable inesperado: {label}")
    if any(not re.fullmatch(r"\d{4}", str(y)) for y in years):
        raise ValueError(f"Etiquetas de año inválidas: {years}")
    if sorted(map(int, years)) != list(map(int, years)) or len(set(years)) != len(years):
        raise ValueError("Años fuera de orden o duplicados")
    cols = len(years) * 12
    rows = len(COLUMNS)
    matrix = response["data"]
    if (response["rowCount"] != rows or response["colCount"] != cols
            or len(matrix) != rows * cols):
        raise ValueError("Dimensiones incorrectas de la matriz INEGI")
    result = {}
    missing = {"", "-", ".", "..", "...", "N/D", "ND", "NA", "N/A", "N.D."}
    for row_index, (_, column, _) in enumerate(COLUMNS):
        for col_index in range(cols):
            period = f"{years[col_index // 12]}-{col_index % 12 + 1:02d}"
            if period < START:
                continue
            raw = matrix[row_index * cols + col_index]
            number = "" if raw is None else str(raw).split("|", 1)[0].strip()
            if number.upper() in missing:
                continue
            try:
                value = float(number.replace(",", ""))
            except ValueError as exc:
                raise ValueError(f"Dato no numérico: {period} {column}: {raw!r}") from exc
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"Dato inválido: {period} {column}: {value}")
            result.setdefault(period, {})[column] = value
    full = {period: values for period, values in result.items() if len(values) == rows}
    periods = sorted(full)
    if len(periods) < 96 or periods[0] != START:
        raise ValueError(f"Cobertura insuficiente: primero={periods[0] if periods else 'ninguno'}; n={len(periods)}")
    for previous, following in zip(periods, periods[1:]):
        year, month = map(int, previous.split("-"))
        expected = f"{year + (month == 12)}-{month % 12 + 1:02d}"
        if following != expected:
            raise ValueError(f"Mes faltante entre {previous} y {following}")
    # No aceptar valores numéricos parciales posteriores al último mes completo.
    if any(period > periods[-1] for period in result):
        raise ValueError("INEGI devolvió datos parciales posteriores al último mes completo")
    print(f"ENEC validado: {periods[0]} a {periods[-1]}; {len(periods)} meses", flush=True)
    print(f"Último mes: {full[periods[-1]]}", flush=True)
    return full


def build_csv(rows):
    from io import StringIO
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    for period, values in sorted(rows.items()):
        writer.writerow({
            "periodo": period,
            **{name: f"{values[name]:.6f}" for _, name, _ in COLUMNS},
            "unidad": "índice 2018=100",
            "fuente": "INEGI - ENEC; ENEC_NACIONAL_36",
            "nota": "Índices de edificación, sector público y privado; sector 23 Construcción",
        })
    return stream.getvalue()


def make_excel(rows):
    try:
        from openpyxl import Workbook
    except ImportError:
        print("Aviso: openpyxl no instalado; el Excel no se generó", flush=True)
        return False
    wb = Workbook()
    ws = wb.active
    ws.title = "ENEC_indices"
    ws.append(["Periodo", "Índice de edificación", "Índice sector público", "Índice sector privado"])
    for period, values in sorted(rows.items()):
        ws.append([period, values["edificacion_indice"], values["publico_indice"], values["privado_indice"]])
    temp = EXCEL.with_name(EXCEL.stem + ".tmp.xlsx")
    wb.save(temp)
    temp.replace(EXCEL)
    return True


def main():
    report = {"consultado_utc": datetime.now(timezone.utc).isoformat(), "fuente": URL,
              "tabla": "ENEC/ENEC_NACIONAL_36", "estado": "sin_validar"}
    try:
        response = fetch()
        rows = extract(response)
        previous = {}
        if DEST.exists():
            with DEST.open(encoding="utf-8-sig", newline="") as handle:
                previous = {r["periodo"]: r for r in csv.DictReader(handle)}
        if previous and max(rows) < max(previous):
            raise ValueError("La respuesta es anterior al último mes guardado")
        differences = {}
        for _, key, _ in COLUMNS:
            deviations = []
            for period, values in rows.items():
                old = previous.get(period, {}).get(key, "")
                if old:
                    old_number = float(old)
                    deviations.append(abs(old_number - values[key]) / max(abs(old_number), 1))
            if deviations:
                differences[key] = round(statistics.median(deviations), 6)
        csv_text = build_csv(rows)
        temp = DEST.with_name(DEST.name + ".tmp")
        temp.write_text(csv_text, encoding="utf-8-sig")
        temp.replace(DEST)
        raw_temp = ORIGINAL.with_name(ORIGINAL.name + ".tmp")
        raw_temp.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        raw_temp.replace(ORIGINAL)
        excel_ok = make_excel(rows)
        report.update(estado="actualizado_fuente_oficial", primero=min(rows), ultimo=max(rows),
                      meses=len(rows), excel_generado=excel_ok,
                      diferencia_relativa_mediana_anterior=differences)
        print(f"ENEC actualizado: {min(rows)} a {max(rows)}; Excel={excel_ok}", flush=True)
        return 0
    except Exception as exc:
        report.update(estado="error", error=str(exc))
        print(f"ENEC producción: {exc}", file=sys.stderr, flush=True)
        return 1
    finally:
        STATUS.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
