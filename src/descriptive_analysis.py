"""
Análisis descriptivo: estadísticos, agregados nacionales y autonómicos, correlaciones.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY_VARS = [
    "precio_m2", "dln_precio", "pct_nacidos_ext", "pct_extranjeros", "flujo_nacidos_ext",
    "flujo_extranjeros", "ln_pib_pc", "g_pib_pc", "tasa_paro_ccaa", "ln_densidad",
    "pct_joven_25_34", "viv_term_1000hab", "tipo_interes_lp",
]

LABELS = {
    "precio_m2": "Precio vivienda (€/m²)",
    "dln_precio": "Δ ln precio (×100)",
    "pct_nacidos_ext": "% nacidos en el extranjero",
    "pct_extranjeros": "% extranjeros",
    "flujo_nacidos_ext": "Flujo nacidos ext. (% pob. t-1)",
    "flujo_extranjeros": "Flujo extranjeros (% pob. t-1)",
    "ln_pib_pc": "ln PIB per cápita",
    "g_pib_pc": "Crec. PIB pc (%)",
    "tasa_paro_ccaa": "Tasa de paro CCAA (%)",
    "ln_densidad": "ln densidad (hab/km²)",
    "pct_joven_25_34": "% población 25-34",
    "viv_term_1000hab": "Viviendas terminadas /1000 hab",
    "tipo_interes_lp": "Tipo interés 10 años (%)",
    "var_precio_pct": "Variación del precio de la vivienda (%, nominal)",
    "flujo_acum_pct_pob_ini": "Aumento de nacidos en el extranjero (% de la población inicial)",
    "d_pct_nacidos_ext": "Δ % nacidos en el extranjero (p.p.)",
}


def summary_statistics(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    cols = [c for c in (cols or KEY_VARS) if c in df.columns]
    s = df[cols].describe(percentiles=[0.25, 0.5, 0.75]).T
    s.insert(0, "descripcion", [LABELS.get(c, c) for c in s.index])
    s["missing"] = df[cols].isna().sum()
    return s.round(3)


def national_series(df: pd.DataFrame) -> pd.DataFrame:
    """Serie nacional: precio medio ponderado por población y % de nacidos en el extranjero."""
    def agg(g):
        out = {}
        if "precio_m2" in g and "poblacion" in g:
            m = g[["precio_m2", "poblacion"]].dropna()
            out["precio_m2_pond"] = np.average(m["precio_m2"], weights=m["poblacion"]) if len(m) else np.nan
        for num, name in (("nacidos_extranjero", "pct_nacidos_ext"), ("extranjeros", "pct_extranjeros")):
            if num in g and "poblacion" in g:
                m = g[[num, "poblacion"]].dropna()
                out[name] = 100 * m[num].sum() / m["poblacion"].sum() if len(m) else np.nan
        out["n_provincias"] = g["provincia_cod"].nunique()
        return pd.Series(out)
    return df.groupby("anio").apply(agg, include_groups=False).reset_index()


def ccaa_series(df: pd.DataFrame) -> pd.DataFrame:
    """Series por comunidad autónoma (precio ponderado por población y % nacidos fuera)."""
    rows = []
    for (ccaa, year), g in df.groupby(["ccaa", "anio"]):
        m = g.dropna(subset=["poblacion"])
        r = {"ccaa": ccaa, "anio": year}
        if "precio_m2" in g:
            mm = m.dropna(subset=["precio_m2"])
            r["precio_m2_pond"] = np.average(mm["precio_m2"], weights=mm["poblacion"]) if len(mm) else np.nan
        if "nacidos_extranjero" in g:
            mm = m.dropna(subset=["nacidos_extranjero"])
            r["pct_nacidos_ext"] = 100 * mm["nacidos_extranjero"].sum() / mm["poblacion"].sum() if len(mm) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def long_differences(df: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    """Cambio entre dos años por provincia (diferencias largas)."""
    a = df[df["anio"] == start].set_index("provincia_cod")
    b = df[df["anio"] == end].set_index("provincia_cod")
    out = pd.DataFrame(index=a.index.intersection(b.index))
    out["provincia"] = b["provincia"]
    out["ccaa"] = b["ccaa"]
    if "ln_precio" in df:
        out["var_precio_pct"] = 100 * (np.exp(b["ln_precio"] - a["ln_precio"]) - 1)
    if "pct_nacidos_ext" in df:
        out["var_pct_nacidos_ext_pp"] = b["pct_nacidos_ext"] - a["pct_nacidos_ext"]
    if {"nacidos_extranjero", "poblacion"}.issubset(df.columns):
        out["flujo_acum_pct_pob_ini"] = 100 * (b["nacidos_extranjero"] - a["nacidos_extranjero"]) / a["poblacion"]
    return out.reset_index()


def correlation_matrix(df: pd.DataFrame, cols: list[str] | None = None, method: str = "pearson") -> pd.DataFrame:
    cols = [c for c in (cols or KEY_VARS) if c in df.columns and df[c].notna().any()]
    return df[cols].corr(method=method)
