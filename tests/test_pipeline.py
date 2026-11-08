"""
Tests automáticos. Usan datos SINTÉTICOS (src/synthetic.py) o ejemplos mínimos construidos a mano;
ninguno usa ni reproduce datos reales.

    pytest -q
"""
import numpy as np
import pandas as pd
import pytest

from src import config, data_cleaning as dc, econometric_models as em, synthetic


# ---------------------------------------------------------------- configuración
def test_52_provinces_unique():
    assert len(config.PROVINCE_CODES) == 52
    assert len(set(config.PROVINCE_CODES)) == 52
    assert config.PROVINCE_CODES == [f"{i:02d}" for i in range(1, 53)]


def test_nuts3_codes_unique_mapping():
    all_nuts = [n for p in config.PROVINCES for n in p[4]]
    assert len(all_nuts) == len(set(all_nuts))


# ---------------------------------------------------------------- limpieza
def test_nuts3_island_aggregation_avoids_double_counting():
    df = pd.DataFrame({
        "geo": ["ES531", "ES532", "ES533", "ES530", "ES530", "ES300"],
        "anio": [2020, 2020, 2020, 2020, 2010, 2020],
        "valor": [10, 20, 30, 999, 55, 7],
    })
    out = dc.nuts3_to_province(df).set_index(["provincia_cod", "anio"])["valor"]
    assert out[("07", 2020)] == 60      # suma de islas; el código antiguo se ignora
    assert out[("07", 2010)] == 55      # año con solo el código antiguo
    assert out[("28", 2020)] == 7


def test_derived_variables_hand_computed():
    df = pd.DataFrame({
        "provincia_cod": ["01", "01", "01"], "anio": [2000, 2001, 2003],
        "precio_m2": [1000.0, 1100.0, 1200.0],
        "nacidos_extranjero": [100.0, 150.0, 200.0],
        "extranjeros": [80.0, 120.0, 150.0],
        "poblacion_total": [1000.0, 1050.0, 1100.0],
    })
    out = dc.add_derived_variables(df).set_index("anio")
    assert out.loc[2001, "pct_nacidos_ext"] == pytest.approx(100 * 150 / 1050)
    assert out.loc[2001, "flujo_nacidos_ext"] == pytest.approx(100 * 50 / 1000)
    assert out.loc[2001, "dln_precio"] == pytest.approx(100 * np.log(1.1))
    # 2003 no tiene año anterior (falta 2002): el retardo debe ser NaN, no 2001
    assert np.isnan(out.loc[2003, "flujo_nacidos_ext"])
    assert np.isnan(out.loc[2003, "dln_precio"])


def test_validation_rejects_duplicates():
    df = pd.DataFrame({"provincia_cod": ["01", "01"], "anio": [2000, 2000]})
    with pytest.raises(dc.DataValidationError):
        dc.validate_panel(df)


def test_validation_rejects_out_of_range():
    df = pd.DataFrame({"provincia_cod": ["01"], "anio": [2000], "pct_nacidos_ext": [150.0]})
    with pytest.raises(dc.DataValidationError):
        dc.validate_panel(df)


def test_manual_loader_schema(tmp_path):
    (tmp_path / "precio_vivienda.csv").write_text("provincia_cod,anio\n1,2000\n")
    with pytest.raises(dc.DataValidationError):
        dc.load_manual("precio_vivienda.csv", tmp_path)
    (tmp_path / "precio_vivienda.csv").write_text("provincia_cod,anio,precio_m2\n1,2000,1500\n")
    out = dc.load_manual("precio_vivienda.csv", tmp_path)
    assert out["provincia_cod"].iloc[0] == "01"


def test_annualize_requires_four_quarters():
    p = pd.DataFrame({"provincia_cod": ["01"] * 7, "anio": [2000] * 4 + [2001] * 3,
                      "trimestre": [1, 2, 3, 4, 1, 2, 3], "precio_m2": [1, 2, 3, 4, 5, 6, 7]})
    out = dc.annualize_prices(p)
    assert list(out["anio"]) == [2000]
    assert out["precio_m2"].iloc[0] == 2.5


# ---------------------------------------------------------------- modelos
@pytest.fixture(scope="module")
def synth_panel():
    return dc.add_derived_variables(synthetic.make_synthetic_panel())


def test_synthetic_panel_valid(synth_panel):
    rep = dc.validate_panel(synth_panel)
    assert rep["provincias"] == 52


def test_twfe_recovers_true_beta(synth_panel):
    r = em.fit_panel_fe(synth_panel, "dln_precio", ["flujo_nacidos_ext"], em.CONTROLS_DIFF)
    c = r.coef("flujo_nacidos_ext")
    assert c["ci_low"] <= synthetic.TRUE_BETA_FLOW <= c["ci_high"]


def test_joint_wald(synth_panel):
    r = em.fit_panel_fe(synth_panel, "dln_precio", ["flujo_nacidos_ext"], ["g_pib_pc"])
    w = em.joint_wald_test(r, ["g_pib_pc"])
    assert w["pvalue"] < 0.05  # el DGP incluye un efecto real de g_pib_pc (0.3)


def test_shift_share_hand_example():
    # 2 provincias, 2 nacionalidades, años 2000 (base) y 2001
    nat = pd.DataFrame({
        "provincia_cod": ["01", "02", "01", "02"] * 2,
        "anio": [2000] * 4 + [2001] * 4,
        "nacionalidad": ["A", "A", "B", "B"] * 2,
        "poblacion": [30, 70, 50, 50, 40, 90, 50, 60],
    })
    panel = pd.DataFrame({"provincia_cod": ["01", "02"], "anio": [2000, 2000], "poblacion": [1000.0, 2000.0]})
    z = em.build_shift_share(nat, panel, 2000).set_index("provincia_cod")["iv_shift_share"]
    # Prov 01: A share .3, ΔA sin 01 = 20; B share .5, ΔB sin 01 = 10 -> (6 + 5)/1000*100 = 1.1
    assert z["01"] == pytest.approx(1.1)
    # Prov 02: A share .7, ΔA sin 02 = 10; B share .5, ΔB sin 02 = 0 -> 7/2000*100 = 0.35
    assert z["02"] == pytest.approx(0.35)


def test_iv_runs_and_reports_first_stage(synth_panel):
    nat = synthetic.make_synthetic_nationalities()
    z = em.build_shift_share(nat, synth_panel, 2002)
    p = synth_panel.merge(z, on=["provincia_cod", "anio"])
    r = em.fit_iv_fe(p, "dln_precio", "flujo_extranjeros", "iv_shift_share", ["g_pib_pc"])
    assert "first_stage_F" in r.extra and r.extra["first_stage_F"] > 0


def test_regression_table_shape(synth_panel):
    rs = [em.fit_pooled_ols(synth_panel, "dln_precio", ["flujo_nacidos_ext"]),
          em.fit_panel_fe(synth_panel, "dln_precio", ["flujo_nacidos_ext"])]
    t = em.regression_table(rs, ["flujo_nacidos_ext"])
    assert t.shape[1] == 2
    assert "Observaciones" in t.index


def test_wooldridge_and_vif(synth_panel):
    w = em.wooldridge_serial_correlation(synth_panel, "dln_precio", ["flujo_nacidos_ext", "g_pib_pc"])
    assert 0 <= w["pvalue"] <= 1
    v = em.vif_table(synth_panel, ["flujo_nacidos_ext", "g_pib_pc"])
    assert (v["VIF"] >= 1).all()


def test_zero_prices_are_missing():
    p = pd.DataFrame({"provincia_cod": ["16"] * 4, "anio": [2012] * 4,
                      "trimestre": [1, 2, 3, 4], "precio_m2": [940.9, 0.0, 0.0, 823.3]})
    assert dc.annualize_prices(p).empty  # año con trimestres no publicados (0) se descarta


def test_official_parsers_number_format():
    from src.official_sources import _num, _prov_code, _is_aggregate
    assert _num(pd.Series(["47.475.420"])).iloc[0] == 47475420
    assert np.isnan(_num(pd.Series([".."])).iloc[0])
    assert _prov_code(pd.Series(["02 Albacete", "TOTAL ESPAÑA"])).tolist()[0] == "02"
    assert _is_aggregate("UE(27_2020)") and _is_aggregate("ÁFRICA") and not _is_aggregate("APÁTRIDAS")
