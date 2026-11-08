"""Genera results/reports/informe.html: versión web autocontenida del proyecto
(figuras incrustadas en base64; cifras leídas de results/tables).

    python scripts/build_html.py
"""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "results" / "figures"
TAB = ROOT / "results" / "tables"
OUT = ROOT / "results" / "reports" / "informe.html"


def img(name: str, alt: str, caption: str) -> str:
    data = base64.b64encode((FIG / name).read_bytes()).decode()
    return (f'<figure class="fig"><img src="data:image/png;base64,{data}" alt="{html.escape(alt)}" loading="lazy">'
            f"<figcaption>{caption}</figcaption></figure>")


def f(x: float, d: int = 2) -> str:
    """Formato español: coma decimal, signo menos tipográfico."""
    s = f"{x:.{d}f}".replace(".", ",")
    return s.replace("-", "−")


def p_fmt(p: float) -> str:
    return "&lt;0,001" if p < 0.001 else f(p, 3)


def forest(rob: pd.DataFrame) -> str:
    """Gráfico de intervalos de confianza en HTML/CSS (escala común)."""
    rows = rob[~rob["modelo"].str.startswith("Niveles")].reset_index(drop=True)
    lo = min(rows["ci_low"].min(), 0) - 0.2
    hi = rows["ci_high"].max() + 0.2
    pos = lambda v: 100 * (v - lo) / (hi - lo)  # noqa: E731
    zero = pos(0)
    ticks = [t for t in range(int(lo) - 1, int(hi) + 2) if lo <= t <= hi]
    out = ['<div class="forest" role="table" aria-label="Coeficiente e intervalo de confianza al 95 % por especificación">']
    out.append('<div class="fr head" role="row"><span role="columnheader">Especificación</span>'
               '<span role="columnheader" class="axis">'
               + "".join(f'<i style="left:{pos(t):.2f}%">{f(t, 0)}</i>' for t in ticks)
               + '</span><span role="columnheader" class="num">β</span><span role="columnheader" class="num">p</span></div>')
    for r in rows.itertuples():
        sig = "sig" if r.p < 0.05 else ("weak" if r.p < 0.10 else "ns")
        main = " main" if r.modelo == "Principal" else ""
        out.append(
            f'<div class="fr{main}" role="row"><span role="cell">{html.escape(r.modelo)}</span>'
            f'<span role="cell" class="track"><b class="zero" style="left:{zero:.2f}%"></b>'
            f'<b class="ci {sig}" style="left:{pos(r.ci_low):.2f}%;width:{pos(r.ci_high) - pos(r.ci_low):.2f}%"></b>'
            f'<b class="pt {sig}" style="left:{pos(r.coef):.2f}%"></b></span>'
            f'<span role="cell" class="num">{f(r.coef)}</span><span role="cell" class="num">{p_fmt(r.p)}</span></div>')
    out.append("</div>")
    return "".join(out)


def build() -> Path:
    rob = pd.read_csv(TAB / "tabla_4_robustez.csv")
    diag = json.loads((TAB / "contrastes_panel.json").read_text())
    wool = json.loads((TAB / "wooldridge_autocorrelacion.json").read_text())
    nat = pd.read_csv(TAB / "serie_nacional.csv")
    get = lambda name: rob[rob["modelo"] == name].iloc[0]  # noqa: E731
    main, iv, share = get("Principal"), get("2SLS shift-share (nacidos ext.)"), get("Regresor: Δ proporción nacidos ext. (p.p.)")
    lvl = rob[rob["modelo"].str.startswith("Niveles")].iloc[0]
    cum = diag["efecto_acumulado_0_2"]
    t1 = pd.read_csv(TAB / "tabla_1_mco.csv", index_col=0)
    pooled = float(t1.iloc[0, 0].rstrip("*"))
    t3 = pd.read_csv(TAB / "tabla_3_iv.csv", index_col=0)
    fs = float(t3.loc["F primera etapa"].dropna().iloc[-1])
    y0, y1 = int(nat["anio"].min()), int(nat["anio"].max())
    n0, n1 = nat.iloc[0], nat.iloc[-1]

    page = TEMPLATE
    repl = {
        "{{MAIN}}": f(main.coef), "{{MAIN_LO}}": f(main.ci_low), "{{MAIN_HI}}": f(main.ci_high),
        "{{POOLED}}": f(pooled), "{{SHARE}}": f(share.coef), "{{SHARE_LO}}": f(share.ci_low), "{{SHARE_HI}}": f(share.ci_high),
        "{{CUM}}": f(cum["efecto_acumulado"]), "{{CUM_LO}}": f(cum["ci_low"]), "{{CUM_HI}}": f(cum["ci_high"]),
        "{{CUM_P}}": p_fmt(cum["p"]),
        "{{LVL}}": f(100 * lvl.coef), "{{LVL_LO}}": f(100 * lvl.ci_low), "{{LVL_HI}}": f(100 * lvl.ci_high), "{{LVL_P}}": p_fmt(lvl.p),
        "{{IV}}": f(iv.coef), "{{IV_LO}}": f(iv.ci_low), "{{IV_HI}}": f(iv.ci_high), "{{IV_P}}": p_fmt(iv.p), "{{FS}}": f(fs, 1),
        "{{NOBS}}": f"{int(main.nobs):,}".replace(",", "."), "{{WOOL}}": p_fmt(wool["pvalue"]),
        "{{Y0}}": str(y0), "{{Y1}}": str(y1),
        "{{FB0}}": f(n0.pct_nacidos_ext, 1), "{{FB1}}": f(n1.pct_nacidos_ext, 1),
        "{{P0}}": f"{n0.precio_m2_pond:,.0f}".replace(",", "."), "{{P1}}": f"{n1.precio_m2_pond:,.0f}".replace(",", "."),
        "{{PMAX}}": f"{nat.precio_m2_pond.max():,.0f}".replace(",", "."), "{{YMAX}}": str(int(nat.loc[nat.precio_m2_pond.idxmax(), 'anio'])),
        "{{FOREST}}": forest(rob),
        "{{FIG01}}": img("01_evolucion_nacional.png", "Serie nacional de precio y población nacida en el extranjero",
                         "Precio medio ponderado por población (€/m², nominal) y % de población nacida en el extranjero y extranjera. España, " + f"{y0}-{y1}."),
        "{{FIG05}}": img("05_dispersion_flujo_precio.png", "Dispersión flujo-precio",
                         "Cada punto es una provincia y un año. Correlación bruta, sin efectos fijos."),
        "{{FIG06}}": img("06_diferencias_largas.png", "Diferencias largas por provincia",
                         f"Cambio acumulado {y0}-{y1} por provincia: aumento de nacidos en el extranjero (% de la población inicial) frente a variación del precio."),
        "{{FIG07}}": img("07_mapa_var_nacidos_ext.png", "Mapa de la variación del % nacidos en el extranjero",
                         f"Variación del % de población nacida en el extranjero, {y0}-{y1} (puntos porcentuales)."),
        "{{FIG08}}": img("08_mapa_var_precio.png", "Mapa de la variación del precio", f"Variación nominal del precio, {y0}-{y1} (%)."),
        "{{FIG02}}": img("02_precio_ccaa.png", "Precio por CCAA", "Precio de la vivienda por comunidad autónoma (€/m²)."),
        "{{FIG03}}": img("03_nacidos_ext_ccaa.png", "Nacidos en el extranjero por CCAA", "Población nacida en el extranjero por comunidad autónoma (% de la población)."),
    }
    for k, v in repl.items():
        page = page.replace(k, v)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(page, encoding="utf-8")
    return OUT


TEMPLATE = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inmigración y precio de la vivienda en España</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
/* Plan: informe de investigación de una columna; tinta azul pizarra (como los gráficos) y rojo ladrillo
   para la inmigración; serif editorial en títulos, sans técnica en cuerpo, mono en cifras. */
:root{
  --ink:#16202b; --muted:#56616d; --paper:#f6f7f8; --surface:#ffffff; --rule:#d9dee3;
  --accent:#1f4e79; --migr:#b0433f; --good:#1f4e79; --weak:#b7791f; --ns:#8a939c;
  --display:"Newsreader", Georgia, "Times New Roman", serif;
  --body:"IBM Plex Sans", system-ui, -apple-system, "Segoe UI", sans-serif;
  --mono:"IBM Plex Mono", ui-monospace, Menlo, Consolas, monospace;
  color-scheme:light;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ink:#e6eaee; --muted:#9aa5b0; --paper:#11161c; --surface:#18202a; --rule:#2b3642;
    --accent:#7fb0dc; --migr:#e2817c; --good:#7fb0dc; --weak:#e0b25c; --ns:#6c7782; color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --ink:#e6eaee; --muted:#9aa5b0; --paper:#11161c; --surface:#18202a; --rule:#2b3642;
  --accent:#7fb0dc; --migr:#e2817c; --good:#7fb0dc; --weak:#e0b25c; --ns:#6c7782; color-scheme:dark;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--paper);color:var(--ink);font:400 16.5px/1.62 var(--body)}
main{max-width:860px;margin:0 auto;padding:40px 20px 80px}
.prose{max-width:68ch}
h1,h2,h3{font-family:var(--display);font-weight:600;line-height:1.15;text-wrap:balance;margin:0}
h1{font-size:clamp(2rem,4.6vw,2.9rem);letter-spacing:-.01em}
h2{font-size:1.7rem;margin-top:56px;padding-top:20px;border-top:1px solid var(--rule)}
h3{font-size:1.2rem;margin-top:28px}
p{margin:12px 0}
a{color:var(--accent)}
a:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.kicker{font:500 .78rem/1 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);display:flex;gap:14px;flex-wrap:wrap}
.lede{font-size:1.15rem;color:var(--muted);margin-top:14px}
.status{margin:26px 0 0;padding:14px 16px;border-left:3px solid var(--weak);background:var(--surface);border-radius:0 6px 6px 0;font-size:.95rem}
.keyfig{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:28px 0 0}
.keyfig div{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:14px 16px}
.keyfig strong{display:block;font:500 1.75rem/1.1 var(--mono);font-variant-numeric:tabular-nums}
.keyfig span{font-size:.86rem;color:var(--muted)}
.keyfig .m strong{color:var(--accent)} .keyfig .iv strong{color:var(--ns)}
.tbl{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:.93rem}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-weight:600;font-size:.8rem;text-transform:uppercase;letter-spacing:.04em;color:var(--muted)}
td.n,th.n{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}
tr.hl td{background:color-mix(in srgb,var(--accent) 9%,transparent);font-weight:600}
.eq{font-family:var(--mono);font-size:.95rem;background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:14px 16px;overflow-x:auto;white-space:nowrap}
.fig{margin:22px 0;background:#fff;border:1px solid var(--rule);border-radius:8px;padding:10px}
.fig img{display:block;width:100%;height:auto}
.fig figcaption{font-size:.84rem;color:#56616d;padding:8px 4px 2px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.pair .fig{margin:0}
ol.findings{padding-left:1.2em} ol.findings li{margin:10px 0}
.forest{background:var(--surface);border:1px solid var(--rule);border-radius:8px;padding:8px 14px;margin:18px 0}
.fr{display:grid;grid-template-columns:minmax(150px,1.3fr) 2fr 56px 62px;gap:12px;align-items:center;padding:8px 0;border-bottom:1px solid var(--rule);font-size:.9rem}
.fr:last-child{border-bottom:0}
.fr.head{font-size:.75rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.fr.head .num{text-transform:none}
.fr.main span:first-child{font-weight:600}
.fr .num{text-align:right;font-family:var(--mono);font-variant-numeric:tabular-nums}
.axis,.track{position:relative;height:18px}
.axis i{position:absolute;transform:translateX(-50%);font-style:normal;font-family:var(--mono)}
.track .zero{position:absolute;top:-6px;bottom:-6px;width:1px;background:var(--muted);opacity:.6}
.track .ci{position:absolute;top:8px;height:2px;border-radius:2px}
.track .pt{position:absolute;top:4px;width:10px;height:10px;border-radius:50%;transform:translateX(-50%)}
.sig{background:var(--good)} .weak{background:var(--weak)} .ns{background:var(--ns)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:.82rem;color:var(--muted)}
.legend b{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px;vertical-align:-1px}
pre{background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:14px 16px;overflow-x:auto;font:400 .86rem/1.55 var(--mono)}
code{font-family:var(--mono);font-size:.9em}
.refs li{margin:6px 0;font-size:.93rem}
footer{margin-top:60px;padding-top:18px;border-top:1px solid var(--rule);font-size:.85rem;color:var(--muted)}
@media (max-width:620px){.pair{grid-template-columns:1fr}.fr{grid-template-columns:1fr 54px 58px}.fr .track,.fr .axis{grid-column:1/-1;grid-row:2}}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style>
</head>
<body>
<main>
<header>
  <div class="kicker"><span>Econometría aplicada</span><span>Panel provincial · {{Y0}}-{{Y1}}</span><span>Datos INE · MIVAU</span></div>
  <h1 style="margin-top:14px">El impacto de la inmigración en los precios de la vivienda en España</h1>
  <p class="lede prose">Un análisis econométrico territorial y temporal con las 52 provincias españolas: cuánto se asocia la llegada de población nacida en el extranjero con el crecimiento del precio de la vivienda, y hasta qué punto esa relación puede leerse como causal.</p>
  <p class="status prose"><strong>Estado:</strong> estimado con datos oficiales del INE (Padrón, tablas 03005 y 03006) y del MIVAU (valor tasado, VDP006_01). <strong>Aún sin controles económicos</strong> (PIB, paro, edad, densidad): los resultados deben leerse con esa limitación.</p>
  <div class="keyfig">
    <div class="m"><strong>{{MAIN}}</strong><span>p.p. de crecimiento del precio por un flujo = 1 % de la población (efectos fijos)</span></div>
    <div><strong>{{POOLED}}</strong><span>la misma relación sin efectos fijos: la correlación bruta exagera</span></div>
    <div class="iv"><strong>{{IV}}</strong><span>estimación causal (2SLS), no significativa (p = {{IV_P}})</span></div>
  </div>
</header>

<h2>Resumen</h2>
<div class="prose">
<p>Entre {{Y0}} y {{Y1}}, el peso de la población nacida en el extranjero pasó del {{FB0}} % al {{FB1}} % de la población residente, y el precio medio de la vivienda libre pasó de {{P0}} a {{P1}} €/m², con un máximo de {{PMAX}} €/m² en {{YMAX}}. Que ambas series suban a la vez no demuestra una relación causal: los inmigrantes se instalan donde hay empleo, que es también donde la demanda de vivienda crece por otros motivos.</p>
<p>Con efectos fijos de provincia y año, un aumento neto de residentes nacidos en el extranjero igual al 1 % de la población se asocia con <strong>{{MAIN}} puntos porcentuales</strong> más de crecimiento anual del precio. La relación es robusta, pero el instrumento <em>shift-share</em> no permite confirmar que sea causal.</p>
</div>
{{FIG01}}

<h2>Pregunta e hipótesis</h2>
<p class="prose"><strong>Pregunta.</strong> ¿En qué medida el crecimiento de la población nacida en el extranjero en una provincia se asocia con el crecimiento del precio de la vivienda, y puede esa relación interpretarse como un efecto causal?</p>
<div class="tbl"><table>
<thead><tr><th></th><th>Hipótesis</th><th>Resultado</th></tr></thead>
<tbody>
<tr><td><strong>H1</strong></td><td>Un flujo neto de nacidos en el extranjero igual al 1 % de la población se asocia con mayor crecimiento del precio (β &gt; 0).</td><td>Se cumple como asociación</td></tr>
<tr><td><strong>H2</strong></td><td>El efecto acumulado a dos años supera al contemporáneo.</td><td>No hay evidencia clara</td></tr>
<tr><td><strong>H3</strong></td><td>El efecto se atenúa con más construcción y salidas de nativos.</td><td>No contrastada aún (faltan datos de construcción)</td></tr>
<tr><td><strong>H4</strong></td><td>MCO/EF no identifican el efecto causal por la elección endógena del destino.</td><td>Coherente: el IV es menor e impreciso</td></tr>
</tbody></table></div>

<h2>Datos</h2>
<div class="tbl"><table>
<thead><tr><th>Concepto</th><th>Variable</th><th>Fuente</th><th>Escala</th></tr></thead>
<tbody>
<tr><td>Precio de la vivienda</td><td>Valor tasado vivienda libre (€/m²)</td><td>MIVAU</td><td>Provincia, trimestral</td></tr>
<tr><td>Población nacida en el extranjero</td><td>Stock a 1 de enero</td><td>INE, Padrón Continuo</td><td>Provincia</td></tr>
<tr><td>Población extranjera (por nacionalidad)</td><td>Stock a 1 de enero</td><td>INE, Padrón Continuo</td><td>Provincia</td></tr>
<tr><td>PIB, población, estructura por edades, superficie</td><td>PIB per cápita, % población 25-34 años, densidad (hab./km²)</td><td>Eurostat</td><td>NUTS-3 → provincia</td></tr>
<tr><td>Tasa de paro</td><td>% población activa 15-74 años</td><td>Eurostat (EPA)</td><td>CCAA</td></tr>
<tr><td>Tipo de interés a 10 años</td><td>Rendimiento de la deuda pública a 10 años (%)</td><td>Eurostat</td><td>España</td></tr>
<tr><td>Viviendas terminadas</td><td>Viviendas libres terminadas por 1.000 hab.</td><td>MIVAU</td><td>Provincia</td></tr>
</tbody></table></div>

<h3>Armonización</h3>
<ul class="prose">
<li><strong>Frecuencia.</strong> Precio anual = media de los 4 trimestres; solo se conservan los años con los 4. Robustez: precio del 4.º trimestre.</li>
<li><strong>Fechas.</strong> El stock del Padrón a 1/1/(t+1) se asigna al año t (final de año), de modo que el flujo del año t ocurre durante el mismo año natural que los precios.</li>
<li><strong>Periodo común.</strong> Solo los años cubiertos por las tres fuentes: {{Y0}}-{{Y1}}.</li>
<li><strong>Limpieza.</strong> Los ceros del MIVAU (trimestres no publicados) se tratan como ausentes; mantenerlos generaba variaciones espurias de hasta ±138 %.</li>
<li><strong>Proporción frente a tamaño.</strong> Además del flujo, se estima con la variación de la proporción de nacidos en el extranjero, que no depende del tamaño de la población.</li>
</ul>

<div class="pair">{{FIG07}}{{FIG08}}</div>

<h2>Metodología</h2>
<p class="prose"><strong>Modelo principal</strong> (panel con efectos fijos de provincia y año, errores agrupados por provincia):</p>
<div class="eq">100·Δln P<sub>pt</sub> = β · 100·(FB<sub>pt</sub> − FB<sub>p,t−1</sub>) / Pob<sub>p,t−1</sub> + X′<sub>pt</sub>γ + μ<sub>p</sub> + τ<sub>t</sub> + ε<sub>pt</sub></div>
<p class="prose">β mide los puntos porcentuales de crecimiento anual del precio asociados a un flujo neto igual al 1 % de la población. τ<sub>t</sub> absorbe todo lo común a España cada año: tipos de interés, crédito, ciclo nacional.</p>
<p class="prose"><strong>Identificación causal (2SLS).</strong> Instrumento <em>shift-share</em>: el flujo predicho a partir del peso inicial de cada nacionalidad en la provincia y de su crecimiento nacional excluida esa provincia.</p>
<div class="eq">Z<sub>pt</sub> = 100 · Σ<sub>n</sub> s<sub>n,p,t0</sub> · ΔN<sub>n,t</sub><sup>(−p)</sup> / Pob<sub>p,t−1</sub></div>
<p class="prose">Es válido solo si la geografía inicial de los enclaves no predice <em>shocks</em> posteriores de precios por otras vías, un supuesto que no puede contrastarse directamente.</p>

<h2>Resultados</h2>
<p class="prose">52 provincias, {{Y0}}-{{Y1}}, {{NOBS}} observaciones provincia-año en el modelo principal. Errores agrupados por provincia. Sin controles económicos.</p>
<div class="tbl"><table>
<thead><tr><th>Especificación</th><th class="n" style="text-transform:none">β</th><th class="n">IC 95 %</th><th class="n">p</th></tr></thead>
<tbody>
<tr><td>MCO agrupado (sin efectos fijos)</td><td class="n">{{POOLED}}</td><td class="n">—</td><td class="n">&lt;0,001</td></tr>
<tr class="hl"><td>EF provincia + año (principal)</td><td class="n">{{MAIN}}</td><td class="n">{{MAIN_LO}} a {{MAIN_HI}}</td><td class="n">&lt;0,001</td></tr>
<tr><td>Variación de la proporción de nacidos en el extranjero (p.p.)</td><td class="n">{{SHARE}}</td><td class="n">{{SHARE_LO}} a {{SHARE_HI}}</td><td class="n">&lt;0,001</td></tr>
<tr><td>Efecto acumulado, retardos 0-2</td><td class="n">{{CUM}}</td><td class="n">{{CUM_LO}} a {{CUM_HI}}</td><td class="n">{{CUM_P}}</td></tr>
<tr><td>Niveles: % de variación del precio por +1 p.p. de nacidos fuera</td><td class="n">{{LVL}} %</td><td class="n">{{LVL_LO}} a {{LVL_HI}}</td><td class="n">{{LVL_P}}</td></tr>
<tr class="hl"><td>2SLS shift-share (F 1.ª etapa: {{FS}})</td><td class="n">{{IV}}</td><td class="n">{{IV_LO}} a {{IV_HI}}</td><td class="n">{{IV_P}}</td></tr>
</tbody></table></div>

<h3>Coeficiente por especificación</h3>
<p class="prose">Efecto de un flujo igual al 1 % de la población sobre el crecimiento anual del precio (p.p.), con su intervalo de confianza al 95 %.</p>
{{FOREST}}
<div class="legend"><span><b class="sig"></b>p &lt; 0,05</span><span><b class="weak"></b>0,05 ≤ p &lt; 0,10</span><span><b class="ns"></b>p ≥ 0,10</span></div>

<h3>Interpretación</h3>
<ol class="findings prose">
<li><strong>La correlación bruta es engañosa.</strong> Sin efectos fijos, β ≈ {{POOLED}}; con efectos de provincia y año cae a {{MAIN}}. Buena parte de la asociación refleja que inmigración y precios se movieron juntos con el ciclo nacional.</li>
<li><strong>Asociación condicional positiva y robusta.</strong> Se mantiene con la definición por nacionalidad, con la variación de la proporción, con el precio del 4.º trimestre, sin provincias atípicas, sin valores extremos y excluyendo provincias de una en una.</li>
<li><strong>Diferencias en el tiempo.</strong> Débil en la expansión hasta 2007, nula en la crisis 2008-2013 y más intensa en la recuperación desde 2014.</li>
<li><strong>Causalidad no demostrada.</strong> El instrumento es fuerte, pero el 2SLS ({{IV}}) tiene un intervalo que incluye el cero. Es coherente con que parte de la asociación refleje que los inmigrantes van a provincias con demanda creciente, aunque la imprecisión impide afirmarlo. Tampoco puede descartarse un efecto moderado.</li>
<li><strong>Sin acumulación a medio plazo.</strong> El efecto acumulado a dos años ({{CUM}}) es prácticamente igual al del primer año.</li>
<li><strong>Diagnósticos.</strong> El test de Wooldridge detecta autocorrelación (p {{WOOL}}), lo que justifica agrupar los errores por provincia.</li>
</ol>

<div class="pair">{{FIG05}}{{FIG06}}</div>
<div class="pair">{{FIG02}}{{FIG03}}</div>

<h2>Conclusiones principales</h2>
<ol class="findings prose">
<li><strong>Existe una asociación positiva y estable.</strong> En las provincias y años en que llega más población nacida en el extranjero, el precio de la vivienda crece más: unos {{MAIN}} puntos porcentuales por cada flujo equivalente al 1 % de la población, una magnitud similar a la encontrada por Saiz (2007) en EE. UU.</li>
<li><strong>La relación bruta exagera el vínculo.</strong> Sin efectos fijos el coeficiente es {{POOLED}}; la mayor parte de la coincidencia entre inmigración y precios se explica por el ciclo económico nacional común a todas las provincias.</li>
<li><strong>El resultado no depende de cómo se mida la inmigración.</strong> Es similar con nacidos en el extranjero o con extranjeros, y con flujos o con la variación de la proporción sobre la población total.</li>
<li><strong>Depende de la fase del ciclo.</strong> La asociación es débil en el <em>boom</em> hasta 2007, desaparece en la crisis de 2008-2013 y es más intensa en la recuperación desde 2014.</li>
<li><strong>No se puede afirmar que sea causal.</strong> Al instrumentar con la red histórica de compatriotas, el efecto baja a {{IV}} y deja de ser significativo. Parte de la asociación podría deberse a que los inmigrantes se dirigen a provincias donde la demanda ya estaba creciendo.</li>
<li><strong>Siguiente paso.</strong> Incorporar controles económicos (renta, paro, construcción) y repetir el análisis a escala municipal para comprobar si el resultado se mantiene.</li>
</ol>

<h2>Sobre el autor</h2>
<div class="prose">
<p><strong>Lorenzo</strong> · Estudiante de cuarto curso de Administración y Dirección de Empresas (ADE) en la Universidad de Castilla-La Mancha (Ciudad Real).</p>
<p>Me estoy especializando en análisis de datos y métodos cuantitativos, dentro de la intensificación en Economía y Métodos Cuantitativos, y quiero continuar con un máster en modelización y análisis de datos económicos. Este proyecto forma parte de mi portfolio: construir un panel con datos oficiales, armonizar fuentes distintas y estimar modelos econométricos de forma reproducible en Python.</p>
<p>Más proyectos en <a href="https://github.com/lromeronez16-maker">github.com/lromeronez16-maker</a>.</p>
</div>

<h2>Reproducción</h2>
<pre>git clone https://github.com/lromeronez16-maker/inmigracion-precio-vivienda-espana.git
cd inmigracion-precio-vivienda-espana
pip install -r requirements.txt
python -m src.run_pipeline --skip-download</pre>
<p class="prose">Código en Python (pandas, statsmodels, linearmodels). Repositorio: <a href="https://github.com/lromeronez16-maker/inmigracion-precio-vivienda-espana">github.com/lromeronez16-maker/inmigracion-precio-vivienda-espana</a>.</p>

<h2>Referencias principales</h2>
<ul class="refs prose">
<li>Card, D. (2001). Immigrant inflows, native outflows, and the local labor market impacts of higher immigration. <em>Journal of Labor Economics</em>, 19(1), 22–64.</li>
<li>Goldsmith-Pinkham, P., Sorkin, I. y Swift, H. (2020). Bartik instruments: What, when, why, and how. <em>American Economic Review</em>, 110(8), 2586–2624.</li>
<li>González, L. y Ortega, F. (2013). Immigration and housing booms: Evidence from Spain. <em>Journal of Regional Science</em>, 53(1), 37–59.</li>
<li>Sá, F. (2015). Immigration and house prices in the UK. <em>Economic Journal</em>, 125(587), 1393–1424.</li>
<li>Saiz, A. (2007). Immigration and housing rents in American cities. <em>Journal of Urban Economics</em>, 61(2), 345–371.</li>
</ul>

<footer>Fuentes: INE (Estadística del Padrón Continuo), MIVAU (valor tasado de la vivienda). Elaboración propia. Cifras generadas automáticamente a partir de las estimaciones del repositorio.</footer>
</main>
</body>
</html>
"""

if __name__ == "__main__":
    print(build())
