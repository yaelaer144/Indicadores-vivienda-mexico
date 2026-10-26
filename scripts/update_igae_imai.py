
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
    url = TABULADOS[which]
    dest = Path(dest)

    response = page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=90000,
    )

    page.wait_for_timeout(6000)

    contenedor = page.locator("#container1")
    if contenedor.count():
        print(
            f"{which}: contenido del tabulado = "
            f"{contenedor.first.inner_text(timeout=10000)[:1500]}",
            flush=True,
        )
        print(
            f"{which}: tablas generadas = "
            f"{contenedor.locator('table').count()}",
            flush=True,
        )

    print(
        f"{which}: opciones de periodo = "
        f"{page.locator('#selectperiodoI option').count()}",
        flush=True,
    )
    print(
        f"{which}: scripts cargados = "
        f"{page.locator('script[src]').count()}",
        flush=True,
    )

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
