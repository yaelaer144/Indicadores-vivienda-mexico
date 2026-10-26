
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
