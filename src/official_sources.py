"""
Lectores de los ficheros oficiales tal como se descargan de INEbase y del MIVAU, y su
conversión al esquema del proyecto (data/raw/manual/*.csv).

Ficheros soportados (guardar sin modificar en data/raw/manual/originales/):
- INE 03006: "Población por provincias, país de nacimiento, español/extranjero y sexo"
  (Estadística del Padrón Continuo, 1 de enero 1998-2022). CSV separado por ';'.
- INE 03005: "Población extranjera por nacionalidad, provincias y sexo" (mismo origen).
- MIVAU VDP006_01: "Valor tasado medio de vivienda libre y protegida" (€/m²), trimestral
  por provincia desde 1995.

ARMONIZACIÓN TEMPORAL (decisión documentada en docs/methodology.md §5.1):
- El Padrón mide stocks a 1 de enero. El stock a 1/1/(t+1) se asigna al año t
  ("stock a final del año t"). Así, el flujo del año t = FB(1/1/t+1) - FB(1/1/t) es la
  variación ocurrida DURANTE el año natural t, el mismo año en que se observan los precios.
- El precio anual es la media de los cuatro trimestres del año t (solo si están los cuatro).
  Como robustez se usa el precio del 4.º trimestre, que coincide con la fecha del stock.
- Periodo: se restringe a los años en que las tres fuentes tienen datos (ventana común).
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from . import config

log = logging.getLogger(__name__)

TIMING_SHIFT = -1  # anio = año de referencia del Padrón - 1 (stock a final de año)

# Comunidades uniprovinciales que el MIVAU publica solo como "Total CCAA"
MIVAU_UNIPROVINCIAL = {
    "Madrid, Comunidad de": "28",
    "Asturias, Principado de": "33",
    "Murcia, Region de": "30",
    "Navarra, Comunidad Foral de": "31",
}


# Nacionalidades que el INE renombra/desdobla en el periodo (se unen en una serie)
NATIONALITY_MERGE = {
    "Serbia y Montenegro (Antigua Yugoslavia)": "Serbia (incl. Serbia y Montenegro)",
    "Serbia": "Serbia (incl. Serbia y Montenegro)",
}


def _num(s: pd.Series) -> pd.Series:
    """'47.475.420' -> 47475420 ; '1.234,5' -> 1234.5 ; '..' o '' -> NaN."""
    s = s.astype(str).str.strip().replace({"..": None, "": None, ".": None, "nan": None})
    s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def _prov_code(s: pd.Series) -> pd.Series:
    """'02 Albacete' -> '02'; 'TOTAL ESPAÑA' -> NaN."""
    return s.astype(str).str.extract(r"^(\d{2})\s")[0]


def _read_ine(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str)


# --------------------------------------------------------------------------------------
# INE 03006: país de nacimiento
# --------------------------------------------------------------------------------------
def load_ine_03006(path: Path) -> pd.DataFrame:
    """Devuelve provincia_cod, anio_padron, poblacion_total, nacidos_extranjero,
    nacidos_espana, extranjeros_03006 (ambos sexos)."""
    d = _read_ine(path)
    d = d[d["Sexo"] == "Ambos sexos"].copy()
    d["provincia_cod"] = _prov_code(d["Provincias"])
    d = d.dropna(subset=["provincia_cod"])
    d["anio_padron"] = d["Periodo"].astype(int)
    d["valor"] = _num(d["Total"])
    pick = {
        ("TOTAL POBLACIÓN", "TOTAL"): "poblacion_total",
        ("NACIDOS EN EL EXTRANJERO", "TOTAL"): "nacidos_extranjero",
        ("NACIDOS EN ESPAÑA", "TOTAL"): "nacidos_espana",
        ("TOTAL POBLACIÓN", "Nacionalidad Extranjera"): "extranjeros_03006",
    }
    key = list(zip(d["País de Nacimiento"], d["Español/Extranjero"]))
    d["var"] = [pick.get(k) for k in key]
    d = d.dropna(subset=["var"])
    out = d.pivot_table(index=["provincia_cod", "anio_padron"], columns="var", values="valor",
                        aggfunc="first").reset_index()
    out.columns.name = None
    return out


# --------------------------------------------------------------------------------------
# INE 03005: nacionalidad
# --------------------------------------------------------------------------------------
def _is_aggregate(name: str) -> bool:
    """Agregados geográficos (TOTAL, continentes, UE...). APÁTRIDAS es una categoría propia."""
    if name == "APÁTRIDAS":
        return False
    return name.upper() == name or bool(re.match(r"^UE\(", name))


def load_ine_03005(path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (total_extranjeros, por_nacionalidad).

    Para el instrumento se conservan solo las nacionalidades individuales con dato en TODOS
    los años; el resto (nacionalidades que el INE desglosa solo en algunos años, 'Resto de...')
    se agrupa en 'Otras' como residuo = total - suma de las conservadas. Así se evitan saltos
    artificiales cuando el INE cambia el desglose (p. ej. Serbia y Montenegro -> Serbia).
    """
    d = _read_ine(path)
    d = d[d["Sexo"] == "Ambos sexos"].copy()
    d["provincia_cod"] = _prov_code(d["Provincias"])
    d = d.dropna(subset=["provincia_cod"])
    d["anio_padron"] = d["Periodo"].astype(int)
    d["poblacion"] = _num(d["Total"])

    total = (d[d["Nacionalidad"] == "TOTAL EXTRANJEROS"][["provincia_cod", "anio_padron", "poblacion"]]
             .rename(columns={"poblacion": "extranjeros"}))

    ind = d[~d["Nacionalidad"].map(_is_aggregate)].copy()
    # Cambios de desglose del INE: se unen en una serie continua
    ind["Nacionalidad"] = ind["Nacionalidad"].replace(NATIONALITY_MERGE)
    ind = ind.groupby(["provincia_cod", "anio_padron", "Nacionalidad"], as_index=False)["poblacion"].sum(min_count=1)
    years = d["anio_padron"].nunique()
    nat_years = ind.dropna(subset=["poblacion"]).groupby("Nacionalidad")["anio_padron"].nunique()
    keep = nat_years[nat_years == years].index
    keep = [n for n in keep if not n.startswith("Resto")]
    dropped = sorted(set(ind["Nacionalidad"]) - set(keep))
    log.info("Nacionalidades individuales conservadas: %d; agrupadas en 'Otras': %d", len(keep), len(dropped))
    k = ind[ind["Nacionalidad"].isin(keep)][["provincia_cod", "anio_padron", "Nacionalidad", "poblacion"]]
    k = k.fillna({"poblacion": 0})
    resid = (total.merge(k.groupby(["provincia_cod", "anio_padron"], as_index=False)["poblacion"].sum(),
                         on=["provincia_cod", "anio_padron"]))
    resid["poblacion"] = resid["extranjeros"] - resid["poblacion"]
    resid["Nacionalidad"] = "Otras"
    nat = pd.concat([k, resid[["provincia_cod", "anio_padron", "Nacionalidad", "poblacion"]]], ignore_index=True)
    nat = nat.rename(columns={"Nacionalidad": "nacionalidad"})
    nat.attrs["agrupadas_en_otras"] = dropped
    return total, nat


# --------------------------------------------------------------------------------------
# MIVAU VDP006_01: valor tasado
# --------------------------------------------------------------------------------------
def load_mivau_vdp006(path: Path, regimen: str = "Libre") -> pd.DataFrame:
    """Valor tasado trimestral (€/m²) por provincia. Las CCAA uniprovinciales se toman de las
    filas 'Total CCAA'. Se descartan el agregado 'Ceuta y Melilla' (hay series separadas
    desde 2004) y los totales de CCAA pluriprovinciales y nacional. Se eliminan duplicados
    exactos (presentes en la serie de Navarra)."""
    v = pd.read_csv(path, sep=";", encoding="utf-8-sig")
    v = v[v["Régimen"] == regimen].copy()
    v["provincia_cod"] = v["CPRO"].map(lambda x: f"{int(x):02d}" if pd.notna(x) else None)
    uni = (v["Provincia"] == "Total CCAA") & v["Comunidad_Autónoma"].isin(MIVAU_UNIPROVINCIAL)
    v.loc[uni, "provincia_cod"] = v.loc[uni, "Comunidad_Autónoma"].map(MIVAU_UNIPROVINCIAL)
    # El MIVAU publica 0 cuando no difunde el dato (pocas tasaciones): es un ausente, no un precio
    zeros = int((v["Valor"] == 0).sum())
    if zeros:
        log.info("MIVAU: %d valores = 0 tratados como ausentes (dato no publicado)", zeros)
    v.loc[v["Valor"] <= 0, "Valor"] = float("nan")
    v = v.dropna(subset=["provincia_cod", "Valor"])
    v = v.rename(columns={"Año": "anio", "Trimestre": "trimestre", "Valor": "precio_m2"})
    v = v[["provincia_cod", "anio", "trimestre", "precio_m2"]]
    n0 = len(v)
    v = v.drop_duplicates()
    if len(v) < n0:
        log.info("MIVAU: %d filas duplicadas exactas eliminadas", n0 - len(v))
    if v.duplicated(["provincia_cod", "anio", "trimestre"]).any():
        raise ValueError("MIVAU: provincia-trimestre con valores distintos duplicados")
    return v.sort_values(["provincia_cod", "anio", "trimestre"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Conversión al esquema del proyecto
# --------------------------------------------------------------------------------------
def convert_official_files(f03006: Path, f03005: Path, fvdp: Path, out_dir: Path = config.RAW_MANUAL) -> dict:
    """Lee los tres ficheros oficiales, aplica la armonización temporal y la ventana común,
    comprueba la coherencia entre fuentes y escribe los CSV del esquema del proyecto."""
    out_dir.mkdir(parents=True, exist_ok=True)
    pob = load_ine_03006(f03006)
    ext_tot, nat = load_ine_03005(f03005)
    precios = load_mivau_vdp006(fvdp)
    dropped = list(nat.attrs.get("agrupadas_en_otras", []))

    # Coherencia: extranjeros de 03006 y 03005 deben coincidir
    chk = pob.merge(ext_tot, on=["provincia_cod", "anio_padron"], how="inner")
    rel = (chk["extranjeros_03006"] - chk["extranjeros"]).abs() / chk["extranjeros"]
    max_rel = float(rel.max())
    if max_rel > 0.001:
        log.warning("Discrepancia extranjeros 03006 vs 03005: máx. %.4f %%", 100 * max_rel)
    # Coherencia: nacidos España + extranjero = total
    gap = (pob["nacidos_espana"] + pob["nacidos_extranjero"] - pob["poblacion_total"]).abs().max()

    # Armonización temporal: stock 1/1/(t+1) -> año t
    pob["anio"] = pob["anio_padron"] + TIMING_SHIFT
    ext_tot["anio"] = ext_tot["anio_padron"] + TIMING_SHIFT
    nat["anio"] = nat["anio_padron"] + TIMING_SHIFT

    # Ventana común a las tres fuentes
    y_ine = set(pob["anio"]) & set(ext_tot["anio"]) & set(nat["anio"])
    y_price = set(precios["anio"])
    common = sorted(y_ine & y_price)
    a, b = common[0], common[-1]
    pob = pob[pob["anio"].between(a, b)]
    nat = nat[nat["anio"].between(a, b)]
    precios = precios[precios["anio"].between(a, b)]

    inm = pob.merge(ext_tot[["provincia_cod", "anio", "extranjeros"]], on=["provincia_cod", "anio"], how="left")
    inm[["provincia_cod", "anio", "anio_padron", "nacidos_extranjero", "extranjeros", "poblacion_total"]].to_csv(
        out_dir / "poblacion_inmigrante.csv", index=False)
    nat[["provincia_cod", "anio", "nacionalidad", "poblacion"]].to_csv(out_dir / "extranjeros_nacionalidad.csv", index=False)
    precios.to_csv(out_dir / "precio_vivienda.csv", index=False)

    info = {
        "ventana_comun": (a, b),
        "padron_fechas": (f"1/1/{a + 1}", f"1/1/{b + 1}"),
        "max_discrepancia_extranjeros_03006_03005_pct": round(100 * max_rel, 5),
        "max_desfase_nacidos_suma_total": float(gap),
        "nacionalidades_individuales": int(nat["nacionalidad"].nunique() - 1),
        "nacionalidades_agrupadas_en_otras": dropped,
        "filas_precio_trimestrales": int(len(precios)),
    }
    return info


if __name__ == "__main__":
    import argparse
    import json
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Convierte ficheros oficiales INE/MIVAU al esquema del proyecto")
    p.add_argument("--ine03006", default=str(config.RAW_MANUAL / "originales" / "ine_03006_pais_nacimiento.csv"))
    p.add_argument("--ine03005", default=str(config.RAW_MANUAL / "originales" / "ine_03005_nacionalidad.csv"))
    p.add_argument("--mivau", default=str(config.RAW_MANUAL / "originales" / "mivau_VDP006_01.csv"))
    a = p.parse_args()
    print(json.dumps(convert_official_files(Path(a.ine03006), Path(a.ine03005), Path(a.mivau)),
                     ensure_ascii=False, indent=2))
