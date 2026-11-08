"""
Orquestación del análisis por etapas. Cada función corresponde a un notebook y guarda sus
tablas y figuras en results/ (o results/_demo/ en modo demo).

    stage_descriptive(panel)      -> notebooks/02
    stage_ols(panel)              -> notebooks/03
    stage_panel(panel)            -> notebooks/04
    stage_iv_robustness(panel)    -> notebooks/05
    write_report(...)             -> results/reports/resumen_resultados.md

El informe se redacta exclusivamente a partir de los objetos estimados: no contiene cifras
escritas a mano.
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from . import config
from . import descriptive_analysis as da
from . import econometric_models as em
from . import visualizations as viz

log = logging.getLogger(__name__)

Y_DIFF = "dln_precio"
Y_LEVEL = "ln_precio"
X_FLOW = "flujo_nacidos_ext"
X_FLOW_ALT = "flujo_extranjeros"
X_SHARE = "pct_nacidos_ext"
X_SHARE_ALT = "pct_extranjeros"


def _period(df) -> str:
    return f"{int(df['anio'].min())}-{int(df['anio'].max())}"


# --------------------------------------------------------------------------------------
def stage_descriptive(panel: pd.DataFrame, demo: bool | None = None) -> dict:
    demo = config.is_demo() if demo is None else demo
    out = config.out_dirs(demo)
    period = _period(panel)
    res = {}

    stats = da.summary_statistics(panel)
    stats.to_csv(out["tables"] / "estadisticos_descriptivos.csv")
    (out["tables"] / "estadisticos_descriptivos.md").write_text(stats.to_markdown(), encoding="utf-8")
    res["summary"] = stats

    nat = da.national_series(panel)
    nat.to_csv(out["tables"] / "serie_nacional.csv", index=False)
    viz.plot_national_evolution(nat.dropna(subset=["precio_m2_pond"]), out["figures"] / "01_evolucion_nacional.png", demo)
    res["national"] = nat

    cc = da.ccaa_series(panel)
    cc.to_csv(out["tables"] / "series_ccaa.csv", index=False)
    viz.plot_ccaa_small_multiples(cc, "precio_m2_pond", out["figures"] / "02_precio_ccaa.png", demo)
    viz.plot_ccaa_small_multiples(cc, "pct_nacidos_ext", out["figures"] / "03_nacidos_ext_ccaa.png", demo)

    corr = da.correlation_matrix(panel)
    corr.to_csv(out["tables"] / "matriz_correlaciones.csv")
    viz.plot_correlation_heatmap(corr, out["figures"] / "04_correlaciones.png", period, demo)
    res["corr"] = corr

    viz.plot_scatter(panel, X_FLOW, Y_DIFF, out["figures"] / "05_dispersion_flujo_precio.png",
                     "Flujo de población nacida en el extranjero y crecimiento del precio", demo, period=period)

    # Diferencias largas entre el primer y último año con datos completos
    d = panel.dropna(subset=["ln_precio", "pct_nacidos_ext"])
    y0, y1 = int(d["anio"].min()), int(d["anio"].max())
    ld = da.long_differences(panel, y0, y1)
    ld.to_csv(out["tables"] / f"diferencias_largas_{y0}_{y1}.csv", index=False)
    if len(ld) and "flujo_acum_pct_pob_ini" in ld:
        viz.plot_scatter(ld, "flujo_acum_pct_pob_ini", "var_precio_pct",
                         out["figures"] / "06_diferencias_largas.png",
                         f"Diferencias largas {y0}-{y1} por provincia", demo, label_col="provincia",
                         period=f"{y0}-{y1}")
        viz.plot_map(ld, "var_pct_nacidos_ext_pp", out["figures"] / "07_mapa_var_nacidos_ext.png",
                     f"Variación del % de población nacida en el extranjero, {y0}-{y1}",
                     "puntos porcentuales", f"{y0}-{y1}", viz.SRC_MIG, demo)
        viz.plot_map(ld, "var_precio_pct", out["figures"] / "08_mapa_var_precio.png",
                     f"Variación del precio de la vivienda, {y0}-{y1}", "% (nominal)", f"{y0}-{y1}",
                     viz.SRC_PRICE, demo)
    res["long_diff"] = ld
    return res


# --------------------------------------------------------------------------------------
def stage_ols(panel: pd.DataFrame, demo: bool | None = None) -> dict:
    demo = config.is_demo() if demo is None else demo
    out = config.out_dirs(demo)
    models = [em.fit_pooled_ols(panel, Y_DIFF, [X_FLOW], name="MCO simple")]
    # Solo se añaden columnas con controles si los controles existen (evita columnas idénticas)
    if em.available(panel, em.CONTROLS_DIFF):
        models.append(em.fit_pooled_ols(panel, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name="MCO + controles"))
    if em.available(panel, em.CONTROLS_DIFF + em.NATIONAL_CONTROLS) != em.available(panel, em.CONTROLS_DIFF):
        models.append(em.fit_pooled_ols(panel, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF + em.NATIONAL_CONTROLS,
                                        name="MCO + controles + tipo interés"))
    models.append(em.fit_pooled_ols(panel, Y_LEVEL, [X_SHARE], em.CONTROLS_LEVEL, name="MCO niveles"))
    table = em.regression_table(models)
    em.save_table(table, out["tables"] / "tabla_1_mco", em.SIGNIF_NOTE)
    return {"models": models, "table": table}


# --------------------------------------------------------------------------------------
def stage_panel(panel: pd.DataFrame, demo: bool | None = None) -> dict:
    demo = config.is_demo() if demo is None else demo
    out = config.out_dirs(demo)
    m_main = em.fit_panel_fe(panel, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name="EF provincia + año (principal)")
    models = [
        em.fit_panel_fe(panel, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, entity=True, time=False, name="EF provincia"),
        m_main,
        em.fit_panel_fe(panel, Y_DIFF, [f"{X_FLOW}_l1"], em.CONTROLS_DIFF, name="Flujo retardado (t-1)"),
        em.fit_panel_fe(panel, Y_DIFF, ["d_pct_nacidos_ext"], em.CONTROLS_DIFF,
                        name="Δ proporción nacidos ext. (p.p.)"),
        em.fit_panel_fe(panel, Y_LEVEL, [X_SHARE], em.CONTROLS_LEVEL, name="Niveles EF provincia + año"),
    ]
    dl, cum = em.distributed_lag(panel, Y_DIFF, X_FLOW, lags=2, controls=em.CONTROLS_DIFF)
    models.append(dl)
    table = em.regression_table(models)
    em.save_table(table, out["tables"] / "tabla_2_panel", em.SIGNIF_NOTE)

    wald = em.joint_wald_test(m_main, em.CONTROLS_DIFF)
    wald_lags = em.joint_wald_test(dl, [X_FLOW, f"{X_FLOW}_l1", f"{X_FLOW}_l2"])
    diag = {"wald_controles": wald, "wald_retardos_flujo": wald_lags, "efecto_acumulado_0_2": cum}
    (out["tables"] / "contrastes_panel.json").write_text(json.dumps(diag, indent=2, default=float), encoding="utf-8")
    return {"models": models, "main": m_main, "dl": dl, "table": table, "diagnostics": diag}


# --------------------------------------------------------------------------------------
def stage_iv_robustness(panel: pd.DataFrame, nat: pd.DataFrame | None, demo: bool | None = None,
                        base_year: int | None = None) -> dict:
    demo = config.is_demo() if demo is None else demo
    out = config.out_dirs(demo)
    res: dict = {}
    period = _period(panel)

    # ---------- IV shift-share
    if nat is not None and len(nat):
        base_year = base_year or int(nat["anio"].min())
        z = em.build_shift_share(nat, panel, base_year)
        p = panel.merge(z, on=["provincia_cod", "anio"], how="left")
        p = p[p["anio"] > base_year]
        iv_ext = em.fit_iv_fe(p, Y_DIFF, X_FLOW_ALT, "iv_shift_share", em.CONTROLS_DIFF,
                              name="2SLS (flujo extranjeros)")
        iv_fb = em.fit_iv_fe(p, Y_DIFF, X_FLOW, "iv_shift_share", em.CONTROLS_DIFF,
                             name="2SLS (flujo nacidos ext.)")
        ols_same = em.fit_panel_fe(p, Y_DIFF, [X_FLOW_ALT], em.CONTROLS_DIFF, name="EF misma muestra")
        rf = em.fit_reduced_form(p, Y_DIFF, "iv_shift_share", em.CONTROLS_DIFF)
        tbl = em.regression_table([ols_same, iv_ext, iv_fb, rf])
        em.save_table(tbl, out["tables"] / "tabla_3_iv", em.SIGNIF_NOTE +
                      f" Instrumento: shift-share con cuotas por nacionalidad en {base_year} (leave-one-out).")
        res.update({"iv": [iv_ext, iv_fb], "ols_same": ols_same, "reduced_form": rf, "iv_table": tbl,
                    "base_year": base_year})
    else:
        log.warning("Sin datos por nacionalidad: se omite la estimación IV")

    # ---------- Robustez
    rob = []
    base = em.fit_panel_fe(panel, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name="Principal")
    rob.append(base.coef(X_FLOW))
    r = em.fit_panel_fe(panel, Y_DIFF, [X_FLOW_ALT], em.CONTROLS_DIFF, name="Def. alternativa: extranjeros")
    rob.append({**r.coef(X_FLOW_ALT), "modelo": r.name})
    if em.available(panel, em.CONTROLS_DIFF):
        r = em.fit_panel_fe(panel, Y_DIFF, [X_FLOW], [], name="Sin controles")
        rob.append(r.coef(X_FLOW))
    if "d_pct_nacidos_ext" in panel:
        r = em.fit_panel_fe(panel, Y_DIFF, ["d_pct_nacidos_ext"], em.CONTROLS_DIFF,
                            name="Regresor: Δ proporción nacidos ext. (p.p.)")
        rob.append({**r.coef("d_pct_nacidos_ext"), "modelo": r.name})
    if "dln_precio_t4" in panel and panel["dln_precio_t4"].notna().any():
        r = em.fit_panel_fe(panel, "dln_precio_t4", [X_FLOW], em.CONTROLS_DIFF,
                            name="Precio 4.º trimestre (alineado con Padrón)")
        rob.append(r.coef(X_FLOW))
    sub = panel[~panel["provincia_cod"].isin(config.ATYPICAL_PROVINCES)]
    r = em.fit_panel_fe(sub, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name="Sin provincias atípicas")
    rob.append(r.coef(X_FLOW))
    lo, hi = panel[X_FLOW].quantile([0.01, 0.99])
    trimmed = panel[(panel[X_FLOW].between(lo, hi)) | panel[X_FLOW].isna()]
    r = em.fit_panel_fe(trimmed, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name="Sin outliers (p1-p99)")
    rob.append(r.coef(X_FLOW))
    for label, (a, b) in config.SUBPERIODS.items():
        s = panel[panel["anio"].between(a, b)]
        if s["anio"].nunique() >= 3 and s[[Y_DIFF, X_FLOW]].dropna().shape[0] > 50:
            r = em.fit_panel_fe(s, Y_DIFF, [X_FLOW], em.CONTROLS_DIFF, name=f"Subperiodo: {label}")
            rob.append(r.coef(X_FLOW))
    r = em.fit_panel_fe(panel, Y_LEVEL, [X_SHARE], em.CONTROLS_LEVEL, name="Niveles: ln precio ~ % nacidos ext.")
    rob.append({**r.coef(X_SHARE), "modelo": r.name})
    if "iv" in res:
        rob.append({**res["iv"][1].coef(X_FLOW), "modelo": "2SLS shift-share (nacidos ext.)"})
    rob_df = pd.DataFrame(rob)
    rob_df.to_csv(out["tables"] / "tabla_4_robustez.csv", index=False)
    (out["tables"] / "tabla_4_robustez.md").write_text(rob_df.round(4).to_markdown(index=False), encoding="utf-8")
    flow_like = rob_df[~rob_df["modelo"].str.startswith("Niveles")]
    viz.plot_coefficients(flow_like, out["figures"] / "09_coeficientes_especificaciones.png",
                          "Efecto estimado de un flujo de inmigración = 1 % de la población\n"
                          "sobre el crecimiento anual del precio de la vivienda",
                          "Puntos porcentuales de Δ ln precio (×100)", period, demo)
    res["robustness"] = rob_df

    loo = em.leave_one_province_out(panel, Y_DIFF, X_FLOW, em.CONTROLS_DIFF)
    loo.to_csv(out["tables"] / "leave_one_province_out.csv", index=False)
    res["loo"] = loo

    # ---------- Diagnósticos
    vif = em.vif_table(panel, [X_FLOW] + em.CONTROLS_DIFF)
    vif.to_csv(out["tables"] / "vif.csv", index=False)
    wool = em.wooldridge_serial_correlation(panel, Y_LEVEL, [X_SHARE] + em.available(panel, em.CONTROLS_LEVEL))
    (out["tables"] / "wooldridge_autocorrelacion.json").write_text(json.dumps(wool, indent=2), encoding="utf-8")
    res.update({"vif": vif, "wooldridge": wool})
    return res


# --------------------------------------------------------------------------------------
def _fmt_ci(c: dict) -> str:
    return f"{c['coef']:.3f} (IC 95 %: {c['ci_low']:.3f} a {c['ci_high']:.3f}; p = {c['p']:.3f})"


def write_report(panel, desc, ols, pan, ivr, demo: bool | None = None) -> str:
    """Redacta un resumen de resultados a partir de las estimaciones. Sin cifras manuales."""
    demo = config.is_demo() if demo is None else demo
    out = config.out_dirs(demo)
    main = pan["main"].coef(X_FLOW)
    used = [v for v in pan["main"].params.index if v != X_FLOW]
    pooled = ols["models"][0].coef(X_FLOW)
    lines = []
    if demo:
        lines += ["> **AVISO: INFORME GENERADO CON DATOS SINTÉTICOS (modo demo). "
                  "Ninguna cifra de este documento es un resultado real.**", ""]
    lines += [
        "# Resumen de resultados (generado automáticamente)", "",
        f"Muestra: {panel['provincia_cod'].nunique()} provincias, años {_period(panel)}. "
        f"Observaciones en el modelo principal: {main['nobs']}.",
        f"Controles incluidos: {', '.join(used) if used else 'NINGUNO (solo efectos fijos de provincia y año; los controles económicos de Eurostat no estaban disponibles en esta ejecución)'}.", "",
        "## Modelo principal (efectos fijos de provincia y año, errores agrupados por provincia)", "",
        f"- Coeficiente del flujo de población nacida en el extranjero: {_fmt_ci(main)}.",
        "- Interpretación: un aumento neto de residentes nacidos en el extranjero equivalente al 1 % de la "
        f"población de la provincia se asocia con una variación de {main['coef']:.2f} puntos porcentuales "
        "en el crecimiento anual del precio de la vivienda, condicionada a los efectos fijos de provincia y año (y a los controles, si los hay).",
    ]
    lines.append(f"- MCO agrupado sin efectos fijos: {pooled['coef']:.3f}. La diferencia con el modelo principal "
                 "indica qué parte de la correlación bruta se debe a diferencias permanentes entre provincias "
                 "y al ciclo nacional común.")
    dsh = [m for m in pan["models"] if m.name.startswith("Δ proporción")]
    if dsh:
        c = dsh[0].coef("d_pct_nacidos_ext")
        lines.append(f"- Con la variación de la **proporción** de nacidos en el extranjero (p.p.) como regresor, que no "
                     f"depende del tamaño de la población: {_fmt_ci(c)}.")
    cum = pan["diagnostics"]["efecto_acumulado_0_2"]
    lines.append(f"- Efecto acumulado (retardos 0-2): {cum['efecto_acumulado']:.3f} "
                 f"(IC 95 %: {cum['ci_low']:.3f} a {cum['ci_high']:.3f}; p = {cum['p']:.3f}).")
    contemp = pan["dl"].coef(X_FLOW)["coef"]
    lines.append("- H2 (efecto acumulado mayor que el contemporáneo): "
                 + ("compatible con los datos." if cum["efecto_acumulado"] > contemp else
                    f"**no se sostiene**: el efecto acumulado ({cum['efecto_acumulado']:.3f}) es menor que el "
                    f"contemporáneo en el mismo modelo ({contemp:.3f}); los retardos tienen signo negativo, lo que "
                    "sugiere una reversión parcial y no una acumulación."))
    lvl = [m for m in pan["models"] if m.name.startswith("Niveles")][0].coef(X_SHARE)
    lines.append(f"- Especificación en niveles: +1 p.p. en el peso de la población nacida en el extranjero se asocia "
                 f"con un {100 * lvl['coef']:.2f} % de variación del precio (IC 95 %: {100 * lvl['ci_low']:.2f} % "
                 f"a {100 * lvl['ci_high']:.2f} %).")
    if "iv" in ivr:
        iv = ivr["iv"][1]
        c = iv.coef(X_FLOW)
        F = iv.extra["first_stage_F"]
        lines += ["", "## Variables instrumentales (shift-share)", "",
                  f"- 2SLS: {_fmt_ci(c)}. Estadístico de primera etapa (Wald robusto a cluster, "
                  f"equivalente a F con un instrumento) = {F:.2f}.",
                  "- " + ("El instrumento es débil (F < 10): la estimación IV no es fiable." if F < 10 else
                          "El instrumento no parece débil según la regla F > 10, pero su validez depende de la "
                          "exogeneidad de las cuotas iniciales (ver docs/methodology.md).")]
    if "iv" in ivr:
        lines.append(f"- Comparación: efectos fijos en la misma muestra con el flujo de extranjeros = "
                     f"{ivr['ols_same'].coef(X_FLOW_ALT)['coef']:.3f}; 2SLS con el flujo de extranjeros = "
                     f"{ivr['iv'][0].coef(X_FLOW_ALT)['coef']:.3f}. Forma reducida: "
                     f"{_fmt_ci(ivr['reduced_form'].coef('iv_shift_share'))}.")
    rob = ivr["robustness"]
    sig = (rob["p"] < 0.05).sum()
    lines += ["", "## Robustez", "",
              f"- {sig} de {len(rob)} especificaciones presentan p < 0.05. Rango de coeficientes de flujo: "
              f"{rob[~rob['modelo'].str.startswith('Niveles')]['coef'].min():.3f} a "
              f"{rob[~rob['modelo'].str.startswith('Niveles')]['coef'].max():.3f}.",
              "- Por especificación: " + "; ".join(f"{r.modelo}: {r.coef:.3f} (p = {r.p:.3f})" for r in rob.itertuples()) + ".",
              f"- Excluyendo provincias de una en una, el coeficiente varía entre {ivr['loo']['coef'].min():.3f} "
              f"y {ivr['loo']['coef'].max():.3f}.",
              f"- Test de Wooldridge de autocorrelación: p = {ivr['wooldridge']['pvalue']:.3f}.",
              f"- VIF máximo: {ivr['vif']['VIF'].max():.2f}.", "",
              "## Advertencia sobre causalidad", "",
              "Los coeficientes de MCO y efectos fijos son asociaciones condicionales. Solo la estimación IV "
              "aspira a una interpretación causal, y únicamente si se cumplen sus supuestos de identificación, "
              "que no pueden contrastarse de forma directa."]
    text = "\n".join(lines) + "\n"
    (out["reports"] / "resumen_resultados.md").write_text(text, encoding="utf-8")
    return text
