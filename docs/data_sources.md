# Fuentes de datos

Todas las fuentes son oficiales. Cada fichero descargado automáticamente se acompaña de un `.meta.json` con la URL, la fecha y hora de descarga (UTC), los filtros aplicados y el hash SHA-256. Los ficheros manuales deben guardarse sin modificar en `data/raw/manual/originales/`, y la versión convertida al esquema del proyecto en `data/raw/manual/` (ver `data/README.md`).

## Ficheros usados en la versión actual

| Fichero original (`data/raw/manual/originales/`) | Organismo / tabla | Cobertura | Convertido a |
|---|---|---|---|
| `ine_03006_pais_nacimiento.csv` | INE, Padrón Continuo, tabla 03006 (provincia × país de nacimiento × español/extranjero × sexo) | 1/1/1998 - 1/1/2022 | `poblacion_inmigrante.csv` |
| `ine_03005_nacionalidad.csv` | INE, Padrón Continuo, tabla 03005 (extranjeros por nacionalidad × provincia × sexo) | 1/1/1998 - 1/1/2022 | `extranjeros_nacionalidad.csv` y el total de extranjeros |
| `mivau_VDP006_01.csv` | MIVAU, valor tasado medio de vivienda libre y protegida (€/m²), trimestral | 1995T1 - 2026 | `precio_vivienda.csv` (solo vivienda **libre**) |

Los dos ficheros del INE (95 MB y 22 MB) no se suben a GitHub por tamaño. Sus `.meta.json` guardan el SHA-256 para verificar que una nueva descarga es idéntica. La conversión se hace con `python -m src.official_sources`; los detalles de armonización están en `docs/methodology.md` §5.1.

## Descarga automática (`python -m src.data_collection`)

| Fichero | Dataset | Organismo | Contenido | Escala |
|---|---|---|---|---|
| `pib_nuts3.csv` | [`nama_10r_3gdp`](https://ec.europa.eu/eurostat/databrowser/view/nama_10r_3gdp/default/table) | Eurostat | PIB a precios corrientes, millones de € | NUTS-3 (provincia/isla) |
| `poblacion_nuts3.csv` | [`demo_r_pjanaggr3`](https://ec.europa.eu/eurostat/databrowser/view/demo_r_pjanaggr3/default/table) | Eurostat | Población a 1 de enero | NUTS-3 |
| `poblacion_edad_nuts3.csv` | [`demo_r_pjangrp3`](https://ec.europa.eu/eurostat/databrowser/view/demo_r_pjangrp3/default/table) | Eurostat | Población por grupos quinquenales de edad | NUTS-3 |
| `superficie_nuts3.csv` | [`demo_r_d3area`](https://ec.europa.eu/eurostat/databrowser/view/demo_r_d3area/default/table) | Eurostat | Superficie (km²) | NUTS-3 |
| `paro_nuts2.csv` | [`lfst_r_lfu3rt`](https://ec.europa.eu/eurostat/databrowser/view/lfst_r_lfu3rt/default/table) | Eurostat (EPA) | Tasa de paro 15-74 | NUTS-2 (CCAA) |
| `tipo_interes_lp.csv` | [`irt_lt_mcby_a`](https://ec.europa.eu/eurostat/databrowser/view/irt_lt_mcby_a/default/table) | Eurostat | Rendimiento de la deuda a 10 años | España |

Notas:
- Baleares y Canarias aparecen por islas en NUTS-3. Se agregan a provincia sumando las islas. Los códigos antiguos (`ES530`, `ES701`, `ES702`) solo se usan cuando no hay códigos nuevos para ese año.
- La tasa de paro solo existe en Eurostat por CCAA. Se asigna a cada provincia el valor de su comunidad. Una alternativa provincial es la EPA del INE (tabla de tasas de paro por provincia), que puede descargarse con `--ine <id>`.
- Los códigos de los datasets son los vigentes en noviembre de 2026. Si Eurostat los renombra, la descarga fallará con un mensaje explícito y los demás datasets se descargarán igualmente.

## API del INE (opcional, automática si se conoce el identificador)

`python -m src.data_collection --ine <id>` descarga cualquier tabla de INEbase por su identificador: es el número `t=` en la URL `https://www.ine.es/jaxiT3/Tabla.htm?t=<id>`. Usa el servicio JSON `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/<id>?tip=AM` y `ine_json_to_long()` lo aplana a formato largo.

**No se fijan identificadores de tabla en el código** porque no se han verificado desde el entorno de desarrollo, que no tenía acceso a ine.es. Deben consultarse en INEbase.

## Descarga manual (obligatoria)

### 1. Población nacida en el extranjero y población extranjera → `poblacion_inmigrante.csv`

- **Organismo:** INE. *Estadística del Padrón Continuo* (datos a 1 de enero, desde 1998).
- **Ruta en INEbase:** Demografía y población → Padrón. Población por municipios → Estadística del Padrón Continuo → Datos provinciales.
  - Tabla de población por **país de nacimiento** (España / extranjero), provincias y sexo → `nacidos_extranjero` (Total sexos, nacidos en el extranjero) y `poblacion_total` (Total).
  - Tabla de población por **nacionalidad** (española / extranjera), provincias y sexo → `extranjeros`.
- **Cuidado:** desde 2021-2022 el INE difunde la *Estadística Continua de Población* (ECP), que tiene otra metodología. No deben mezclarse ECP y Padrón en la misma serie sin documentarlo.

### 2. Precio de la vivienda → `precio_vivienda.csv`

- **Organismo:** Ministerio de Vivienda y Agenda Urbana (MIVAU; antes Ministerio de Fomento / MITMA). Estadística de **Valor tasado de la vivienda libre** (€/m²), trimestral, por provincias, desde 1995.
- **Acceso:** web del MIVAU → Estadísticas → Vivienda y actuaciones urbanas → Precio de la vivienda / Valor tasado. La serie histórica por provincias se descarga en Excel.
- **Conversión:** una fila por provincia y trimestre (`provincia_cod, anio, trimestre, precio_m2`). El pipeline calcula la media anual solo cuando hay los 4 trimestres.
- **Alternativas para robustez:** INE, Índice de Precios de Vivienda (IPV; por CCAA, desde 2007); Consejo General del Notariado (Portal Estadístico, precio €/m² por provincia); Colegio de Registradores (Estadística Registral Inmobiliaria).

### 3. Extranjeros por nacionalidad → `extranjeros_nacionalidad.csv` (necesario para el IV)

- **Organismo:** INE, Estadística del Padrón Continuo. Tabla de población extranjera por **nacionalidad** (país), provincias y sexo.
- **Recomendación:** usar el año disponible más antiguo (1998-2001) como año base del instrumento. Conservar las nacionalidades individuales; no usar solo los agregados continentales.

### 4. Viviendas terminadas (opcional) → `viviendas_terminadas.csv`

- **Organismo:** MIVAU. Estadística de **Vivienda libre** (viviendas terminadas, a partir de los certificados de fin de obra), anual por provincias.

## Datos no disponibles o no incorporados

| Variable deseada | Situación |
|---|---|
| Salario medio provincial | Existe en AEAT (*Mercado de trabajo y pensiones en las fuentes tributarias*); no incorporado en esta versión |
| Renta de los hogares | INE, *Atlas de distribución de renta de los hogares*, solo desde 2015; no incorporado |
| Stock de vivienda | Solo en años censales (2001, 2011, 2021); no incorporado |
| Turismo | INE, Encuesta de Ocupación Hotelera, pernoctaciones por provincia; no incorporado |
| Flujos brutos de inmigración | INE, Estadística de Migraciones; no incorporado |
| Precios municipales | MIVAU publica el valor tasado de municipios de más de 25.000 habitantes; versión municipal no implementada |
