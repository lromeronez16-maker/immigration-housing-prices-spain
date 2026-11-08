# Metodología

## 1. Pregunta de investigación

**Pregunta principal.** ¿En qué medida el crecimiento de la población nacida en el extranjero en una provincia española se asocia con el crecimiento del precio de la vivienda en esa provincia? ¿Puede interpretarse esa relación como causal?

**Preguntas secundarias.**

1. ¿El efecto es inmediato o se acumula en los años siguientes (corto frente a medio plazo)?
2. ¿Depende el resultado de cómo se mida la inmigración (nacidos en el extranjero frente a extranjeros, stock frente a flujo)?
3. ¿Es homogéneo entre provincias y entre fases del ciclo inmobiliario (expansión 2000-2007, crisis 2008-2013, recuperación desde 2014)?
4. ¿Cambia la estimación al instrumentar los flujos con un instrumento *shift-share*?

## 2. Hipótesis

- **H1 (principal).** Un flujo neto de población nacida en el extranjero equivalente al 1 % de la población provincial se asocia con un mayor crecimiento del precio de la vivienda (β > 0), condicionado a efectos fijos de provincia y año y a controles económicos.
- **H2.** El efecto acumulado a dos años es mayor que el efecto contemporáneo, porque la oferta de vivienda se ajusta con retraso.
- **H3.** El efecto es menor cuando la oferta es más elástica (más construcción) y puede verse compensado por salidas de población nativa.
- **H4.** La estimación MCO/EF está sesgada respecto del efecto causal por la elección endógena de destino de los inmigrantes. El signo del sesgo es ambiguo a priori (ver §5).

Las hipótesis se contrastan; no se presupone que se cumplan.

## 3. Marco teórico

Se parte del modelo de stock-flujo del mercado de la vivienda (DiPasquale y Wheaton, 1992). A corto plazo el stock de vivienda es prácticamente fijo, de modo que un aumento de la demanda residencial se traslada sobre todo a precios y alquileres. A medio plazo la construcción responde y el efecto sobre el precio depende de la **elasticidad de la oferta** (Saiz, 2010), que en España varía mucho entre provincias (suelo disponible, geografía, regulación urbanística).

### Mecanismos de transmisión

| Canal | Dirección esperada sobre precios |
|---|---|
| Aumento del número de hogares y de la demanda residencial, inicialmente sobre todo en alquiler | + |
| Mayor demanda de compra a medida que los inmigrantes se asientan y acceden al crédito | + |
| Mayor oferta de trabajo en la construcción, que abarata la producción de vivienda | − |
| Salida de población nativa de las zonas receptoras (*native flight*; Saiz y Wachter, 2011; Sá, 2015) | − |
| Composición: menor renta media de los recién llegados, más demanda de vivienda barata | ambigua |
| Efecto sobre la actividad económica local (empleo, consumo) | + |

### Causalidad inversa y selección

Los inmigrantes eligen dónde vivir. Pueden dirigirse a provincias con fuerte creación de empleo, que son también las de mayor presión sobre los precios (sesgo al alza de MCO). También pueden evitar las provincias caras (sesgo a la baja). El Banco de España (Informe Anual 2025) analiza el efecto de los precios de la vivienda sobre la localización de los inmigrantes, lo que confirma que la causalidad inversa es relevante en el caso español.

## 4. Definiciones: no son categorías equivalentes

| Concepto | Definición | Fuente | Variable |
|---|---|---|---|
| Población **nacida en el extranjero** | Residentes cuyo país de nacimiento no es España. Incluye a los españoles nacionalizados y a los españoles nacidos fuera. | INE, Padrón | `nacidos_extranjero`, `pct_nacidos_ext` |
| Población **extranjera** | Residentes con nacionalidad no española. Excluye a los nacionalizados e incluye a los nacidos en España con nacionalidad extranjera. | INE, Padrón | `extranjeros`, `pct_extranjeros` |
| **Flujo** neto | Variación anual del stock a 1 de enero, en % de la población del año anterior. Es una medida **neta**: entradas menos salidas y defunciones (y, en el caso de los extranjeros, menos nacionalizaciones). | Derivado | `flujo_nacidos_ext`, `flujo_extranjeros` |
| Flujos **brutos** | Entradas registradas (Estadística de Variaciones Residenciales / Estadística de Migraciones). | INE | No incorporados en esta versión |

La medida principal es la de **nacidos en el extranjero**, porque no cambia con las nacionalizaciones. Estas fueron masivas en España durante los años 2010, sobre todo de personas latinoamericanas, y hacen que el stock de extranjeros caiga aunque nadie se vaya. La definición por nacionalidad se usa como robustez y en el instrumento, porque el Padrón desagrega por nacionalidad.

## 5. Especificaciones

**Variable dependiente principal:** `dln_precio` = 100 · Δln(valor tasado €/m²), que es aproximadamente la tasa de crecimiento nominal anual. Alternativa: `ln_precio` en niveles.

**Variable explicativa principal:** `flujo_nacidos_ext` = 100 · (FB<sub>pt</sub> − FB<sub>p,t−1</sub>) / Pob<sub>p,t−1</sub>.

Esta normalización (Saiz, 2007; González y Ortega, 2013) permite leer β como los **puntos porcentuales** adicionales de crecimiento del precio cuando llega un flujo neto equivalente al 1 % de la población. Si el aumento de población se trasladara uno a uno al precio, β ≈ 1. Por eso β es una semielasticidad de escala comparable con la literatura.

### 5.1 Armonización de frecuencias y periodo común

| Problema | Decisión |
|---|---|
| Distinta frecuencia: Padrón anual (stock a 1 de enero) frente a MIVAU trimestral | Precio anual = **media de los 4 trimestres** del año natural; los provincia-año sin los 4 trimestres se descartan. Robustez: precio del **4.º trimestre**. |
| Distinta fecha de referencia | El stock a 1/1/(t+1) se asigna al año t ("stock a final del año t"). Así, el flujo del año t = FB(1/1/t+1) − FB(1/1/t) es la variación ocurrida **durante** el año natural t, el mismo año en que se promedia el precio. Con el precio del 4.º trimestre la alineación es exacta (final de año). |
| Distintos periodos (Padrón 1/1/1998-1/1/2022; MIVAU 1995T1-2026) | Se usa solo la **ventana común**: años 1997-2021, es decir, Padrón 1/1/1998-1/1/2022 y precios 1997-2021. Los flujos y las variaciones de precio empiezan en 1998. |
| Ceros en el MIVAU | El MIVAU publica 0 cuando no difunde el dato (pocas tasaciones). Se tratan como **ausentes**: 17 trimestres, concentrados en 2011-2013 en provincias pequeñas, y 10 provincia-año descartados. Tratarlos como precios generaba variaciones anuales espurias de hasta ±138 %. |
| Duplicados en el MIVAU | 110 filas duplicadas exactas (serie de Navarra) eliminadas. |
| CCAA uniprovinciales | Madrid, Asturias, Murcia y Navarra solo aparecen como "Total CCAA" en el MIVAU: se asignan a su provincia. |
| Desglose cambiante de nacionalidades | Se conservan las 114 nacionalidades individuales con dato en todos los años. "Serbia y Montenegro" y "Serbia" se unen en una sola serie. Las categorías "Resto de…" van a un residuo "Otras" = total − suma de las conservadas. |
| Coherencia entre ficheros del INE | Comprobado: extranjeros (03006) = total de extranjeros (03005) en todas las celdas, y nacidos en España + nacidos en el extranjero = total. |

**Proporción frente a tamaño de la población.** Un flujo grande en una provincia grande no implica más presión relativa. Por eso, además del flujo normalizado por la población inicial, se estima el modelo con la **variación de la proporción** de nacidos en el extranjero (Δ % en p.p.) y en niveles con el **% de nacidos en el extranjero**. Ambas medidas no dependen del tamaño de la población.

### A. MCO agrupado
Δln P<sub>pt</sub> = α + β·m<sub>pt</sub> + X'<sub>pt</sub>γ + ε<sub>pt</sub>, con errores agrupados por provincia. Es una asociación bruta: no controla diferencias permanentes entre provincias ni el ciclo nacional.

### B. Panel con efectos fijos (modelo principal)
Δln P<sub>pt</sub> = β·m<sub>pt</sub> + X'<sub>pt</sub>γ + μ<sub>p</sub> + τ<sub>t</sub> + ε<sub>pt</sub>

- μ<sub>p</sub>: en un modelo en diferencias, recoge **tendencias** de precio propias de cada provincia.
- τ<sub>t</sub>: absorbe todo lo común a España en cada año. Esto incluye los tipos de interés, las condiciones de crédito, la fiscalidad estatal y la política monetaria del BCE. Por eso el tipo de interés solo entra en el MCO agrupado.
- Errores estándar agrupados por provincia (52 clusters), robustos a heterocedasticidad y a autocorrelación arbitraria dentro de cada provincia (Bertrand, Duflo y Mullainathan, 2004).
- Variantes: flujo retardado (t−1), retardos distribuidos 0-2 con efecto acumulado y su error estándar (combinación lineal de coeficientes), y niveles (ln P sobre % nacidos en el extranjero).
- Contrastes de Wald de significatividad conjunta de los controles y de los retardos del flujo.

### C. Variables instrumentales: shift-share (Bartik / Card)

Z<sub>pt</sub> = 100 · Σ<sub>n</sub> s<sub>n,p,t0</sub> · ΔN<sub>n,t</sub><sup>(−p)</sup> / Pob<sub>p,t−1</sub>

- s<sub>n,p,t0</sub>: proporción de los residentes de nacionalidad *n* en España que vivían en la provincia *p* en el año base *t0*.
- ΔN<sub>n,t</sub><sup>(−p)</sup>: variación nacional del stock de la nacionalidad *n* sin contar la provincia *p* (*leave-one-out*).

La idea es que los recién llegados se instalan donde ya hay redes de compatriotas (Altonji y Card, 1991; Card, 2001). Así, la parte del flujo que se explica por los *shocks* de origen (crisis en Ecuador, Rumanía, Venezuela, etc.) y por la geografía previa de los enclaves es plausiblemente ajena a los *shocks* locales de demanda de vivienda. González y Ortega (2013) aplican esta estrategia a las provincias españolas.

**Supuestos de identificación y riesgos.**

1. **Exogeneidad de las cuotas** (Goldsmith-Pinkham, Sorkin y Swift, 2020): la distribución de los enclaves en el año base no debe predecir *shocks* posteriores de precios por otras vías. Riesgo: los enclaves se formaron en provincias con un tipo concreto de actividad (agricultura intensiva, turismo, construcción) que tiene su propio ciclo inmobiliario. Mitigación: elegir el año base lo más temprano posible, añadir efectos fijos y comprobar si las cuotas iniciales están correlacionadas con las tendencias de precio previas.
2. **Exogeneidad de los shifts** (Borusyak, Hull y Jaravel, 2022): alternativa, válida si hay muchas nacionalidades con *shocks* independientes. Con pocas nacionalidades dominantes es difícil de sostener.
3. **Persistencia y ajuste dinámico** (Jaeger, Ruist y Stuhler, 2018): si las cuotas de origen son muy estables en el tiempo, el instrumento mezcla el impacto de los flujos actuales con el ajuste a flujos pasados.
4. **Inferencia** (Adão, Kolesár y Morales, 2019): las provincias con estructuras de origen parecidas comparten *shocks*. Los errores agrupados por provincia pueden infraestimar la incertidumbre.
5. **Fuerza del instrumento:** se reporta el estadístico de la primera etapa, robusto a cluster. Con un único instrumento equivale a un F. Si es menor que 10, el IV se considera débil y no se interpreta (Staiger y Stock, 1997; Stock y Yogo, 2005).
6. El instrumento se construye con **nacionalidad**, no con país de nacimiento, porque el Padrón desagrega así. Por eso se estima el 2SLS con ambos regresores endógenos.

### D. Robustez y diagnósticos
- Definición alternativa de inmigración (extranjeros).
- Sin controles.
- Exclusión de provincias atípicas (Madrid, Barcelona, Baleares, Las Palmas, S. C. de Tenerife, Ceuta, Melilla).
- Recorte de valores extremos del flujo (p1-p99).
- Subperiodos: expansión, crisis y recuperación.
- Variable dependiente en niveles.
- Exclusión de provincias de una en una (*leave-one-province-out*).
- Multicolinealidad: factores de inflación de la varianza (VIF).
- Autocorrelación: test de Wooldridge (2002) para paneles.

## 6. Variables de control

| Variable | Justificación | Fuente | Escala | Estado |
|---|---|---|---|---|
| ln PIB per cápita / crecimiento del PIB pc | Renta y demanda solvente de vivienda | Eurostat `nama_10r_3gdp` | Provincia | Implementada |
| Tasa de paro | Ciclo laboral; atrae o expulsa población | Eurostat `lfst_r_lfu3rt` (EPA) | **CCAA** | Implementada (escala CCAA) |
| ln densidad | Escasez de suelo y aglomeración | Eurostat `demo_r_d3area` + población | Provincia | Implementada |
| % población 25-34 | Edad de formación de hogares | Eurostat `demo_r_pjangrp3` | Provincia | Implementada |
| Viviendas terminadas por 1.000 hab. (t−1) | Oferta nueva; retardada por su endogeneidad | MIVAU | Provincia | Implementada (fichero manual opcional) |
| Tipo de interés a 10 años | Coste de financiación | Eurostat `irt_lt_mcby_a` | Nacional | Solo MCO agrupado (absorbido por τ<sub>t</sub>) |
| Salario medio | Capacidad de pago | AEAT, *Mercado de trabajo y pensiones en las fuentes tributarias* | Provincia | **No incorporada** (pendiente) |
| Renta de los hogares | Capacidad de pago | INE, *Atlas de distribución de renta de los hogares* (desde 2015) | Provincia/municipio | **No incorporada** (serie corta) |
| Stock de vivienda | Oferta acumulada | INE, Censos 2011 y 2021 | Provincia | **No incorporada** (solo años censales) |
| Actividad turística | Demanda no residencial | INE, Encuesta de Ocupación Hotelera (pernoctaciones) | Provincia | **No incorporada** (pendiente) |

**Controles «malos».** No se controla por el crecimiento de la población nativa ni por el empleo contemporáneo, porque pueden ser consecuencia de la inmigración. Condicionar en ellos sesgaría β (Angrist y Pischke, 2009).

## 7. Limitaciones conocidas

- El **valor tasado** no es un precio de transacción. Se suaviza respecto al mercado y depende de la composición de las viviendas tasadas. Lo ideal sería contrastarlo con el índice de precios del INE (IPV, por CCAA desde 2007) y con precios notariales o registrales.
- Los precios son **nominales**. Los efectos fijos de año absorben la inflación común, pero no las diferencias de inflación entre provincias.
- El flujo es **neto** y procede del Padrón. Infrarregistro, depuraciones por caducidad de inscripciones de extranjeros no comunitarios y cambios metodológicos (por ejemplo, la Estadística Continua de Población desde 2021) pueden generar saltos.
- La **escala provincial** mezcla mercados urbanos y rurales muy distintos y puede ocultar efectos dentro de la provincia (Accetturo et al., 2014).
- Con 52 provincias el número de clusters es moderado. Los p-valores con pocos clusters pueden ser optimistas (Cameron, Gelbach y Miller, 2008).
- La **versión municipal** no está implementada en esta versión.
