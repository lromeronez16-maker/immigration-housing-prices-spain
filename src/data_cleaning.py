"""
Limpieza, armonización y construcción del panel provincia × año.

Flujo:
1. Carga de los ficheros brutos (Eurostat automáticos + ficheros manuales con esquema fijo).
2. Paso de NUTS-3 a provincia (las islas de Baleares y Canarias se agregan).
3. Unión en un panel balanceado o no balanceado (52 provincias × años).
4. Construcción de variables derivadas (logaritmos, tasas, flujos migratorios).
5. Validación de estructura y rangos.

Nota terminológica (ver docs/methodology.md):
- `nacidos_extranjero`: población residente nacida fuera de España (incluye nacionalizados).
- `extranjeros`: población residente con nacionalidad extranjera (excluye nacionalizados,
  incluye nacidos en España de nacionalidad extranjera).
- Los *flujos* se aproximan como variación interanual del stock (padrón a 1 de enero),
  que es la variación neta (entradas - salidas - nacionalizaciones/defunciones, según la definición).
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from . import config

log = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Esquemas de los ficheros manuales (columnas obligatorias -> tipo)
# --------------------------------------------------------------------------------------
MANUAL_SCHEMAS: dict[str, dict] = {
    "poblacion_inmigrante.csv": {
        "required": {"provincia_cod": str, "anio": int, "nacidos_extranjero": float, "extranjeros": float},
        "optional": {"poblacion_total": float, "anio_padron": int},
    },
    "precio_vivienda.csv": {
        # trimestre puede faltar si el dato ya es anual
        "required": {"provincia_cod": str, "anio": int, "precio_m2": float},
        "optional": {"trimestre": int},
    },
    "extranjeros_nacionalidad.csv": {
        "required": {"provincia_cod": str, "anio": int, "nacionalidad": str, "poblacion": float},
        "optional": {},
    },
    "viviendas_terminadas.csv": {
        "required": {"provincia_cod": str, "anio": int, "viviendas_terminadas": float},
        "optional": {},
    },
}


class DataValidationError(ValueError):
    """Error de validación de datos (estructura, claves o rangos)."""


# --------------------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------------------
def normalize_province_code(s: pd.Series) -> pd.Series:
    """Convierte códigos de provincia a texto de dos dígitos ('1' -> '01')."""
    return s.astype(str).str.strip().str.extract(r"(\d+)")[0].str.zfill(2)


def load_manual(fname: str, manual_dir: Path = config.RAW_MANUAL) -> pd.DataFrame | None:
    """Carga y valida un fichero manual. Devuelve None si no existe."""
    path = manual_dir / fname
    if not path.exists():
        log.warning("No existe %s", path)
        return None
    schema = MANUAL_SCHEMAS[fname]
    df = pd.read_csv(path, dtype={"provincia_cod": str})
    missing = [c for c in schema["required"] if c not in df.columns]
    if missing:
        raise DataValidationError(f"{fname}: faltan columnas obligatorias {missing}")
    df["provincia_cod"] = normalize_province_code(df["provincia_cod"])
    for col, typ in {**schema["required"], **schema["optional"]}.items():
        if col in df.columns and col != "provincia_cod":
            df[col] = df[col].astype(str) if typ is str else pd.to_numeric(df[col], errors="coerce")
    bad = sorted(set(df["provincia_cod"]) - set(config.PROVINCE_CODES))
    if bad:
        raise DataValidationError(f"{fname}: códigos de provincia no válidos {bad}")
    return df


def load_eurostat(name: str, raw_dir: Path = config.RAW_EUROSTAT) -> pd.DataFrame | None:
    path = raw_dir / f"{name}.csv"
    if not path.exists():
        log.warning("No existe %s (ejecuta python -m src.data_collection)", path)
        return None
    return pd.read_csv(path)


def nuts3_to_province(df: pd.DataFrame, value_col: str = "valor", extra_keys: list[str] | None = None) -> pd.DataFrame:
    """Agrega una variable aditiva NUTS-3 a provincia (suma de islas en Baleares y Canarias).

    Si para una provincia insular conviven códigos NUTS antiguos y nuevos en el mismo año
    (p. ej. ES530 y ES531-533), se usan solo los nuevos para no duplicar.
    """
    extra_keys = extra_keys or []
    d = df[df["geo"].isin(config.NUTS3_TO_PROVINCE)].copy()
    d["provincia_cod"] = d["geo"].map(config.NUTS3_TO_PROVINCE)
    old_codes = {"ES530", "ES701", "ES702"}
    d["_old"] = d["geo"].isin(old_codes)
    keys = ["provincia_cod", "anio"] + extra_keys
    has_new = d[~d["_old"]].groupby(keys)[value_col].count().rename("_n_new").reset_index()
    d = d.merge(has_new, on=keys, how="left")
    d = d[~(d["_old"] & (d["_n_new"].fillna(0) > 0))]
    out = d.groupby(keys, as_index=False)[value_col].sum(min_count=1)
    return out


def nuts2_to_province(df: pd.DataFrame, value_col: str = "valor") -> pd.DataFrame:
    """Asigna a cada provincia el valor de su NUTS-2 (CCAA). Para variables no aditivas (tasas)."""
    rows = []
    d = df.set_index(["geo", "anio"])[value_col]
    for cod in config.PROVINCE_CODES:
        n2 = config.PROVINCE_NUTS2[cod]
        if n2 in d.index.get_level_values(0):
            s = d.loc[n2]
            rows.append(pd.DataFrame({"provincia_cod": cod, "anio": s.index, value_col: s.values}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["provincia_cod", "anio", value_col])


def annualize_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Media anual del precio €/m² si los datos son trimestrales. Exige 4 trimestres por año.
    Los precios no positivos se tratan como ausentes."""
    prices = prices.copy()
    prices.loc[prices["precio_m2"] <= 0, "precio_m2"] = np.nan
    prices = prices.dropna(subset=["precio_m2"])
    if "trimestre" not in prices.columns or prices["trimestre"].isna().all():
        return prices[["provincia_cod", "anio", "precio_m2"]].copy()
    g = prices.groupby(["provincia_cod", "anio"])["precio_m2"]
    out = g.mean().to_frame()
    out["n_trim"] = g.count()
    # Precio del 4.º trimestre: coincide con la fecha del stock del Padrón a final de año
    q4 = prices[prices["trimestre"] == 4].set_index(["provincia_cod", "anio"])["precio_m2"]
    out["precio_m2_t4"] = q4.reindex(out.index)
    incomplete = out[out["n_trim"] < 4]
    if len(incomplete):
        log.info("Se descartan %d provincia-años con menos de 4 trimestres de precio", len(incomplete))
    out = out[out["n_trim"] == 4].drop(columns="n_trim").reset_index()
    return out


# --------------------------------------------------------------------------------------
# Controles desde Eurostat
# --------------------------------------------------------------------------------------
def build_eurostat_controls(raw_dir: Path = config.RAW_EUROSTAT) -> pd.DataFrame:
    """Construye controles provinciales a partir de los CSV de Eurostat disponibles."""
    parts: list[pd.DataFrame] = []

    pib = load_eurostat("pib_nuts3", raw_dir)
    if pib is not None:
        parts.append(nuts3_to_province(pib).rename(columns={"valor": "pib_meur"}))

    pob = load_eurostat("poblacion_nuts3", raw_dir)
    if pob is not None:
        parts.append(nuts3_to_province(pob).rename(columns={"valor": "poblacion_eurostat"}))

    edad = load_eurostat("poblacion_edad_nuts3", raw_dir)
    if edad is not None:
        e = nuts3_to_province(edad, extra_keys=["age"])
        e = e.pivot_table(index=["provincia_cod", "anio"], columns="age", values="valor").reset_index()
        if {"TOTAL", "Y25-29", "Y30-34"}.issubset(e.columns):
            e["pct_joven_25_34"] = 100 * (e["Y25-29"] + e["Y30-34"]) / e["TOTAL"]
            parts.append(e[["provincia_cod", "anio", "pct_joven_25_34"]])

    area = load_eurostat("superficie_nuts3", raw_dir)
    if area is not None:
        parts.append(nuts3_to_province(area).rename(columns={"valor": "superficie_km2"}))

    paro = load_eurostat("paro_nuts2", raw_dir)
    if paro is not None:
        parts.append(nuts2_to_province(paro).rename(columns={"valor": "tasa_paro_ccaa"}))

    out = None
    for p in parts:
        p["anio"] = p["anio"].astype(int)
        out = p if out is None else out.merge(p, on=["provincia_cod", "anio"], how="outer")

    tipo = load_eurostat("tipo_interes_lp", raw_dir)
    if out is not None and tipo is not None:
        t = tipo[tipo["geo"] == "ES"][["anio", "valor"]].rename(columns={"valor": "tipo_interes_lp"})
        out = out.merge(t, on="anio", how="left")
    if out is not None and "superficie_km2" in out.columns:
        # La superficie apenas varía: se rellena con el último valor disponible de cada provincia
        out = out.sort_values(["provincia_cod", "anio"])
        out["superficie_km2"] = out.groupby("provincia_cod")["superficie_km2"].transform(lambda s: s.ffill().bfill())
    return out if out is not None else pd.DataFrame(columns=["provincia_cod", "anio"])


# --------------------------------------------------------------------------------------
# Variables derivadas
# --------------------------------------------------------------------------------------
def _lag(df: pd.DataFrame, col: str, k: int = 1) -> pd.Series:
    """Retardo dentro de provincia que respeta huecos en los años (no usa el año anterior disponible
    si no es exactamente t-k)."""
    prev = df[["provincia_cod", "anio", col]].copy()
    prev["anio"] = prev["anio"] + k
    merged = df[["provincia_cod", "anio"]].merge(prev, on=["provincia_cod", "anio"], how="left")
    return merged[col].astype(float).to_numpy()


def add_derived_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula las variables del modelo. Todas las tasas en puntos porcentuales."""
    df = df.sort_values(["provincia_cod", "anio"]).reset_index(drop=True).copy()

    # Población de referencia: la del Padrón (INE) si se aporta; si no, Eurostat
    if "poblacion_total" in df.columns and df["poblacion_total"].notna().any():
        df["poblacion"] = df["poblacion_total"]
        if "poblacion_eurostat" in df.columns:
            df["poblacion"] = df["poblacion"].fillna(df["poblacion_eurostat"])
    elif "poblacion_eurostat" in df.columns:
        df["poblacion"] = df["poblacion_eurostat"]

    if "precio_m2" in df.columns:
        df["ln_precio"] = np.log(df["precio_m2"])
        df["dln_precio"] = 100 * (df["ln_precio"] - _lag(df, "ln_precio"))
    if "precio_m2_t4" in df.columns:
        df["ln_precio_t4"] = np.log(df["precio_m2_t4"])
        df["dln_precio_t4"] = 100 * (df["ln_precio_t4"] - _lag(df, "ln_precio_t4"))

    if {"nacidos_extranjero", "poblacion"}.issubset(df.columns):
        pop_l1 = _lag(df, "poblacion")
        df["pct_nacidos_ext"] = 100 * df["nacidos_extranjero"] / df["poblacion"]
        # Variación de la proporción (p.p.): no depende del tamaño de la población
        df["d_pct_nacidos_ext"] = df["pct_nacidos_ext"] - _lag(df, "pct_nacidos_ext")
        df["flujo_nacidos_ext"] = 100 * (df["nacidos_extranjero"] - _lag(df, "nacidos_extranjero")) / pop_l1
        df["g_nacidos_ext"] = 100 * (np.log(df["nacidos_extranjero"]) - np.log(_lag(df, "nacidos_extranjero")))
        df["poblacion_nativa"] = df["poblacion"] - df["nacidos_extranjero"]
        df["flujo_nativos"] = 100 * (df["poblacion_nativa"] - _lag(df, "poblacion_nativa")) / pop_l1
        df["g_poblacion"] = 100 * (np.log(df["poblacion"]) - np.log(pop_l1))
    if {"extranjeros", "poblacion"}.issubset(df.columns):
        pop_l1 = _lag(df, "poblacion")
        df["pct_extranjeros"] = 100 * df["extranjeros"] / df["poblacion"]
        df["d_pct_extranjeros"] = df["pct_extranjeros"] - _lag(df, "pct_extranjeros")
        df["flujo_extranjeros"] = 100 * (df["extranjeros"] - _lag(df, "extranjeros")) / pop_l1

    if {"pib_meur", "poblacion"}.issubset(df.columns):
        df["ln_pib_pc"] = np.log(df["pib_meur"] * 1e6 / df["poblacion"])
        df["g_pib_pc"] = 100 * (df["ln_pib_pc"] - _lag(df, "ln_pib_pc"))
        df["g_pib"] = 100 * (np.log(df["pib_meur"]) - np.log(_lag(df, "pib_meur")))
    if {"superficie_km2", "poblacion"}.issubset(df.columns):
        df["ln_densidad"] = np.log(df["poblacion"] / df["superficie_km2"])
    if "tasa_paro_ccaa" in df.columns:
        df["d_tasa_paro"] = df["tasa_paro_ccaa"] - _lag(df, "tasa_paro_ccaa")
    if "pct_joven_25_34" in df.columns:
        df["d_pct_joven"] = df["pct_joven_25_34"] - _lag(df, "pct_joven_25_34")
    if {"viviendas_terminadas", "poblacion"}.issubset(df.columns):
        df["viv_term_1000hab"] = 1000 * df["viviendas_terminadas"] / df["poblacion"]

    # Retardos de las variables migratorias principales
    for col in ["flujo_nacidos_ext", "flujo_extranjeros", "pct_nacidos_ext"]:
        if col in df.columns:
            df[f"{col}_l1"] = _lag(df, col, 1)
            df[f"{col}_l2"] = _lag(df, col, 2)
    if "viv_term_1000hab" in df.columns:
        df["viv_term_1000hab_l1"] = _lag(df, "viv_term_1000hab", 1)

    df["ccaa"] = df["provincia_cod"].map(config.PROVINCE_CCAA)
    df["provincia"] = df["provincia_cod"].map(config.PROVINCE_NAME)
    return df


# --------------------------------------------------------------------------------------
# Validación
# --------------------------------------------------------------------------------------
def validate_panel(df: pd.DataFrame) -> dict:
    """Comprueba claves únicas, rangos plausibles y cobertura. Lanza error si algo es inválido."""
    if df.duplicated(["provincia_cod", "anio"]).any():
        dups = df[df.duplicated(["provincia_cod", "anio"], keep=False)][["provincia_cod", "anio"]]
        raise DataValidationError(f"Claves duplicadas provincia-año:\n{dups.head()}")
    checks = {
        "precio_m2": (1, 20000),
        "pct_nacidos_ext": (0, 100),
        "pct_extranjeros": (0, 100),
        "tasa_paro_ccaa": (0, 60),
        "pct_joven_25_34": (0, 50),
    }
    for col, (lo, hi) in checks.items():
        if col in df.columns:
            s = df[col].dropna()
            if ((s < lo) | (s > hi)).any():
                raise DataValidationError(f"{col} fuera de rango [{lo}, {hi}]")
    if {"nacidos_extranjero", "poblacion"}.issubset(df.columns):
        if (df["nacidos_extranjero"] > df["poblacion"]).any():
            raise DataValidationError("Nacidos en el extranjero > población total")
    report = {
        "provincias": int(df["provincia_cod"].nunique()),
        "anios": (int(df["anio"].min()), int(df["anio"].max())),
        "observaciones": int(len(df)),
        "missing_pct": df.isna().mean().mul(100).round(1).to_dict(),
    }
    return report


# --------------------------------------------------------------------------------------
# Construcción del panel
# --------------------------------------------------------------------------------------
def build_panel(manual_dir: Path = config.RAW_MANUAL, raw_eurostat: Path = config.RAW_EUROSTAT,
                save: bool = True) -> pd.DataFrame:
    """Construye el panel provincia-año a partir de los datos reales descargados."""
    inm = load_manual("poblacion_inmigrante.csv", manual_dir)
    precios = load_manual("precio_vivienda.csv", manual_dir)
    if inm is None or precios is None:
        raise FileNotFoundError(
            "Faltan ficheros obligatorios en data/raw/manual/ "
            "(poblacion_inmigrante.csv y precio_vivienda.csv). Ver data/README.md."
        )
    # Ventana común: solo años con precio Y datos de inmigración (mismo periodo en todas las fuentes)
    precios_a = annualize_prices(precios)
    common = sorted(set(precios_a["anio"]) & set(inm["anio"]))
    if not common:
        raise DataValidationError("No hay años comunes entre precios e inmigración")
    precios_a = precios_a[precios_a["anio"].between(common[0], common[-1])]
    inm = inm[inm["anio"].between(common[0], common[-1])]
    log.info("Ventana común precios-inmigración: %s-%s", common[0], common[-1])
    panel = precios_a.merge(inm, on=["provincia_cod", "anio"], how="outer")
    viv = load_manual("viviendas_terminadas.csv", manual_dir)
    if viv is not None:
        panel = panel.merge(viv, on=["provincia_cod", "anio"], how="left")
    controls = build_eurostat_controls(raw_eurostat)
    if len(controls):
        panel = panel.merge(controls, on=["provincia_cod", "anio"], how="left")
    panel = add_derived_variables(panel)
    report = validate_panel(panel)
    log.info("Panel construido: %s", {k: v for k, v in report.items() if k != "missing_pct"})
    if save:
        config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        panel.to_csv(config.PROCESSED_DIR / "panel_provincial.csv", index=False)
    return panel


def load_panel(demo: bool | None = None) -> pd.DataFrame:
    """Devuelve el panel procesado real o, en modo demo, uno sintético."""
    demo = config.is_demo() if demo is None else demo
    if demo:
        from .synthetic import make_synthetic_panel
        return add_derived_variables(make_synthetic_panel())
    path = config.PROCESSED_DIR / "panel_provincial.csv"
    if not path.exists():
        return build_panel()
    return pd.read_csv(path, dtype={"provincia_cod": str})


def load_nationalities(demo: bool | None = None) -> pd.DataFrame | None:
    demo = config.is_demo() if demo is None else demo
    if demo:
        from .synthetic import make_synthetic_nationalities
        return make_synthetic_nationalities()
    return load_manual("extranjeros_nacionalidad.csv")
