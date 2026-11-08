"""
Ejecuta el proyecto completo de principio a fin.

    python -m src.run_pipeline                 # datos reales (descarga + panel + modelos)
    python -m src.run_pipeline --skip-download # usa los datos ya descargados
    python -m src.run_pipeline --demo          # datos SINTÉTICOS, solo para comprobar el código
"""
from __future__ import annotations

import argparse
import logging
import os


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true", help="Usar datos sintéticos (no reales)")
    p.add_argument("--skip-download", action="store_true", help="No descargar datos de Eurostat")
    p.add_argument("--base-year", type=int, default=None, help="Año base del instrumento shift-share")
    args = p.parse_args()
    if args.demo:
        os.environ["INMIG_DEMO"] = "1"
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from . import analysis, data_cleaning, data_collection

    if not args.demo:
        if not args.skip_download:
            data_collection.collect_all()
        panel = data_cleaning.build_panel()
    else:
        panel = data_cleaning.load_panel(demo=True)
    nat = data_cleaning.load_nationalities()

    desc = analysis.stage_descriptive(panel)
    ols = analysis.stage_ols(panel)
    pan = analysis.stage_panel(panel)
    ivr = analysis.stage_iv_robustness(panel, nat, base_year=args.base_year)
    print(analysis.write_report(panel, desc, ols, pan, ivr))


if __name__ == "__main__":
    main()
