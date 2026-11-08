"""
Configuración central del proyecto.

Contiene:
- Rutas del repositorio (datos brutos, procesados, resultados).
- Tabla maestra de provincias (código INE, nombre, comunidad autónoma, NUTS-2 y NUTS-3).
- Modo DEMO: si la variable de entorno INMIG_DEMO=1 está activa, el pipeline usa datos
  SINTÉTICOS (generados en src/synthetic.py) y escribe todo en results/_demo/.
  El modo demo existe solo para comprobar que el código se ejecuta; sus cifras NO son reales.
"""
from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------------------
# Rutas
# --------------------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_EUROSTAT = RAW_DIR / "eurostat"
RAW_INE = RAW_DIR / "ine"
RAW_MITMA = RAW_DIR / "mitma"
RAW_MANUAL = RAW_DIR / "manual"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = ROOT / "results"


def is_demo() -> bool:
    """True si se ejecuta en modo demostración con datos sintéticos."""
    return os.environ.get("INMIG_DEMO", "0") == "1"


def results_root(demo: bool | None = None) -> Path:
    """Carpeta de resultados. En modo demo se separa para no mezclarlos con resultados reales."""
    demo = is_demo() if demo is None else demo
    return RESULTS_DIR / "_demo" if demo else RESULTS_DIR


def out_dirs(demo: bool | None = None) -> dict[str, Path]:
    root = results_root(demo)
    dirs = {"tables": root / "tables", "figures": root / "figures", "reports": root / "reports"}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


# --------------------------------------------------------------------------------------
# Provincias: (código INE, nombre, CCAA, NUTS-2, [NUTS-3 (versión 2016/2021)])
# Baleares y Canarias se dividen en islas en NUTS-3 desde 2013/2016; se agregan a provincia.
# Los códigos antiguos ES701/ES702 (Canarias, NUTS 2010) se incluyen por si aparecen.
# --------------------------------------------------------------------------------------
PROVINCES: list[tuple[str, str, str, str, list[str]]] = [
    ("01", "Araba/Álava", "País Vasco", "ES21", ["ES211"]),
    ("02", "Albacete", "Castilla-La Mancha", "ES42", ["ES421"]),
    ("03", "Alicante/Alacant", "Comunitat Valenciana", "ES52", ["ES521"]),
    ("04", "Almería", "Andalucía", "ES61", ["ES611"]),
    ("05", "Ávila", "Castilla y León", "ES41", ["ES411"]),
    ("06", "Badajoz", "Extremadura", "ES43", ["ES431"]),
    ("07", "Illes Balears", "Illes Balears", "ES53", ["ES531", "ES532", "ES533", "ES530"]),
    ("08", "Barcelona", "Cataluña", "ES51", ["ES511"]),
    ("09", "Burgos", "Castilla y León", "ES41", ["ES412"]),
    ("10", "Cáceres", "Extremadura", "ES43", ["ES432"]),
    ("11", "Cádiz", "Andalucía", "ES61", ["ES612"]),
    ("12", "Castellón/Castelló", "Comunitat Valenciana", "ES52", ["ES522"]),
    ("13", "Ciudad Real", "Castilla-La Mancha", "ES42", ["ES422"]),
    ("14", "Córdoba", "Andalucía", "ES61", ["ES613"]),
    ("15", "A Coruña", "Galicia", "ES11", ["ES111"]),
    ("16", "Cuenca", "Castilla-La Mancha", "ES42", ["ES423"]),
    ("17", "Girona", "Cataluña", "ES51", ["ES512"]),
    ("18", "Granada", "Andalucía", "ES61", ["ES614"]),
    ("19", "Guadalajara", "Castilla-La Mancha", "ES42", ["ES424"]),
    ("20", "Gipuzkoa", "País Vasco", "ES21", ["ES212"]),
    ("21", "Huelva", "Andalucía", "ES61", ["ES615"]),
    ("22", "Huesca", "Aragón", "ES24", ["ES241"]),
    ("23", "Jaén", "Andalucía", "ES61", ["ES616"]),
    ("24", "León", "Castilla y León", "ES41", ["ES413"]),
    ("25", "Lleida", "Cataluña", "ES51", ["ES513"]),
    ("26", "La Rioja", "La Rioja", "ES23", ["ES230"]),
    ("27", "Lugo", "Galicia", "ES11", ["ES112"]),
    ("28", "Madrid", "Comunidad de Madrid", "ES30", ["ES300"]),
    ("29", "Málaga", "Andalucía", "ES61", ["ES617"]),
    ("30", "Murcia", "Región de Murcia", "ES62", ["ES620"]),
    ("31", "Navarra", "Comunidad Foral de Navarra", "ES22", ["ES220"]),
    ("32", "Ourense", "Galicia", "ES11", ["ES113"]),
    ("33", "Asturias", "Principado de Asturias", "ES12", ["ES120"]),
    ("34", "Palencia", "Castilla y León", "ES41", ["ES414"]),
    ("35", "Las Palmas", "Canarias", "ES70", ["ES704", "ES705", "ES708", "ES701"]),
    ("36", "Pontevedra", "Galicia", "ES11", ["ES114"]),
    ("37", "Salamanca", "Castilla y León", "ES41", ["ES415"]),
    ("38", "Santa Cruz de Tenerife", "Canarias", "ES70", ["ES703", "ES706", "ES707", "ES709", "ES702"]),
    ("39", "Cantabria", "Cantabria", "ES13", ["ES130"]),
    ("40", "Segovia", "Castilla y León", "ES41", ["ES416"]),
    ("41", "Sevilla", "Andalucía", "ES61", ["ES618"]),
    ("42", "Soria", "Castilla y León", "ES41", ["ES417"]),
    ("43", "Tarragona", "Cataluña", "ES51", ["ES514"]),
    ("44", "Teruel", "Aragón", "ES24", ["ES242"]),
    ("45", "Toledo", "Castilla-La Mancha", "ES42", ["ES425"]),
    ("46", "Valencia/València", "Comunitat Valenciana", "ES52", ["ES523"]),
    ("47", "Valladolid", "Castilla y León", "ES41", ["ES418"]),
    ("48", "Bizkaia", "País Vasco", "ES21", ["ES213"]),
    ("49", "Zamora", "Castilla y León", "ES41", ["ES419"]),
    ("50", "Zaragoza", "Aragón", "ES24", ["ES243"]),
    ("51", "Ceuta", "Ceuta", "ES63", ["ES630"]),
    ("52", "Melilla", "Melilla", "ES64", ["ES640"]),
]

PROVINCE_CODES = [p[0] for p in PROVINCES]
PROVINCE_NAME = {p[0]: p[1] for p in PROVINCES}
PROVINCE_CCAA = {p[0]: p[2] for p in PROVINCES}
PROVINCE_NUTS2 = {p[0]: p[3] for p in PROVINCES}
NUTS3_TO_PROVINCE = {n3: p[0] for p in PROVINCES for n3 in p[4]}

# Provincias excluidas en algunas pruebas de robustez por ser atípicas
# (grandes metrópolis, territorios insulares muy turísticos y ciudades autónomas).
ATYPICAL_PROVINCES = ["28", "08", "07", "35", "38", "51", "52"]

# Periodos para análisis por submuestras (ciclo inmobiliario español)
SUBPERIODS = {
    "expansión (hasta 2007)": (1900, 2007),
    "crisis (2008-2013)": (2008, 2013),
    "recuperación (2014 en adelante)": (2014, 2100),
}
