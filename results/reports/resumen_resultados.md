# Resumen de resultados (generado automáticamente)

Muestra: 52 provincias, años 1997-2021. Observaciones en el modelo principal: 1216.
Controles incluidos: NINGUNO (solo efectos fijos de provincia y año; los controles económicos de Eurostat no estaban disponibles en esta ejecución).

## Modelo principal (efectos fijos de provincia y año, errores agrupados por provincia)

- Coeficiente del flujo de población nacida en el extranjero: 1.201 (IC 95 %: 0.693 a 1.709; p = 0.000).
- Interpretación: un aumento neto de residentes nacidos en el extranjero equivalente al 1 % de la población de la provincia se asocia con una variación de 1.20 puntos porcentuales en el crecimiento anual del precio de la vivienda, condicionada a los efectos fijos de provincia y año (y a los controles, si los hay).
- MCO agrupado sin efectos fijos: 5.485. La diferencia con el modelo principal indica qué parte de la correlación bruta se debe a diferencias permanentes entre provincias y al ciclo nacional común.
- Con la variación de la **proporción** de nacidos en el extranjero (p.p.) como regresor, que no depende del tamaño de la población: 1.548 (IC 95 %: 0.952 a 2.143; p = 0.000).
- Efecto acumulado (retardos 0-2): 1.145 (IC 95 %: 0.429 a 1.860; p = 0.002).
- H2 (efecto acumulado mayor que el contemporáneo): compatible con los datos.
- Especificación en niveles: +1 p.p. en el peso de la población nacida en el extranjero se asocia con un 0.88 % de variación del precio (IC 95 %: -0.01 % a 1.76 %).

## Variables instrumentales (shift-share)

- 2SLS: 0.471 (IC 95 %: -0.506 a 1.449; p = 0.345). Estadístico de primera etapa (Wald robusto a cluster, equivalente a F con un instrumento) = 47.78.
- El instrumento no parece débil según la regla F > 10, pero su validez depende de la exogeneidad de las cuotas iniciales (ver docs/methodology.md).
- Comparación: efectos fijos en la misma muestra con el flujo de extranjeros = 1.104; 2SLS con el flujo de extranjeros = 0.443. Forma reducida: 0.342 (IC 95 %: -0.398 a 1.082; p = 0.365).

## Robustez

- 7 de 11 especificaciones presentan p < 0.05. Rango de coeficientes de flujo: -0.334 a 1.548.
- Por especificación: Principal: 1.201 (p = 0.000); Def. alternativa: extranjeros: 1.104 (p = 0.000); Regresor: Δ proporción nacidos ext. (p.p.): 1.548 (p = 0.000); Precio 4.º trimestre (alineado con Padrón): 1.197 (p = 0.000); Sin provincias atípicas: 1.191 (p = 0.000); Sin outliers (p1-p99): 1.345 (p = 0.000); Subperiodo: expansión (hasta 2007): 0.602 (p = 0.059); Subperiodo: crisis (2008-2013): -0.334 (p = 0.571); Subperiodo: recuperación (2014 en adelante): 1.522 (p = 0.001); Niveles: ln precio ~ % nacidos ext.: 0.009 (p = 0.051); 2SLS shift-share (nacidos ext.): 0.471 (p = 0.345).
- Excluyendo provincias de una en una, el coeficiente varía entre 1.130 y 1.363.
- Test de Wooldridge de autocorrelación: p = 0.000.
- VIF máximo: 1.00.

## Advertencia sobre causalidad

Los coeficientes de MCO y efectos fijos son asociaciones condicionales. Solo la estimación IV aspira a una interpretación causal, y únicamente si se cumplen sus supuestos de identificación, que no pueden contrastarse de forma directa.
