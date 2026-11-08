|                        | (1) EF misma muestra   | (2) 2SLS (flujo extranjeros)   | (3) 2SLS (flujo nacidos ext.)   | (4) Forma reducida   |
|:-----------------------|:-----------------------|:-------------------------------|:--------------------------------|:---------------------|
| flujo_extranjeros      | 1.1040***              | 0.4428                         |                                 |                      |
| flujo_extranjeros (ee) | (0.2433)               | (0.4698)                       |                                 |                      |
| flujo_nacidos_ext      |                        |                                | 0.4712                          |                      |
| flujo_nacidos_ext (ee) |                        |                                | (0.4987)                        |                      |
| iv_shift_share         |                        |                                |                                 | 0.3420               |
| iv_shift_share (ee)    |                        |                                |                                 | (0.3772)             |
| Variable dependiente   | dln_precio             | dln_precio                     | dln_precio                      | dln_precio           |
| Efectos fijos          | provincia + año        | provincia + año                | provincia + año                 | provincia + año      |
| Errores estándar       | cluster provincia      | cluster provincia              | cluster provincia               | cluster provincia    |
| Observaciones          | 1216                   | 1216                           | 1216                            | 1216                 |
| Provincias             | 52                     | 52                             | 52                              | 52                   |
| R² (within si EF)      | 0.129                  | 0.836                          | 0.836                           | 0.031                |
| F primera etapa        |                        | 48.59                          | 47.78                           |                      |

Errores estándar entre paréntesis. *** p<0.01, ** p<0.05, * p<0.10. Errores agrupados por provincia salvo indicación contraria. Instrumento: shift-share con cuotas por nacionalidad en 1997 (leave-one-out).
