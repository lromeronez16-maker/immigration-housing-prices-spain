"""
Descarga de datos oficiales y registro de su procedencia.

Fuentes automáticas (vía API):
- Eurostat (paquete `eurostat`): PIB NUTS-3, población NUTS-3, población por edad NUTS-3,
  superficie NUTS-3, tasa de paro NUTS-2, tipo de interés a largo plazo de España.
- INE (API JSON "Tempus"): cualquier tabla de INEbase a partir de su identificador.

Fuentes manuales (requieren descarga desde la web oficial; ver data/README.md):
- Población nacida en el extranjero y población extranjera por provincia (INE, Padrón).
- Población extranjera por nacionalidad y provincia (INE, Padrón) -> instrumento shift-share.
- Valor tasado medio de la vivienda libre por provincia (MIVAU/MITMA).
- Viviendas libres terminadas por provincia (MIVAU), opcional.

Cada descarga guarda el fichero original sin modificar en data/raw/ junto con un fichero
`.meta.json` con la URL, fecha y hora de descarga, número de filas y hash SHA-256.

Uso:
    python -m src.data_collection            # descarga lo automático y revisa lo manual
    python -m src.data_collection --ine 2852 # descarga además una tabla del INE por id
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import re
from pathlib import Path

import pandas as pd

from . import config

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Catálogo de Eurostat. Los filtros se aplican localmente solo sobre dimensiones existentes,
# de modo que un cambio menor en la estructura del dataset no rompe la descarga.
# --------------------------------------------------------------------------------------
EUROSTAT_DATASETS: dict[str, dict] = {
    "pib_nuts3": {
        "code": "nama_10r_3gdp",
        "filters": {"unit": ["MIO_EUR"]},
        "geo_prefix": "ES",
        "descripcion": "PIB a precios corrientes de mercado, millones de euros, NUTS-3.",
    },
    "poblacion_nuts3": {
        "code": "demo_r_pjanaggr3",
        "filters": {"sex": ["T"], "age": ["TOTAL"], "unit": ["NR"]},
        "geo_prefix": "ES",
        "descripcion": "Población a 1 de enero, total, NUTS-3.",
    },
    "poblacion_edad_nuts3": {
        "code": "demo_r_pjangrp3",
        "filters": {"sex": ["T"], "unit": ["NR"], "age": ["TOTAL", "Y25-29", "Y30-34"]},
        "geo_prefix": "ES",
        "descripcion": "Población a 1 de enero por grupos quinquenales de edad, NUTS-3.",
    },
    "superficie_nuts3": {
        "code": "demo_r_d3area",
        "filters": {"unit": ["KM2"], "landuse": ["TOTAL"]},
        "geo_prefix": "ES",
        "descripcion": "Superficie total en km², NUTS-3.",
    },
    "paro_nuts2": {
        "code": "lfst_r_lfu3rt",
        "filters": {"sex": ["T"], "age": ["Y15-74"], "unit": ["PC"], "isced11": ["TOTAL"]},
        "geo_prefix": "ES",
        "descripcion": "Tasa de paro (% población activa 15-74), NUTS-2 (CCAA). EPA armonizada.",
    },
    "tipo_interes_lp": {
        "code": "irt_lt_mcby_a",
        "filters": {"geo": ["ES"]},
        "geo_prefix": "ES",
        "descripcion": "Rendimiento de la deuda pública a 10 años (criterio de convergencia), España, anual.",
    },
}

INE_API = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table_id}?tip=AM"

# Ficheros que deben aportarse manualmente (ver esquema en data_cleaning.MANUAL_SCHEMAS)
MANUAL_FILES = {
    "poblacion_inmigrante.csv": "OBLIGATORIO - INE Padrón: nacidos en el extranjero y extranjeros por provincia y año.",
    "precio_vivienda.csv": "OBLIGATORIO - MIVAU: valor tasado medio vivienda libre (€/m²) por provincia y trimestre/año.",
    "extranjeros_nacionalidad.csv": "OPCIONAL (necesario para IV shift-share) - INE Padrón: extranjeros por nacionalidad y provincia.",
    "viviendas_terminadas.csv": "OPCIONAL - MIVAU: viviendas libres terminadas por provincia y año.",
}


# --------------------------------------------------------------------------------------
# Utilidades de trazabilidad
# --------------------------------------------------------------------------------------
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_metadata(path: Path, **info) -> Path:
    """Escribe <fichero>.meta.json con la procedencia del fichero descargado."""
    meta = {
        "fichero": path.name,
        "descargado_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256": _sha256(path),
        **info,
    }
    meta_path = path.with_suffix(path.suffix + ".meta.json")
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta_path


# --------------------------------------------------------------------------------------
# Eurostat
# --------------------------------------------------------------------------------------
def eurostat_wide_to_long(df: pd.DataFrame) -> pd.DataFrame:
    """Convierte la salida ancha del paquete `eurostat` (una columna por año) a formato largo."""
    df = df.copy()
    geo_col = next((c for c in df.columns if str(c).startswith("geo")), None)
    if geo_col is None:
        raise ValueError("No se encuentra la columna geográfica en el dataset de Eurostat")
    df = df.rename(columns={geo_col: "geo"})
    year_cols = [c for c in df.columns if re.fullmatch(r"\d{4}", str(c))]
    id_cols = [c for c in df.columns if c not in year_cols]
    long = df.melt(id_vars=id_cols, value_vars=year_cols, var_name="anio", value_name="valor")
    long["anio"] = long["anio"].astype(int)
    long["valor"] = pd.to_numeric(long["valor"], errors="coerce")
    return long


def fetch_eurostat(name: str, out_dir: Path = config.RAW_EUROSTAT) -> Path:
    """Descarga un dataset de Eurostat, filtra España y guarda CSV largo + metadatos."""
    import eurostat  # importación diferida: solo necesaria para descargar

    spec = EUROSTAT_DATASETS[name]
    log.info("Descargando Eurostat %s (%s)", spec["code"], name)
    wide = eurostat.get_data_df(spec["code"])
    long = eurostat_wide_to_long(wide)
    for dim, values in spec["filters"].items():
        if dim in long.columns:
            long = long[long[dim].isin(values)]
        else:
            log.warning("Dimensión '%s' no existe en %s; filtro ignorado", dim, spec["code"])
    long = long[long["geo"].astype(str).str.startswith(spec["geo_prefix"])]
    if long.empty:
        raise RuntimeError(f"El dataset {spec['code']} quedó vacío tras filtrar; revisa los filtros")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.csv"
    long.to_csv(path, index=False)
    write_metadata(
        path,
        fuente="Eurostat",
        dataset=spec["code"],
        url=f"https://ec.europa.eu/eurostat/databrowser/view/{spec['code']}/default/table",
        descripcion=spec["descripcion"],
        filtros=spec["filters"],
        filas=len(long),
    )
    return path


# --------------------------------------------------------------------------------------
# INE (API Tempus)
# --------------------------------------------------------------------------------------
def fetch_ine_table(table_id: int | str, out_dir: Path = config.RAW_INE, timeout: int = 120) -> Path:
    """Descarga una tabla de INEbase en JSON (sin modificar) a partir de su identificador.

    El identificador es el número `t=` de la URL de la tabla en INEbase
    (p. ej. https://www.ine.es/jaxiT3/Tabla.htm?t=XXXX).
    """
    import requests

    url = INE_API.format(table_id=table_id)
    log.info("Descargando INE tabla %s", table_id)
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"ine_tabla_{table_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    write_metadata(path, fuente="INE", tabla=str(table_id), url=url, series=len(data))
    return path


def ine_json_to_long(path: Path) -> pd.DataFrame:
    """Aplana el JSON de la API Tempus del INE: una fila por serie y periodo.

    Columnas: cod_serie, nombre, metadatos (variables de la serie unidas por ' | '),
    anio, periodo, valor. La identificación de provincia/variable se hace después en
    data_cleaning a partir de `nombre`/`metadatos`, porque cada tabla del INE tiene
    una estructura distinta.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = []
    for serie in data:
        meta = " | ".join(m.get("Nombre", "") for m in serie.get("MetaData", []) or [])
        for obs in serie.get("Data", []) or []:
            rows.append(
                {
                    "cod_serie": serie.get("COD"),
                    "nombre": serie.get("Nombre"),
                    "metadatos": meta,
                    "anio": obs.get("Anyo"),
                    "periodo": obs.get("FK_Periodo"),
                    "valor": obs.get("Valor"),
                    "secreto": obs.get("Secreto"),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Comprobación de ficheros manuales
# --------------------------------------------------------------------------------------
def check_manual_files(manual_dir: Path = config.RAW_MANUAL) -> pd.DataFrame:
    """Informa de qué ficheros manuales están presentes."""
    rows = []
    for fname, desc in MANUAL_FILES.items():
        rows.append({"fichero": fname, "presente": (manual_dir / fname).exists(), "descripcion": desc})
    return pd.DataFrame(rows)


def collect_all(ine_tables: list[str] | None = None) -> None:
    """Descarga todas las fuentes automáticas e informa de las manuales pendientes."""
    for name in EUROSTAT_DATASETS:
        try:
            fetch_eurostat(name)
        except Exception as exc:  # se continúa con el resto y se informa
            log.error("Fallo al descargar %s: %s", name, exc)
    for t in ine_tables or []:
        try:
            fetch_ine_table(t)
        except Exception as exc:
            log.error("Fallo al descargar tabla INE %s: %s", t, exc)
    status = check_manual_files()
    print("\nEstado de los ficheros manuales (data/raw/manual/):")
    print(status.to_string(index=False))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ine", nargs="*", default=[], help="Identificadores de tablas INE a descargar")
    args = p.parse_args()
    collect_all(args.ine)


if __name__ == "__main__":
    main()
