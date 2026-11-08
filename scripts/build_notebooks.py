"""Genera los notebooks de notebooks/ a partir de este script (fuente única y revisable).

    python scripts/build_notebooks.py
"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"

SETUP = """# Configuración: raíz del repositorio en el path
import sys, os
from pathlib import Path
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Para comprobar el código sin datos reales: os.environ["INMIG_DEMO"] = "1"
from src import config
print("MODO DEMO (DATOS SINTÉTICOS)" if config.is_demo() else "Datos reales")"""

LOAD = """from src import data_cleaning as dc
panel = dc.load_panel()
print(panel.shape)
panel.head()"""

NOTEBOOKS = {
    "01_exploracion_datos.ipynb": [
        ("md", "# 01 · Exploración de datos\n\nComprobación de la disponibilidad, cobertura y calidad de las "
               "fuentes antes de cualquier estimación. Si faltan ficheros, ver `data/README.md`."),
        ("code", SETUP),
        ("code", "from src import data_collection as dcol\ndcol.check_manual_files()"),
        ("md", "## Construcción y validación del panel provincia × año"),
        ("code", LOAD),
        ("code", "rep = dc.validate_panel(panel)\n{k: v for k, v in rep.items() if k != 'missing_pct'}"),
        ("md", "## Datos ausentes por variable (%)\n\nLas variables con muchos ausentes limitan el periodo "
               "común de estimación."),
        ("code", "import pandas as pd\npd.Series(rep['missing_pct']).sort_values(ascending=False).head(25)"),
        ("md", "## Cobertura temporal por variable"),
        ("code", "cov = panel.groupby('anio')[[c for c in ['precio_m2','nacidos_extranjero','extranjeros',"
                 "'pib_meur','tasa_paro_ccaa','viviendas_terminadas'] if c in panel]].count()\ncov"),
    ],
    "02_analisis_descriptivo.ipynb": [
        ("md", "# 02 · Análisis descriptivo\n\nEvolución nacional y autonómica, distribución territorial, "
               "correlaciones y diferencias largas. Las correlaciones de esta sección **no** implican causalidad."),
        ("code", SETUP),
        ("code", LOAD),
        ("code", "from src import analysis\ndesc = analysis.stage_descriptive(panel)\ndesc['summary']"),
        ("code", "desc['national'].tail(10)"),
        ("code", "desc['corr'].round(2)"),
        ("md", "## Provincias con mayor variación del peso de la población nacida en el extranjero"),
        ("code", "desc['long_diff'].sort_values('var_pct_nacidos_ext_pp', ascending=False).head(10)"),
        ("code", "from IPython.display import Image\nout = config.out_dirs()\n"
                 "Image(filename=str(out['figures'] / '01_evolucion_nacional.png'))"),
    ],
    "03_modelos_mco.ipynb": [
        ("md", "# 03 · Regresión MCO\n\n$$\\Delta \\ln P_{pt}\\times 100 = \\alpha + \\beta\\, \\frac{\\Delta FB_{pt}}"
               "{Pob_{p,t-1}}\\times 100 + X_{pt}'\\gamma + \\varepsilon_{pt}$$\n\nMCO agrupado, errores agrupados "
               "por provincia. Sin efectos fijos, β recoge también diferencias permanentes entre provincias y "
               "shocks comunes: es una **asociación**, no un efecto causal."),
        ("code", SETUP),
        ("code", LOAD),
        ("code", "from src import analysis\nols = analysis.stage_ols(panel)\nols['table']"),
        ("code", "print(ols['models'][1].raw.summary())"),
    ],
    "04_modelos_panel.ipynb": [
        ("md", "# 04 · Datos de panel con efectos fijos\n\n$$\\Delta \\ln P_{pt}\\times 100 = \\beta\\, m_{pt} + "
               "X_{pt}'\\gamma + \\mu_p + \\tau_t + \\varepsilon_{pt}$$\n\n- $\\mu_p$: efectos fijos provinciales "
               "(tendencias de precio específicas de cada provincia).\n- $\\tau_t$: efectos fijos de año (ciclo "
               "nacional, tipos de interés, crédito, política monetaria).\n- Errores agrupados por provincia.\n\n"
               "Incluye flujo retardado, retardos distribuidos (efecto acumulado) y contrastes de Wald."),
        ("code", SETUP),
        ("code", LOAD),
        ("code", "from src import analysis\npan = analysis.stage_panel(panel)\npan['table']"),
        ("code", "pan['diagnostics']"),
        ("code", "print(pan['main'].raw)"),
    ],
    "05_robustez_y_causalidad.ipynb": [
        ("md", "# 05 · Robustez e identificación causal\n\n**Instrumento shift-share (Card, 2001; González y "
               "Ortega, 2013):** el flujo predicho asigna a cada provincia el crecimiento nacional de cada "
               "nacionalidad (excluida la propia provincia) según la distribución inicial de esa nacionalidad. "
               "Supuesto clave: las cuotas iniciales no están correlacionadas con shocks posteriores de "
               "demanda de vivienda (Goldsmith-Pinkham et al., 2020). Ver `docs/methodology.md`."),
        ("code", SETUP),
        ("code", LOAD),
        ("code", "from src import analysis\nnat = dc.load_nationalities()\n"
                 "ivr = analysis.stage_iv_robustness(panel, nat)\nivr.get('iv_table', 'IV no estimado: faltan datos por nacionalidad')"),
        ("code", "ivr['robustness'].round(4)"),
        ("code", "ivr['loo'][['provincia','coef','ci_low','ci_high']].sort_values('coef').round(4)"),
        ("code", "ivr['vif'], ivr['wooldridge']"),
        ("md", "## Informe automático\n\nEl resumen se genera solo a partir de las estimaciones anteriores."),
        ("code", "from src import analysis as a\nols = a.stage_ols(panel); pan = a.stage_panel(panel)\n"
                 "desc = a.stage_descriptive(panel)\nfrom IPython.display import Markdown\n"
                 "Markdown(a.write_report(panel, desc, ols, pan, ivr))"),
    ],
}


def build() -> None:
    NB_DIR.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(s) if t == "md" else nbf.v4.new_code_cell(s) for t, s in cells]
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        nbf.write(nb, NB_DIR / name)
        print("escrito", name)


if __name__ == "__main__":
    build()
