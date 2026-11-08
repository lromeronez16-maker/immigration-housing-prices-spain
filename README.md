# The Impact of Immigration on Housing Prices in Spain
### A territorial and temporal econometric analysis (provincial panel)

🌐 **English** · [Español](README.es.md)

![tests](https://github.com/lromeronez16-maker/inmigracion-precio-vivienda-espana/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> **Project status:** estimated with official data from INE (Municipal Register, tables 03005 and 03006) and MIVAU (appraised housing values, VDP006_01) for **52 provinces, 1997-2021**. **No economic controls yet** (GDP, unemployment, age structure and density from Eurostat): the code downloads them, but this run was made without them. The results below should be read with that limitation in mind.

---

## Executive summary

Since the early 2000s, Spain has gone through two major immigration waves and two cycles of sharp housing price increases. The timing alone does not prove a causal link. Immigrants choose where to settle, and they tend to go where jobs are, which is also where housing demand rises for other reasons.

This project builds a **panel of Spain's 52 provinces** from official data (INE, MIVAU and Eurostat) and estimates the relationship between growth in the foreign-born population and growth in housing prices. It proceeds in several steps:

1. **Descriptive analysis** of how both variables evolve over time and are distributed across provinces.
2. **Pooled OLS** with economic and demographic controls.
3. **Fixed-effects panel** with province and year fixed effects, standard errors clustered by province, distributed lags and joint significance tests.
4. **Shift-share instrumental variables** (Card, 2001; González and Ortega, 2013) based on the historical distribution of each nationality across provinces, with an explicit discussion of their assumptions and risks.
5. **Robustness**: alternative definitions, excluding atypical provinces and outliers, sub-periods of the cycle, leave-one-province-out, multicollinearity and serial correlation.

The aim is to measure the size of the relationship and how far it can be read as causal, without starting from a predetermined conclusion.

## Research question

> To what extent is growth in the foreign-born population of a province associated with growth in its housing prices, and can that relationship be interpreted as a causal effect?

## Hypotheses

| | Hypothesis |
|---|---|
| **H1** | A net inflow of foreign-born residents equal to 1% of the provincial population is associated with higher annual price growth (β > 0), conditional on fixed effects and controls. |
| **H2** | The cumulative two-year effect exceeds the contemporaneous effect (slow supply adjustment). |
| **H3** | The effect is weaker where more housing is built, and may be offset by native outflows. |
| **H4** | OLS/FE do not identify the causal effect because immigrants choose their destination endogenously. The direction of the bias is ambiguous. |

Theory, transmission mechanisms and offsetting effects: [`docs/methodology.md`](docs/methodology.md) (in Spanish).

## Data

| Concept | Variable | Source | Level |
|---|---|---|---|
| Housing price | Appraised value of free-market housing (€/m²) | MIVAU (Ministry of Housing) | Province, quarterly |
| Foreign-born population | Stock on 1 January | INE, Municipal Register (Padrón) | Province |
| Foreign nationals (by nationality) | Stock on 1 January | INE, Municipal Register (Padrón) | Province |
| GDP, population, age structure, area | GDP per capita, % population aged 25-34, density (inhabitants/km²) | Eurostat | NUTS-3 → province |
| Unemployment rate | % of labour force aged 15-74 | Eurostat (Labour Force Survey) | Region (CCAA) |
| 10-year interest rate | 10-year government bond yield (%) | Eurostat | Spain |
| Completed dwellings | Completed free-market dwellings per 1,000 inhabitants | MIVAU | Province |

The project explicitly distinguishes between the **foreign-born population** (country of birth), **foreign nationals** (citizenship) and **net flows**; they are not treated as equivalent. Sources, download paths and unavailable data are documented in [`docs/data_sources.md`](docs/data_sources.md) (in Spanish).

### Harmonisation

- **Frequency:** the annual price is the average of the 4 quarters of the calendar year, and only years with all 4 quarters are kept. Robustness check: fourth-quarter price.
- **Reference dates:** the Register stock on 1 January of year t+1 is assigned to year t (end-of-year stock), so the year-t flow happens during the same calendar year as the prices.
- **Common period:** only years covered by all three sources are used, 1997-2021.
- **Data cleaning:** MIVAU zeros (unpublished quarters) are treated as missing; leaving them in produced spurious annual changes of up to ±138%.
- **Share vs. population size:** besides the flow scaled by initial population, the model is also estimated with the change in the foreign-born **share** (percentage points), which does not depend on population size.

## Methodology

**Main model (fixed-effects panel):**

$$100\,\Delta\ln P_{pt} = \beta \cdot \underbrace{100\,\frac{FB_{pt}-FB_{p,t-1}}{Pop_{p,t-1}}}_{\text{net foreign-born inflow}} + X_{pt}'\gamma + \mu_p + \tau_t + \varepsilon_{pt}$$

- β: percentage points of annual price growth associated with a net inflow equal to 1% of the population.
- μ<sub>p</sub>, τ<sub>t</sub>: province and year fixed effects. τ<sub>t</sub> absorbs interest rates, credit conditions and the national cycle.
- Standard errors clustered by province.

**Causal identification (2SLS):** the instrument is the predicted inflow

$$Z_{pt} = 100 \sum_n s_{n,p,t_0}\,\frac{\Delta N^{(-p)}_{n,t}}{Pop_{p,t-1}}$$

which combines each nationality's initial share in the province with its national growth excluding that province (leave-one-out). It is valid only if the initial geography of immigrant enclaves does not predict later price shocks through other channels. That assumption cannot be tested directly and is discussed in detail in the methodology.

## Results

> All figures come from `results/` and are generated automatically by `python -m src.run_pipeline`. Sample: 52 provinces, 1997-2021 (1,216 province-year observations in the main model). Standard errors clustered by province. **No economic controls.**

![National trends](results/figures/01_evolucion_nacional.png)

### Main results

| Specification | β | 95% CI | p |
|---|---|---|---|
| Pooled OLS (no fixed effects) | 5.49 | — | <0.001 |
| **Province + year FE (main)** | **1.20** | 0.69 to 1.71 | <0.001 |
| Change in foreign-born share (pp) | 1.55 | 0.95 to 2.14 | <0.001 |
| Cumulative effect, lags 0-2 | 1.14 | 0.43 to 1.86 | 0.002 |
| Levels: ln price on % foreign-born | 0.0088 | −0.0001 to 0.018 | 0.051 |
| **2SLS shift-share** (first stage: 47.8) | **0.47** | −0.51 to 1.45 | 0.345 |

β = percentage points of annual price growth associated with a net increase in foreign-born residents equal to 1% of the provincial population.

### Interpretation

1. **The raw correlation is misleading.** Without fixed effects, β ≈ 5.5. Controlling for province and year, it falls to 1.2. Much of the raw association reflects immigration and prices moving together over the national cycle (the 1998-2007 boom, the crisis, the recovery), not differences between provinces.
2. **A positive and robust conditional association.** With fixed effects, a net inflow equal to 1% of the population is associated with about 1.2 pp higher price growth that year. The result holds with the nationality-based definition (1.10), with the change in share (1.55), with the fourth-quarter price (1.20), without atypical provinces (1.19), without outliers (1.35) and when dropping provinces one at a time (1.13-1.36). The magnitude is comparable to Saiz (2007) for the US (around 1).
3. **Differences over time.** β = 0.60 (p = 0.06) in the expansion up to 2007, −0.33 (p = 0.57) in the 2008-2013 crisis and 1.52 (p = 0.001) in the recovery since 2014.
4. **Causality: not established.** The shift-share instrument is strong (first stage: 47.8), but the 2SLS estimate is 0.47 with a confidence interval that includes zero (p = 0.35). The reduced form is not significant either. The IV estimate is smaller than the fixed-effects one, which is consistent with part of the association reflecting immigrants moving to provinces where demand was already rising. Even so, the estimate is too imprecise to say this with confidence. **These data do not show that immigration causes higher housing prices at the provincial level.** A moderate effect cannot be ruled out either.
5. **Short vs. medium run.** The cumulative two-year effect (1.14) is practically the same as the contemporaneous one (1.12): there is no evidence that the effect builds up over time. The second lag is negative (−0.42, p < 0.10).
6. **Diagnostics.** Wooldridge's test detects serial correlation (p < 0.001), which justifies clustering by province. There is no relevant multicollinearity (VIF ≈ 1).

![Coefficients by specification](results/figures/09_coeficientes_especificaciones.png)

| Output | Contents |
|---|---|
| `results/tables/tabla_1_mco.*` | Pooled OLS |
| `results/tables/tabla_2_panel.*` | Fixed effects, lags, share, levels |
| `results/tables/tabla_3_iv.*` | 2SLS, first stage, reduced form |
| `results/tables/tabla_4_robustez.*` | Comparison across specifications |
| `results/reports/resumen_resultados.md` | Report generated only from the estimates |

Tables, figures and the automatic report are in Spanish.

## Limitations

- **No economic controls in this version** (income, unemployment, age structure, density, construction). Year fixed effects absorb the common cycle, but not province-specific economic shocks.
- Appraised value is not a transaction price, and prices are nominal. MIVAU does not publish some quarters for small provinces (10 province-years excluded).
- Flows are net and come from the Municipal Register, which has periodic clean-ups and methodological changes.
- In Eurostat, the unemployment rate is only available by region (CCAA).
- The provincial level may hide effects within provinces.
- 52 clusters: inference is only moderately reliable.
- The IV relies on assumptions that cannot be tested directly.
- The municipal-level version is not implemented.

## Repository structure

```
├── data/              raw/ (originals + .meta.json) · processed/ · README.md
├── docs/              methodology.md · data_sources.md · literature_review.md
├── notebooks/         01 exploration → 05 robustness and causality
├── results/           tables/ · figures/ · reports/
├── scripts/           build_notebooks.py
├── src/
│   ├── config.py               paths, provinces, NUTS codes
│   ├── data_collection.py      Eurostat / INE downloads + provenance
│   ├── official_sources.py     INE and MIVAU file readers, harmonisation
│   ├── data_cleaning.py        panel construction and validation
│   ├── descriptive_analysis.py
│   ├── econometric_models.py   OLS, FE, shift-share 2SLS, diagnostics, tables
│   ├── visualizations.py
│   ├── analysis.py             analysis stages and automatic report
│   ├── run_pipeline.py         full run
│   └── synthetic.py            SYNTHETIC data for tests/demo only
└── tests/             pytest
```

Code comments and the documentation in `docs/` are in Spanish.

## Reproducing the results

```bash
git clone https://github.com/lromeronez16-maker/inmigracion-precio-vivienda-espana.git
cd inmigracion-precio-vivienda-espana
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

pytest -q                                   # tests

python -m src.run_pipeline --skip-download  # panel + models + tables + figures + report
```

The converted official data are already in `data/raw/manual/`, so the last command reproduces the results directly.

- **Adding the Eurostat controls:** run `python -m src.data_collection` before the pipeline.
- **Rebuilding from the original INE/MIVAU files:** save INE tables 03006 and 03005 and MIVAU file VDP006_01 in `data/raw/manual/originales/`, then run `python -m src.official_sources`.
- **Checking the code without real data:** run `python -m src.run_pipeline --demo`. It uses **synthetic data**, writes to `results/_demo/` (not version-controlled) and marks every output as not real.

## Key references

- Card, D. (2001). Immigrant inflows, native outflows, and the local labor market impacts of higher immigration. *Journal of Labor Economics*, 19(1), 22–64.
- Goldsmith-Pinkham, P., Sorkin, I. and Swift, H. (2020). Bartik instruments: What, when, why, and how. *American Economic Review*, 110(8), 2586–2624.
- González, L. and Ortega, F. (2013). Immigration and housing booms: Evidence from Spain. *Journal of Regional Science*, 53(1), 37–59.
- Sá, F. (2015). Immigration and house prices in the UK. *Economic Journal*, 125(587), 1393–1424.
- Saiz, A. (2007). Immigration and housing rents in American cities. *Journal of Urban Economics*, 61(2), 345–371.

Full list: [`docs/literature_review.md`](docs/literature_review.md).

## License

Code released under the MIT License. The data belong to the agencies that produce them and are subject to their reuse terms.
