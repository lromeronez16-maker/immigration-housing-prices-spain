"""
Modelos econométricos: MCO, panel con efectos fijos, variables instrumentales (shift-share)
y pruebas de robustez/diagnóstico.

Convenciones:
- Variable dependiente principal en diferencias: dln_precio = 100·Δln(precio €/m²)  (≈ % anual).
- Variable migratoria principal en flujos: flujo_nacidos_ext = 100·ΔFB_t / Pob_{t-1}
  (aumento neto de residentes nacidos en el extranjero en % de la población inicial).
  Con esta normalización, β mide los puntos porcentuales de crecimiento del precio asociados
  a un flujo equivalente al 1 % de la población (especificación tipo Saiz, 2007;
  González y Ortega, 2013).
- Especificación en niveles: ln_precio sobre pct_nacidos_ext; 100·β = % de variación del
  precio asociado a +1 p.p. de peso de la población nacida en el extranjero.
- Errores estándar agrupados (cluster) por provincia en todas las especificaciones de panel.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.iv import IV2SLS
from linearmodels.panel import PanelOLS
from scipy import stats
from statsmodels.stats.outliers_influence import variance_inflation_factor

from . import config

log = logging.getLogger(__name__)

# Conjuntos de controles (se usan solo los disponibles en el panel)
CONTROLS_DIFF = ["g_pib_pc", "d_tasa_paro", "d_pct_joven", "viv_term_1000hab_l1"]
CONTROLS_LEVEL = ["ln_pib_pc", "tasa_paro_ccaa", "ln_densidad", "pct_joven_25_34"]
# Variables nacionales (sin variación provincial): solo en MCO agrupado sin efectos temporales
NATIONAL_CONTROLS = ["tipo_interes_lp"]


# --------------------------------------------------------------------------------------
# Contenedor homogéneo de resultados
# --------------------------------------------------------------------------------------
@dataclass
class ModelResult:
    name: str
    dep_var: str
    params: pd.Series
    std_errors: pd.Series
    pvalues: pd.Series
    conf_int: pd.DataFrame
    nobs: int
    r2: float | None
    n_entities: int | None = None
    fixed_effects: str = "ninguno"
    se_type: str = ""
    extra: dict = field(default_factory=dict)
    raw: object | None = None

    def coef(self, var: str) -> dict:
        return {
            "modelo": self.name, "variable": var, "coef": self.params.get(var, np.nan),
            "se": self.std_errors.get(var, np.nan), "p": self.pvalues.get(var, np.nan),
            "ci_low": self.conf_int.loc[var].iloc[0] if var in self.conf_int.index else np.nan,
            "ci_high": self.conf_int.loc[var].iloc[1] if var in self.conf_int.index else np.nan,
            "nobs": self.nobs,
        }


def _from_statsmodels(res, name, dep, fe, se_type, n_ent=None) -> ModelResult:
    ci = res.conf_int()
    ci.columns = ["lower", "upper"]
    return ModelResult(name, dep, res.params, res.bse, res.pvalues, ci, int(res.nobs),
                       float(res.rsquared), n_ent, fe, se_type, raw=res)


def _from_linearmodels(res, name, dep, fe, se_type, n_ent=None, r2=None) -> ModelResult:
    ci = res.conf_int()
    ci.columns = ["lower", "upper"]
    return ModelResult(name, dep, res.params, res.std_errors, res.pvalues, ci, int(res.nobs),
                       float(r2 if r2 is not None else res.rsquared), n_ent, fe, se_type, raw=res)


# --------------------------------------------------------------------------------------
# Preparación
# --------------------------------------------------------------------------------------
def available(df: pd.DataFrame, cols: list[str]) -> list[str]:
    """Devuelve solo las columnas presentes con datos; avisa de las que faltan."""
    ok = [c for c in cols if c in df.columns and df[c].notna().any()]
    missing = sorted(set(cols) - set(ok))
    if missing:
        log.info("Controles no disponibles y omitidos: %s", missing)
    return ok


def model_sample(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Muestra de estimación: filas completas en las columnas usadas, sin infinitos."""
    d = df[["provincia_cod", "anio"] + [c for c in cols if c not in ("provincia_cod", "anio")]].copy()
    d = d.replace([np.inf, -np.inf], np.nan).dropna()
    return d


# --------------------------------------------------------------------------------------
# MCO agrupado
# --------------------------------------------------------------------------------------
def fit_pooled_ols(df, y, x, controls=None, name="MCO agrupado", cluster=True) -> ModelResult:
    controls = available(df, controls or [])
    d = model_sample(df, [y] + x + controls)
    X = sm.add_constant(d[x + controls])
    if cluster:
        groups = d["provincia_cod"].astype("category").cat.codes
        res = sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": groups})
        se = "cluster provincia"
    else:
        res = sm.OLS(d[y], X).fit(cov_type="HC1")
        se = "HC1"
    return _from_statsmodels(res, name, y, "ninguno", se, d["provincia_cod"].nunique())


# --------------------------------------------------------------------------------------
# Panel con efectos fijos
# --------------------------------------------------------------------------------------
def fit_panel_fe(df, y, x, controls=None, entity=True, time=True, name=None) -> ModelResult:
    """PanelOLS con efectos fijos de provincia y/o año y errores agrupados por provincia."""
    controls = available(df, controls or [])
    d = model_sample(df, [y] + x + controls).set_index(["provincia_cod", "anio"])
    exog = d[x + controls]
    mod = PanelOLS(d[y], exog, entity_effects=entity, time_effects=time, drop_absorbed=True, check_rank=False)
    res = mod.fit(cov_type="clustered", cluster_entity=True)
    fe = " + ".join([s for s, f in (("provincia", entity), ("año", time)) if f]) or "ninguno"
    name = name or f"EF {fe}"
    out = _from_linearmodels(res, name, y, fe, "cluster provincia", d.index.get_level_values(0).nunique(),
                             r2=res.rsquared_within)
    out.extra["r2_within"] = float(res.rsquared_within)
    return out


def joint_wald_test(result: ModelResult, variables: list[str]) -> dict:
    """Contraste de Wald de significatividad conjunta H0: β_j = 0 para todas las variables."""
    vars_ = [v for v in variables if v in result.params.index]
    if not vars_:
        return {"variables": [], "stat": np.nan, "df": 0, "pvalue": np.nan}
    raw = result.raw
    names = list(result.params.index)
    R = np.zeros((len(vars_), len(names)))
    for i, v in enumerate(vars_):
        R[i, names.index(v)] = 1
    if hasattr(raw, "wald_test") and hasattr(raw, "std_errors"):  # linearmodels
        w = raw.wald_test(restriction=R, value=np.zeros(len(vars_)))
        return {"variables": vars_, "stat": float(w.stat), "df": len(vars_), "pvalue": float(w.pval)}
    w = raw.wald_test(R, scalar=True)  # statsmodels
    return {"variables": vars_, "stat": float(w.statistic), "df": len(vars_), "pvalue": float(w.pvalue)}


def distributed_lag(df, y, base: str, lags: int = 2, controls=None) -> tuple[ModelResult, dict]:
    """Modelo de retardos distribuidos con EF; devuelve además el efecto acumulado (suma de β)
    con su error estándar (vía matriz de covarianzas)."""
    xs = [base] + [f"{base}_l{k}" for k in range(1, lags + 1)]
    res = fit_panel_fe(df, y, xs, controls, name=f"Retardos distribuidos (0-{lags})")
    cov = res.raw.cov.loc[xs, xs].to_numpy()
    total = float(res.params[xs].sum())
    se = float(np.sqrt(np.ones(len(xs)) @ cov @ np.ones(len(xs))))
    p = 2 * (1 - stats.norm.cdf(abs(total / se)))
    cum = {"efecto_acumulado": total, "se": se, "p": p, "ci_low": total - 1.96 * se, "ci_high": total + 1.96 * se}
    res.extra["acumulado"] = cum
    return res, cum


# --------------------------------------------------------------------------------------
# Instrumento shift-share (Bartik / Card)
# --------------------------------------------------------------------------------------
def build_shift_share(nat: pd.DataFrame, panel: pd.DataFrame, base_year: int,
                      leave_one_out: bool = True) -> pd.DataFrame:
    """Flujo migratorio predicho para cada provincia y año.

    Z_pt = 100 · Σ_n s_{n,p,t0} · ΔN_{n,t}^{(-p)} / Pob_{p,t-1}

    - s_{n,p,t0}: fracción de los residentes de nacionalidad n en España que vivían en la
      provincia p en el año base t0 (red de compatriotas, "enclave").
    - ΔN_{n,t}^{(-p)}: variación nacional del stock de nacionalidad n entre t-1 y t, excluyendo
      la propia provincia p (leave-one-out) para reducir la endogeneidad mecánica.
    - Solo se usa para t > t0.
    """
    need = {"provincia_cod", "anio", "nacionalidad", "poblacion"}
    if not need.issubset(nat.columns):
        raise ValueError(f"nat debe contener {need}")
    nat = nat.copy()
    base = nat[nat["anio"] == base_year]
    if base.empty:
        raise ValueError(f"No hay datos de nacionalidad en el año base {base_year}")
    tot_base = base.groupby("nacionalidad")["poblacion"].transform("sum")
    shares = base.assign(share=base["poblacion"] / tot_base)[["provincia_cod", "nacionalidad", "share"]]

    nat = nat.sort_values(["nacionalidad", "provincia_cod", "anio"])
    nat["d_prov"] = nat.groupby(["nacionalidad", "provincia_cod"])["poblacion"].diff()
    prev_year = nat.groupby(["nacionalidad", "provincia_cod"])["anio"].shift()
    nat.loc[nat["anio"] - prev_year != 1, "d_prov"] = np.nan
    nat["d_nat"] = nat.groupby(["nacionalidad", "anio"])["d_prov"].transform(lambda s: s.sum(min_count=1))
    nat["shift"] = nat["d_nat"] - nat["d_prov"] if leave_one_out else nat["d_nat"]

    m = nat.merge(shares, on=["provincia_cod", "nacionalidad"], how="left")
    m = m[m["anio"] > base_year]
    m["contrib"] = m["share"].fillna(0) * m["shift"]
    z = m.groupby(["provincia_cod", "anio"], as_index=False)["contrib"].sum(min_count=1)

    pop = panel[["provincia_cod", "anio", "poblacion"]].copy()
    pop["anio"] = pop["anio"] + 1
    z = z.merge(pop.rename(columns={"poblacion": "pob_l1"}), on=["provincia_cod", "anio"], how="left")
    z["iv_shift_share"] = 100 * z["contrib"] / z["pob_l1"]
    return z[["provincia_cod", "anio", "iv_shift_share"]]


def fit_iv_fe(df, y, endog, instrument, controls=None, name="2SLS shift-share") -> ModelResult:
    """2SLS con efectos fijos de provincia y año (dummies) y errores agrupados por provincia.

    Devuelve diagnósticos de primera etapa (F parcial del instrumento excluido).
    """
    controls = available(df, controls or [])
    d = model_sample(df, [y, endog, instrument] + controls)
    fe = pd.get_dummies(d[["provincia_cod", "anio"]].astype(str), drop_first=True, dtype=float)
    exog = pd.concat([pd.Series(1.0, index=d.index, name="const"), d[controls], fe], axis=1)
    res = IV2SLS(d[y], exog, d[[endog]], d[[instrument]]).fit(cov_type="clustered", clusters=d["provincia_cod"])
    fs = res.first_stage.diagnostics
    out = _from_linearmodels(res, name, y, "provincia + año", "cluster provincia", d["provincia_cod"].nunique())
    out.extra["first_stage_F"] = float(fs["f.stat"].iloc[0])
    out.extra["first_stage_partial_r2"] = float(fs["partial.rsquared"].iloc[0])
    # Coeficiente de la primera etapa
    fs_res = res.first_stage.individual[endog]
    out.extra["first_stage_coef"] = float(fs_res.params[instrument])
    out.extra["first_stage_se"] = float(fs_res.std_errors[instrument])
    out.params = out.params[[endog] + controls]
    return out


def fit_reduced_form(df, y, instrument, controls=None) -> ModelResult:
    """Forma reducida: efecto directo del instrumento sobre el precio (EF provincia + año)."""
    return fit_panel_fe(df, y, [instrument], controls, name="Forma reducida")


# --------------------------------------------------------------------------------------
# Diagnósticos
# --------------------------------------------------------------------------------------
def vif_table(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Factores de inflación de la varianza (multicolinealidad)."""
    cols = available(df, cols)
    d = model_sample(df, cols)[cols]
    X = sm.add_constant(d)
    return pd.DataFrame({
        "variable": cols,
        "VIF": [variance_inflation_factor(X.values, i + 1) for i in range(len(cols))],
    })


def wooldridge_serial_correlation(df: pd.DataFrame, y: str, x: list[str]) -> dict:
    """Test de Wooldridge (2002) de autocorrelación de primer orden en paneles.

    Se estima el modelo en primeras diferencias, se regresan los residuos sobre su retardo y
    se contrasta H0: ρ = -0.5 (ausencia de autocorrelación en los errores en niveles).
    """
    d = model_sample(df, [y] + x).sort_values(["provincia_cod", "anio"])
    g = d.groupby("provincia_cod")
    dd = pd.DataFrame({c: g[c].diff() for c in [y] + x})
    dd["provincia_cod"] = d["provincia_cod"]
    dd["anio"] = d["anio"]
    dd.loc[g["anio"].diff() != 1, [y] + x] = np.nan
    dd = dd.dropna()
    res = sm.OLS(dd[y], dd[x]).fit()
    dd["e"] = res.resid
    dd["e_l1"] = dd.groupby("provincia_cod")["e"].shift()
    s = dd.dropna(subset=["e_l1"])
    r = sm.OLS(s["e"], s[["e_l1"]]).fit(cov_type="cluster",
                                         cov_kwds={"groups": s["provincia_cod"].astype("category").cat.codes})
    rho, se = float(r.params["e_l1"]), float(r.bse["e_l1"])
    f = ((rho + 0.5) / se) ** 2
    return {"rho": rho, "F": f, "pvalue": float(1 - stats.chi2.cdf(f, 1)), "nobs": int(r.nobs)}


def leave_one_province_out(df, y, x_main, controls=None) -> pd.DataFrame:
    """Re-estima el modelo principal excluyendo cada provincia de una en una."""
    rows = []
    for cod in sorted(df["provincia_cod"].unique()):
        r = fit_panel_fe(df[df["provincia_cod"] != cod], y, [x_main], controls)
        rows.append({"excluida": cod, "provincia": config.PROVINCE_NAME.get(cod, cod), **r.coef(x_main)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------
# Tablas de regresión
# --------------------------------------------------------------------------------------
def _stars(p: float) -> str:
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def regression_table(results: list[ModelResult], variables: list[str] | None = None) -> pd.DataFrame:
    """Tabla comparativa con coeficientes, (errores estándar) y estadísticos por columna."""
    variables = variables or list(dict.fromkeys(v for r in results for v in r.params.index if v != "const"))
    cols = {}
    for i, r in enumerate(results, start=1):
        col = []
        for v in variables:
            if v in r.params.index:
                col += [f"{r.params[v]:.4f}{_stars(r.pvalues[v])}", f"({r.std_errors[v]:.4f})"]
            else:
                col += ["", ""]
        col += [r.dep_var, r.fixed_effects, r.se_type, f"{r.nobs}",
                f"{r.n_entities or ''}", f"{r.r2:.3f}" if r.r2 is not None else ""]
        fs = r.extra.get("first_stage_F")
        col.append(f"{fs:.2f}" if fs is not None else "")
        cols[f"({i}) {r.name}"] = col
    index = [x for v in variables for x in (v, f"{v} (ee)")] + [
        "Variable dependiente", "Efectos fijos", "Errores estándar", "Observaciones",
        "Provincias", "R² (within si EF)", "F primera etapa"]
    return pd.DataFrame(cols, index=index)


def save_table(table: pd.DataFrame, path_stem, note: str = "") -> None:
    """Guarda la tabla en CSV, Markdown y LaTeX."""
    from pathlib import Path
    stem = Path(path_stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(stem.with_suffix(".csv"))
    md = table.to_markdown()
    if note:
        md += f"\n\n{note}\n"
    stem.with_suffix(".md").write_text(md, encoding="utf-8")
    stem.with_suffix(".tex").write_text(table.to_latex(escape=True), encoding="utf-8")


SIGNIF_NOTE = ("Errores estándar entre paréntesis. *** p<0.01, ** p<0.05, * p<0.10. "
               "Errores agrupados por provincia salvo indicación contraria.")
