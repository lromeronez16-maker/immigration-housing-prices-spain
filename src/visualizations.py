"""
Gráficos del proyecto. Todos incluyen título, unidades, periodo y fuente.
En modo demo se añade una marca de agua "DATOS SINTÉTICOS".
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

from .descriptive_analysis import LABELS  # noqa: E402

SRC_PRICE = "MIVAU (valor tasado vivienda libre)"
SRC_MIG = "INE (Estadística del Padrón Continuo)"
SRC_EUROSTAT = "Eurostat"

sns.set_theme(style="whitegrid", context="notebook")
PALETTE = ["#1f4e79", "#c0504d", "#4f9a94", "#e3a33b", "#7f7f7f"]

GEOJSON_URL = ("https://raw.githubusercontent.com/codeforgermany/click_that_hood/main/"
               "public/data/spain-provinces.geojson")


def _finish(fig, path: Path, source: str, period: str, demo: bool) -> Path:
    fig.text(0.01, 0.005, f"Fuente: {source}. Periodo: {period}. Elaboración propia.",
             fontsize=8, color="#555555", ha="left", va="bottom")
    if demo:
        fig.text(0.5, 0.5, "DATOS SINTÉTICOS\nNO SON RESULTADOS REALES", fontsize=30, color="red",
                 alpha=0.18, ha="center", va="center", rotation=25, weight="bold")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def _period(df) -> str:
    return f"{int(df['anio'].min())}-{int(df['anio'].max())}"


def plot_national_evolution(nat: pd.DataFrame, path: Path, demo=False) -> Path:
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(nat["anio"], nat["precio_m2_pond"], color=PALETTE[0], lw=2, label="Precio vivienda (€/m²)")
    ax1.set_ylabel("Precio medio ponderado (€/m², corrientes)", color=PALETTE[0])
    ax2 = ax1.twinx()
    if "pct_nacidos_ext" in nat:
        ax2.plot(nat["anio"], nat["pct_nacidos_ext"], color=PALETTE[1], lw=2, label="% nacidos en el extranjero")
    if "pct_extranjeros" in nat:
        ax2.plot(nat["anio"], nat["pct_extranjeros"], color=PALETTE[1], lw=1.5, ls="--", label="% extranjeros")
    ax2.set_ylabel("% de la población residente", color=PALETTE[1])
    ax2.grid(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=True)
    ax1.set_title("España: precio de la vivienda y población de origen extranjero")
    ax1.set_xlabel("Año")
    return _finish(fig, path, f"{SRC_PRICE}; {SRC_MIG}", _period(nat), demo)


def plot_ccaa_small_multiples(cc: pd.DataFrame, var: str, path: Path, demo=False) -> Path:
    regions = sorted(cc["ccaa"].dropna().unique())
    n = len(regions)
    ncols = 5
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(16, 3 * nrows), sharex=True, sharey=True)
    for ax, r in zip(axes.flat, regions):
        s = cc[cc["ccaa"] == r]
        ax.plot(s["anio"], s[var], color=PALETTE[0])
        ax.set_title(r, fontsize=9)
    for ax in list(axes.flat)[n:]:
        ax.axis("off")
    unit = "€/m²" if "precio" in var else "% población"
    fig.suptitle(f"{'Precio de la vivienda' if 'precio' in var else 'Población nacida en el extranjero'} "
                 f"por comunidad autónoma ({unit})", y=1.0)
    src = SRC_PRICE if "precio" in var else SRC_MIG
    return _finish(fig, path, src, _period(cc), demo)


def plot_scatter(df: pd.DataFrame, x: str, y: str, path: Path, title: str, demo=False,
                 label_col: str | None = None, source=f"{SRC_PRICE}; {SRC_MIG}", period=None) -> Path:
    d = df[[x, y] + ([label_col] if label_col else [])].replace([np.inf, -np.inf], np.nan).dropna()
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.regplot(data=d, x=x, y=y, ax=ax, scatter_kws={"alpha": 0.5, "s": 18, "color": PALETTE[0]},
                line_kws={"color": PALETTE[1]})
    if label_col:
        for _, r in d.iterrows():
            ax.annotate(str(r[label_col])[:12], (r[x], r[y]), fontsize=6, alpha=0.7)
    ax.set_xlabel(LABELS.get(x, x))
    ax.set_ylabel(LABELS.get(y, y))
    rho = d[[x, y]].corr().iloc[0, 1]
    ax.set_title(f"{title}\n(correlación de Pearson = {rho:.2f}; ajuste lineal MCO con IC 95 %)", fontsize=11)
    return _finish(fig, path, source, period or (_period(df) if "anio" in df else ""), demo)


def plot_correlation_heatmap(corr: pd.DataFrame, path: Path, period: str, demo=False) -> Path:
    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr.rename(index=LABELS, columns=LABELS), mask=mask, annot=True, fmt=".2f",
                cmap="RdBu_r", vmin=-1, vmax=1, ax=ax, annot_kws={"size": 7}, cbar_kws={"label": "Correlación de Pearson"})
    ax.set_title("Matriz de correlaciones (panel provincia-año)")
    return _finish(fig, path, f"{SRC_PRICE}; {SRC_MIG}", period, demo)


def plot_coefficients(coefs: pd.DataFrame, path: Path, title: str, xlabel: str, period: str, demo=False) -> Path:
    """coefs: DataFrame con columnas modelo, coef, ci_low, ci_high."""
    d = coefs.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9, 0.55 * len(d) + 1.5))
    ax.errorbar(d["coef"], range(len(d)), xerr=[d["coef"] - d["ci_low"], d["ci_high"] - d["coef"]],
                fmt="o", color=PALETTE[0], ecolor=PALETTE[0], capsize=3)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels(d["modelo"])
    ax.set_xlabel(xlabel)
    ax.set_title(title + "\n(punto = estimación; barra = IC 95 %)", fontsize=11)
    return _finish(fig, path, f"{SRC_PRICE}; {SRC_MIG}", period, demo)


def plot_map(values: pd.DataFrame, value_col: str, path: Path, title: str, unit: str,
             period: str, source: str, demo=False) -> Path | None:
    """Mapa coroplético provincial. Requiere geopandas y el GeoJSON de provincias.
    Devuelve None (sin error) si geopandas no está instalado o no hay acceso al GeoJSON."""
    try:
        import geopandas as gpd
    except ImportError:
        return None
    try:
        gdf = gpd.read_file(GEOJSON_URL)
    except Exception:
        return None
    code_col = next((c for c in gdf.columns if c.lower() in ("cod_prov", "codigo", "cod", "id_prov")), None)
    if code_col is None:
        return None
    gdf["provincia_cod"] = gdf[code_col].astype(str).str.zfill(2)
    # Desplaza Canarias junto a la península (recurso cartográfico habitual)
    canarias = gdf["provincia_cod"].isin(["35", "38"])
    gdf.loc[canarias, "geometry"] = gdf.loc[canarias, "geometry"].translate(xoff=6.5, yoff=7.5)
    g = gdf.merge(values[["provincia_cod", value_col]], on="provincia_cod", how="left")
    fig, ax = plt.subplots(figsize=(10, 8))
    g.plot(column=value_col, cmap="viridis", legend=True, ax=ax, edgecolor="white", linewidth=0.3,
           missing_kwds={"color": "lightgrey"}, legend_kwds={"label": unit, "shrink": 0.6})
    ax.set_axis_off()
    ax.set_title(title)
    return _finish(fig, path, source, period, demo)
