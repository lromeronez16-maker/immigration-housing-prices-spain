# Datos

```
data/
├── raw/                 # Datos originales, sin modificar
│   ├── eurostat/        # Descarga automática (+ .meta.json de procedencia)
│   ├── ine/             # Tablas del INE vía API (+ .meta.json)
│   ├── mitma/           # Ficheros originales del MIVAU/MITMA
│   └── manual/          # Ficheros convertidos al esquema del proyecto (ver abajo)
│       └── originales/  # Copias intactas de las descargas manuales (xlsx, csv, px)
└── processed/
    └── panel_provincial.csv   # Generado por src/data_cleaning.py (no editar a mano)
```

**Este repositorio no incluye todavía datos reales.** No se han simulado ni incluido observaciones haciéndolas pasar por reales. Los datos sintéticos de `src/synthetic.py` solo se usan para los tests y para el modo demo, y nunca se guardan en esta carpeta.

## Paso 1: descarga automática

```bash
python -m src.data_collection
```

Descarga los controles de Eurostat y muestra qué ficheros manuales faltan.

## Paso 2: ficheros manuales (esquema obligatorio)

Hay plantillas con las cabeceras en `data/raw/manual/plantillas/`. `provincia_cod` es el código INE de provincia de dos dígitos (`01`…`52`).

| Fichero | Columnas | Unidad | Obligatorio |
|---|---|---|---|
| `poblacion_inmigrante.csv` | `provincia_cod, anio, nacidos_extranjero, extranjeros[, poblacion_total]` | personas a 1 de enero | Sí |
| `precio_vivienda.csv` | `provincia_cod, anio[, trimestre], precio_m2` | €/m², valor tasado vivienda libre | Sí |
| `extranjeros_nacionalidad.csv` | `provincia_cod, anio, nacionalidad, poblacion` | personas a 1 de enero | Solo para el IV |
| `viviendas_terminadas.csv` | `provincia_cod, anio, viviendas_terminadas` | viviendas | No |

Dónde descargar cada uno: `docs/data_sources.md`.

El cargador comprueba las columnas, los tipos y los códigos de provincia, y detiene la ejecución con un mensaje claro si algo no cuadra.

## Paso 3: construir el panel

```bash
python -m src.run_pipeline --skip-download
```
