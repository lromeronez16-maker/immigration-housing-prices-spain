"""
DATOS SINTÉTICOS — SOLO PARA PRUEBAS DE SOFTWARE.

Este módulo genera un panel artificial con la misma estructura que el panel real para:
- ejecutar los tests automáticos (tests/),
- comprobar que los notebooks y el pipeline funcionan de principio a fin (modo INMIG_DEMO=1).

Las cifras NO proceden de ninguna fuente oficial y NO deben interpretarse ni publicarse
como resultados. Todos los gráficos y tablas generados en modo demo llevan la marca
"DATOS SINTÉTICOS" y se guardan en results/_demo/ (excluido del control de versiones).

El proceso generador incluye un efecto conocido (TRUE_BETA_FLOW) para que los tests puedan
verificar que los estimadores recuperan el parámetro correcto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

TRUE_BETA_FLOW = 1.5      # efecto verdadero de un flujo = 1 % de la población sobre Δln precio (p.p.)
SYNTHETIC_YEARS = range(2002, 2024)
NATIONALITIES = ["A", "B", "C", "D", "E", "F"]


def make_synthetic_nationalities(seed: int = 7) -> pd.DataFrame:
    """Stock sintético de extranjeros por nacionalidad, provincia y año."""
    rng = np.random.default_rng(seed)
    rows = []
    # Cuotas de cada nacionalidad heterogéneas entre provincias (enclaves)
    share = rng.dirichlet(np.ones(len(config.PROVINCE_CODES)) * 0.6, size=len(NATIONALITIES))
    nat_growth = rng.normal(0.04, 0.06, size=(len(NATIONALITIES), len(SYNTHETIC_YEARS)))
    totals = rng.uniform(50_000, 600_000, size=len(NATIONALITIES))
    for n_i, nat in enumerate(NATIONALITIES):
        level = totals[n_i]
        for t_i, year in enumerate(SYNTHETIC_YEARS):
            level *= 1 + nat_growth[n_i, t_i]
            for p_i, cod in enumerate(config.PROVINCE_CODES):
                noise = rng.normal(1, 0.03)
                rows.append({"provincia_cod": cod, "anio": year, "nacionalidad": nat,
                             "poblacion": max(level * share[n_i, p_i] * noise, 0.0)})
    return pd.DataFrame(rows)


def make_synthetic_panel(seed: int = 42) -> pd.DataFrame:
    """Panel sintético provincia-año con columnas de nivel (antes de add_derived_variables)."""
    rng = np.random.default_rng(seed)
    nat = make_synthetic_nationalities(seed + 1)
    ext = nat.groupby(["provincia_cod", "anio"], as_index=False)["poblacion"].sum().rename(columns={"poblacion": "extranjeros"})
    years = list(SYNTHETIC_YEARS)
    year_fe = dict(zip(years, rng.normal(3, 5, len(years))))
    rows = []
    for cod in config.PROVINCE_CODES:
        pop = rng.uniform(1e5, 6e6)
        area = rng.uniform(500, 15_000)
        price = rng.uniform(800, 3000)
        prov_fe = rng.normal(0, 1)
        gdp_pc = rng.uniform(17_000, 35_000)
        e = ext[ext["provincia_cod"] == cod].set_index("anio")["extranjeros"]
        fb_prev = None
        for y in years:
            fb = e[y] * 1.25 + pop * 0.01  # nacidos en el extranjero > extranjeros (nacionalizados)
            if fb_prev is not None:
                flow = 100 * (fb - fb_prev) / pop
                g_gdp = rng.normal(1.5, 2)
                price *= np.exp((year_fe[y] + prov_fe + TRUE_BETA_FLOW * flow + 0.3 * g_gdp + rng.normal(0, 2)) / 100)
                gdp_pc *= np.exp(g_gdp / 100)
                pop = pop * (1 + rng.normal(0.003, 0.002)) + (fb - fb_prev)
            fb_prev = fb
            rows.append({
                "provincia_cod": cod, "anio": y, "precio_m2": price,
                "nacidos_extranjero": fb, "extranjeros": e[y], "poblacion_total": pop,
                "pib_meur": gdp_pc * pop / 1e6, "superficie_km2": area,
                "pct_joven_25_34": float(np.clip(rng.normal(13, 1.5), 8, 20)),
                "tasa_paro_ccaa": float(np.clip(rng.normal(15, 5), 4, 35)),
                "tipo_interes_lp": 4 - 0.12 * (y - 2002) + rng.normal(0, 0.1),
                "viviendas_terminadas": abs(rng.normal(4, 2)) * pop / 1000,
            })
    df = pd.DataFrame(rows)
    df.attrs["SINTETICO"] = True
    return df
