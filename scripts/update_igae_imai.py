
#!/usr/bin/env python3
"""Actualiza IGAE e IMAI desde tabulados oficiales de INEGI.

Conserva el histórico si falla la descarga o validación.
Prueba local:
python scripts/update_igae_imai.py --local-igae IGAE.csv --local-imai IMAI.csv
"""

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

TABULADOS = {
    "IGAE": (
        "https://www.inegi.org.mx/app/tabulados/default.aspx"
        "?pr=11&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3252&opc=p"
    ),
    "IMAI": (
        "https://www.inegi.org.mx/app/tabulados/default.aspx"
        "?pr=10&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3251&opc=p"
    ),
}

OUTPUTS = (
    "igae_construccion_mensual.csv",
    "imai_construccion_mensual.csv",
    "imai_construccion_subsectores_mensual.csv",
)


def descargar(page, which, dest):
    """Descarga CSV sin modificar los datos existentes."""
    import re

    url = TABULADOS[which]
    dest = Path(dest)

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=90000,
    )

    page.wait_for_timeout(6000)

    code = response.status if response else None

    print(
        f"{which}: HTTP {code}; título={page.title()}",
        flush=True,
    )

    if code != 200:
        raise RuntimeError(
            f"{which}: sitio no disponible (HTTP {code})"
        )


    # Localizar el control real de exportación CSV.
    # El input btndescargacsv está oculto en el HTML.

    csv_button = page.locator("#aCsv")

    csv_button.wait_for(
        state="visible",
        timeout=30000
    )

    print(
        f"{which}: icono CSV visible",
        flush=True
    )

    controles = [csv_button]

    print(
        f"{which}: controles CSV visibles="
        f"{len(controles)}",
        flush=True
    )


    def valido(blob):
        if len(blob) < 500:
            return False

        inicio = blob[:2000].lstrip().lower()

        if any(
            marker in inicio
            for marker in (
                b"<!doctype html",
                b"<html",
                b"<head",
            )
        ):
            return False

        return (
            b"," in blob[:4000]
            or b";" in blob[:4000]
            or b"\t" in blob[:4000]
        )

    for n, el in enumerate(controles, start=1):
        try:
            print(
                f"{which}: intentando control {n}",
                flush=True,
            )

            downloaded = []
            responses = []

            def on_download(download):
                downloaded.append(download)

            def on_response(r):
                try:
                    h = r.headers
                    ct = h.get(
                        "content-type", ""
                    ).lower()
                    cd = h.get(
                        "content-disposition", ""
                    ).lower()

                    if (
                        "csv" in ct
                        or ".csv" in cd
                        or "attachment" in cd
                    ):
                        responses.append(r)

                except Exception:
                    pass

            page.on("download", on_download)
            page.on("response", on_response)

            try:

                el.click(timeout=10000)
                page.wait_for_timeout(3000)

                modal = page.locator("#myModal")

                print(
                    f"{which}: modal visible = "
                    f"{modal.is_visible()}",
                    flush=True
                )

                for campo in (
                    "selectperiodoI",
                    "selectperiodoF",
                    "selectTipoInfo"
                ):
                    opciones = page.locator(
                        f"#{campo} option"
                    )

                    print(
                        f"{which}: {campo} = "
                        f"{opciones.all_text_contents()[:30]}",
                        flush=True
                    )

                print(
                    f"{which}: Exportar visible = "
                    f"{page.locator('#myBtn').is_visible()}",
                    flush=True
                )

                if modal.is_visible():
                    print(
                        f"{which}: esperando configuración "
                        "de exportación; sin confirmar descarga",
                        flush=True
                    )

                for d in downloaded:
                    with tempfile.TemporaryDirectory() as td:
                        candidate = (
                            Path(td) / "download.csv"
                        )

                        d.save_as(candidate)
                        raw = candidate.read_bytes()

                        if valido(raw):
                            dest.write_bytes(raw)

                            print(
                                f"{which}: CSV descargado "
                                f"({len(raw)} bytes)",
                                flush=True,
                            )

                            return

                for r in responses:
                    if r.status == 200:
                        raw = r.body()

                        if valido(raw):
                            dest.write_bytes(raw)

                            print(
                                f"{which}: CSV recibido "
                                f"por HTTP ({len(raw)} bytes)",
                                flush=True,
                            )

                            return

            finally:
                page.remove_listener(
                    "download", on_download
                )
                page.remove_listener(
                    "response", on_response
                )

        except Exception as exc:
            print(
                f"{which}: control {n} no produjo CSV: "
                f"{exc}",
                flush=True,
            )

    raise RuntimeError(
        f"{which}: se detectó el botón CSV, "
        "pero no se recibió un archivo válido. "
        "Puede requerir otra interacción o estar "
        "protegido por reCAPTCHA. "
        "No se alteraron los históricos."
    )


def get_last(path):
    if not path.exists():
        return None

    with path.open(
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    return max(
        (
            r["periodo"]
            for r in rows
            if r.get("periodo")
        ),
        default=None,
    )


def validate(stage):
    for name in OUTPUTS:
        path = stage / name

        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(
                f"No se generó {name}"
            )

        with path.open(
            encoding="utf-8-sig",
            newline="",
        ) as f:
            rows = list(csv.DictReader(f))

        periods = [
            r["periodo"]
            for r in rows
        ]

        if (
            len(periods) < 90
            or len(periods) != len(set(periods))
            or periods != sorted(periods)
        ):
            raise RuntimeError(
                f"Histórico incompleto o duplicado: {name}"
            )

        if periods[0] != "2016-01":
            raise RuntimeError(
                f"El histórico no inicia "
                f"en enero de 2016: {name}"
            )

        existing = ROOT / name

        if existing.exists():
            with existing.open(
                encoding="utf-8-sig",
                newline="",
            ) as f:
                previous_rows = {
                    r["periodo"]: r
                    for r in csv.DictReader(f)
                }

            with path.open(
                encoding="utf-8-sig",
                newline="",
            ) as f:
                current_rows = {
                    r["periodo"]: r
                    for r in csv.DictReader(f)
                }

            common = sorted(
                set(previous_rows) & set(current_rows)
            )[-24:]

            values = []

            field = (
                "indice"
                if name != OUTPUTS[2]
                else "construction"
            )

            for period in common:
                try:
                    old = float(
                        previous_rows[period][field]
                    )
                    new = float(
                        current_rows[period][field]
                    )

                    if old > 0:
                        values.append(
                            abs(new - old) / old
                        )

                except (
                    KeyError,
                    ValueError,
                    TypeError,
                ):
                    continue

            if (
                len(values) >= 6
                and sorted(values)[len(values) // 2] > 0.02
            ):
                raise RuntimeError(
                    f"{name}: cambios excesivos "
                    "respecto al histórico; "
                    "posible serie incorrecta"
                )

        previous = get_last(ROOT / name)

        if previous and periods[-1] < previous:
            raise RuntimeError(
                f"{name} retrocede de "
                f"{previous} a {periods[-1]}"
            )

        print(
            f"{name}: {len(periods)} meses, "
            f"{periods[0]} a {periods[-1]}",
            flush=True,
        )


def main():
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--local-igae",
        type=Path,
    )

    ap.add_argument(
        "--local-imai",
        type=Path,
    )

    args = ap.parse_args()

    if bool(args.local_igae) != bool(args.local_imai):
        ap.error(
            "Se necesitan ambos CSV en modo local"
        )

    with tempfile.TemporaryDirectory(
        prefix="inegi_igae_imai_"
    ) as td:
        temp = Path(td)

        if args.local_igae:
            shutil.copy2(
                args.local_igae,
                temp / "IGAE.csv",
            )

            shutil.copy2(
                args.local_imai,
                temp / "IMAI.csv",
            )

            metodo = "prueba_local"

        else:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox"],
                )

                try:
                    context = browser.new_context(
                        accept_downloads=True,
                        locale="es-MX",
                    )

                    page = context.new_page()

                    for which in ("IGAE", "IMAI"):
                        descargar(
                            page,
                            which,
                            temp / f"{which}.csv",
                        )

                finally:
                    browser.close()

            metodo = "playwright_tabulados"

        subprocess.run(
            [
                sys.executable,
                str(ROOT / "prepare_igae_imai.py"),
                str(temp / "IGAE.csv"),
                str(temp / "IMAI.csv"),
                str(temp),
            ],
            check=True,
        )

        validate(temp)

        # Reemplazar únicamente datos validados.
        for name in OUTPUTS:
            os.replace(
                temp / name,
                ROOT / name,
            )

        status = {
            "fecha_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "resultado": "ok",
            "metodo": metodo,
            "fuentes": TABULADOS,
            "ultimo_igae": get_last(
                ROOT / OUTPUTS[0]
            ),
            "ultimo_imai": get_last(
                ROOT / OUTPUTS[1]
            ),
        }

        (
            ROOT / "igae_imai_update_status.json"
        ).write_text(
            json.dumps(
                status,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        print(
            "Actualización verificada: "
            "archivos generados correctamente",
            flush=True,
        )


if __name__ == "__main__":
    try:
        main()

    except Exception as exc:
        print(
            f"ERROR: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
