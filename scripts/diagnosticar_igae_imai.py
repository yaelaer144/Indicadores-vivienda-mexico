
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import re

URLS = {
    "IGAE": "https://www.inegi.org.mx/app/tabulados/default.aspx?pr=11&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3252&opc=p",
    "IMAI": "https://www.inegi.org.mx/app/tabulados/default.aspx?pr=10&vr=1&in=2&tp=20&wr=1&cno=1&idrt=3251&opc=p",
}

OUT = Path("diagnostico_inegi")
OUT.mkdir(exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox"]
    )

    context = browser.new_context(
        accept_downloads=True,
        locale="es-MX"
    )

    for nombre, url in URLS.items():
        page = context.new_page()

        resultado = {
            "indicador": nombre,
            "url_solicitada": url,
            "errores": [],
            "frames": []
        }

        page.on(
            "pageerror",
            lambda error, r=resultado:
                r["errores"].append(str(error))
        )

        try:
            respuesta = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=90000
            )

            page.wait_for_timeout(8000)

            resultado["http"] = (
                respuesta.status if respuesta else None
            )
            resultado["url_final"] = page.url
            resultado["titulo"] = page.title()

            for frame in page.frames:
                datos = {
                    "url": frame.url,
                    "controles": []
                }

                controles = frame.locator(
                    "button, a, input, [role=button]"
                )

                for i in range(min(controles.count(), 100)):
                    el = controles.nth(i)

                    try:
                        texto = (
                            el.inner_text(timeout=1000)
                            or el.get_attribute("title")
                            or el.get_attribute("value")
                            or ""
                        )

                        if re.search(
                            r"csv|excel|descargar|exportar",
                            texto,
                            re.IGNORECASE
                        ):
                            datos["controles"].append(
                                texto[:150]
                            )
                    except Exception:
                        pass

                resultado["frames"].append(datos)

            page.screenshot(
                path=str(OUT / f"{nombre}.png"),
                full_page=True
            )

        except Exception as e:
            resultado["errores"].append(str(e))

        (OUT / f"{nombre}.json").write_text(
            json.dumps(
                resultado,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        print(json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2
        ))

        page.close()

    browser.close()
