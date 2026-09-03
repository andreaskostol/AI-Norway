"""
prepare_data.py

Konverterer siste datarelease (dashboard/releases/<RELEASE>/) til en
kompakt JSON for nettsiden (site/public/data/dashboard.json) og kopierer
release-CSV-ene til site/public/data/releases/<RELEASE>/ for nedlasting.

Kjoering:  python dashboard/site/prepare_data.py [RELEASE]
           (default: siste mappe under dashboard/releases/)
"""

import json
import os
import shutil
import sys

import pandas as pd

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
DASH_DIR = os.path.dirname(SITE_DIR)
REL_BASE = os.path.join(DASH_DIR, "releases")
REPO_DIR = os.path.dirname(DASH_DIR)
# Okkupasjons-klynge-bootstrap av KI-indeksen (standardfeil per vintage),
# produsert av analysis/06_figures/recursive_kiindeks_headline.py. Siste
# rad = nyeste vintage; svarer til den sesongjusterte (sa) hovedindeksen.
HEADLINE_SE_CSV = os.path.join(
    REPO_DIR, "analysis", "output", "coefficients",
    "coef_recursive_kiindeks_headline.csv")
# Samme bootstrap for Mouchel-kvintilene (recursive_kiindeks_headline.py
# mouchel), til maalvelgeren paa nettsiden.
HEADLINE_SE_CSV_BY_MEASURE = {
    "eloundou": HEADLINE_SE_CSV,
    "mouchel": os.path.join(REPO_DIR, "analysis", "output", "coefficients",
                            "coef_recursive_kiindeks_headline_mouchel.csv"),
}

ADJUSTMENTS = ["raw", "sa", "percap", "percap_sa"]

# Tidsseriepakker: pakkenavn -> (fasettkolonner, verdikolonner-ordnet)
TS_PACKAGES = {
    "by_exposure": ([], None),
    "age_by_exposure": (["exposure_quintile"], None),
    "by_age": ([], None),
    "software_developers": ([], None),
    "customer_service": ([], None),
    "electricians": ([], None),
    "home_health_aides": ([], None),
    "usage_patterns_by_age": (["usage_pattern", "age_bucket"], None),
    "hires_by_exposure": ([], None),
    "hires_age_by_exposure": (["exposure_quintile"], None),
    "hires_by_age": ([], None),
    "wages_by_exposure": ([], None),
    "wages_age_by_exposure": (["exposure_quintile"], None),
    "wages_by_age": ([], None),
    # Yrkescase (figur 5-8) og KI-bruk (figur 10) for nyansettelser
    # og loenn, slik at disse figurene ogsaa foelger utfallsvelgeren.
    "hires_software_developers": ([], None),
    "hires_customer_service": ([], None),
    "hires_electricians": ([], None),
    "hires_home_health_aides": ([], None),
    "wages_software_developers": ([], None),
    "wages_customer_service": ([], None),
    "wages_electricians": ([], None),
    "wages_home_health_aides": ([], None),
    "hires_usage_patterns_by_age": (["usage_pattern", "age_bucket"], None),
    "wages_usage_patterns_by_age": (["usage_pattern", "age_bucket"], None),
    # Offentlig sektor (release 2026-09): hovedkuttene 1-3 for alle tre
    # utfall, som egne public_-pakker. Kvintilene er de samme nasjonale
    # Eloundou-kvintilene, men yrkessammensetningen innen hver kvintil er
    # en annen enn i privat sektor, saa nivaaene skal ikke sammenlignes
    # paa tvers av sektor (jf. data dictionary). Vises i egen seksjon.
    "public_by_exposure": ([], None),
    "public_age_by_exposure": (["exposure_quintile"], None),
    "public_by_age": ([], None),
    "public_hires_by_exposure": ([], None),
    "public_hires_age_by_exposure": (["exposure_quintile"], None),
    "public_hires_by_age": ([], None),
    "public_wages_by_exposure": ([], None),
    "public_wages_age_by_exposure": (["exposure_quintile"], None),
    "public_wages_by_age": ([], None),
    # Maalvelgeren (release 2026-09): hovedkuttene by_exposure og
    # age_by_exposure med kvintiler fra Mouchel et al. (2026) i stedet
    # for Eloundou, for alle tre utfall. Samme struktur som motstykkene,
    # saa app.js bytter bare pakkeprefiks ("mouchel_").
    "mouchel_by_exposure": ([], None),
    "mouchel_age_by_exposure": (["exposure_quintile"], None),
    "mouchel_hires_by_exposure": ([], None),
    "mouchel_hires_age_by_exposure": (["exposure_quintile"], None),
    "mouchel_wages_by_exposure": ([], None),
    "mouchel_wages_age_by_exposure": (["exposure_quintile"], None),
}
SNAP_PACKAGES = ["composition", "usage_augmentation_ratio_composition",
                 "usage_automation_ratio_composition",
                 "public_composition"]
# Yrkesvelgeren (figur 9): de lange yrkespakkene skrives til en egen
# fil, public/data/occupations.json, slik at dashboard.json ikke vokser
# med ~95 000 tall. Noekkel = utfall slik app.js bruker det.
OCC_PACKAGES = {"employment": "occupations", "wages": "wages_occupations"}
# Engelske yrkesnavn for /en/: SSBs offisielle engelske STYRK-08-navn
# (Klass API, klassifikasjon 7, language=en), lagret i repoet med to
# manuelle rettelser (2221 Specialist nurses, 2267 Occupational
# therapists). STYRK-08 avviker fra ISCO-08 for enkelte koder, saa
# ISCO-titler kan ikke brukes direkte.
OCC_TITLES_EN = os.path.join(REPO_DIR, "data", "ai_exposure",
                             "styrk08_names_en.csv")


def load_ts(release, name, facets):
    pkg = f"canaries_no_{name}"
    path = os.path.join(REL_BASE, release, pkg, f"{pkg}.csv")
    df = pd.read_csv(path, dtype={"observation_date": str})
    meta_cols = ["observation_date", "adjustment"] + facets
    value_cols = [c for c in df.columns
                  if c not in meta_cols and not c.startswith("composition_")]
    comp_cols = [c for c in df.columns if c.startswith("composition_")]
    dates = sorted(df["observation_date"].unique())
    # Loenn publiseres bare som raw/sa; bruk variantene som finnes.
    adjustments = [a for a in ADJUSTMENTS
                   if a in set(df["adjustment"].unique())]

    out = {"value_cols": value_cols, "dates": dates, "series": {}}

    def key(facet_vals):
        return "|".join(facet_vals) if facet_vals else "_"

    for adj in adjustments:
        sub = df[df["adjustment"] == adj]
        out["series"][adj] = {}
        if facets:
            for fv, g in sub.groupby(facets):
                fv = fv if isinstance(fv, tuple) else (fv,)
                g = g.set_index("observation_date").reindex(dates)
                out["series"][adj][key(list(fv))] = {
                    c: [None if pd.isna(v) else round(float(v), 2)
                        for v in g[c]] for c in value_cols}
        else:
            g = sub.set_index("observation_date").reindex(dates)
            out["series"][adj][key([])] = {
                c: [None if pd.isna(v) else round(float(v), 2)
                    for v in g[c]] for c in value_cols}

    if comp_cols:
        g = df[df["adjustment"] == "raw"].set_index(
            "observation_date").reindex(dates)
        out["composition"] = {
            c: [None if pd.isna(v) else round(float(v), 2) for v in g[c]]
            for c in comp_cols}

    # Siste maaned av yoy- og annualized-filene (til oppsummeringer).
    for suffix, field in [("_yoy_change", "yoy_latest"),
                          ("_annualized", "ann_latest")]:
        path = os.path.join(REL_BASE, release, pkg, f"{pkg}{suffix}.csv")
        if not os.path.exists(path):
            continue
        ydf = pd.read_csv(path, dtype={"observation_date": str})
        last = ydf["observation_date"].max()
        ylast = ydf[ydf["observation_date"] == last]
        out[field] = {"date": last, "series": {}}
        for adj in adjustments:
            sub = ylast[ylast["adjustment"] == adj]
            out[field]["series"][adj] = {}
            for _, row in sub.iterrows():
                fk = key([str(row[f]) for f in facets])
                out[field]["series"][adj][fk] = {
                    c: (None if pd.isna(row[c]) else round(float(row[c]), 4))
                    for c in value_cols}
    return out


def load_snapshot(release, name):
    pkg = f"canaries_no_{name}"
    path = os.path.join(REL_BASE, release, pkg, f"{pkg}.csv")
    df = pd.read_csv(path)
    group_col = [c for c in df.columns
                 if c not in ("observation_date", "Age Group", "Share")][0]
    return {
        "group_col": group_col,
        "rows": [{"age": r["Age Group"], "group": r[group_col],
                  "share": round(float(r["Share"]), 4)}
                 for _, r in df.iterrows()],
    }


def build_download_manifest(release):
    """Hvilke nedlastbare filer som faktisk finnes per pakke, slik at
    nettsiden ikke lager doede lenker (case-pakkene for nyansettelser
    mangler f.eks. _yoy_change/_annualized)."""
    base = os.path.join(REL_BASE, release)
    manifest = {}
    for d in sorted(os.listdir(base)):
        if not d.startswith("canaries_no_") or \
                not os.path.isdir(os.path.join(base, d)):
            continue
        name = d[len("canaries_no_"):]
        files = set(os.listdir(os.path.join(base, d)))
        kinds = [k for k, fn in [
            ("csv", f"{d}.csv"),
            ("yoy_change", f"{d}_yoy_change.csv"),
            ("annualized", f"{d}_annualized.csv"),
            ("data_dictionary", f"{d}_data_dictionary.md")]
            if fn in files]
        manifest[name] = kinds
    return manifest


def load_occupations(release):
    """Les de lange yrkespakkene (en rad per maaned x justering x yrke)
    og pakk dem om til en liste av yrker med tallrekker per utfall og
    justering. Returnerer None hvis pakkene mangler i releasen, slik at
    eldre releaser fortsatt kan bygges."""
    out = {"release": release, "dates": None, "occupations": []}
    occ = {}
    titles_en = {}
    if os.path.exists(OCC_TITLES_EN):
        t = pd.read_csv(OCC_TITLES_EN, dtype=str)
        titles_en = dict(zip(t["styrk08"].str.zfill(4), t["name_en"]))
    for outcome, name in OCC_PACKAGES.items():
        pkg = f"canaries_no_{name}"
        path = os.path.join(REL_BASE, release, pkg, f"{pkg}.csv")
        if not os.path.exists(path):
            print(f"  {pkg}: mangler, occupations.json hoppes over")
            return None
        df = pd.read_csv(path, dtype={"styrk08": str,
                                      "observation_date": str})
        value_col = [c for c in df.columns if c.endswith("Index")][0]
        dates = sorted(df["observation_date"].unique())
        if out["dates"] is None:
            out["dates"] = dates
        assert dates == out["dates"], "ulik datoakse i yrkespakkene"
        for (code, label), g in df.groupby(["styrk08", "occupation"],
                                           sort=True):
            if code not in occ:
                q = g["exposure_quintile"].iloc[0]
                # "Quintile 5 (most exposed)" -> 5; tom -> None
                quint = (None if pd.isna(q)
                         else int(str(q).split()[1]))
                occ[code] = {"code": code, "name": label,
                             "name_en": titles_en.get(code),
                             "quintile": quint,
                             "n_base": int(g["n_base"].iloc[0])}
            occ[code][outcome] = {}
            for adj in ["raw", "sa"]:
                sub = g[g["adjustment"] == adj].set_index(
                    "observation_date").reindex(dates)
                occ[code][outcome][adj] = [
                    None if pd.isna(v) else round(float(v), 2)
                    for v in sub[value_col]]
    out["occupations"] = [occ[c] for c in sorted(occ)]
    missing = [c for c in sorted(occ) if not occ[c]["name_en"]]
    if missing:
        print(f"  ADVARSEL: {len(missing)} yrker mangler engelsk navn: "
              f"{missing}")
    return out


def load_headline_uncertainty(path=HEADLINE_SE_CSV):
    """Les bootstrap-standardfeilen for KI-indeksen og returner nyeste
    vintage som en liten dict til dashboard.json. Standardfeilen gjelder
    den sesongjusterte hovedindeksen (spec 'sa'), som er den app.js viser
    som standard. Returnerer None hvis artefakten mangler, slik at
    nettsiden faller tilbake til aa vise indeksen uten baand."""
    if not os.path.exists(path):
        print(f"  headline_uncertainty: {os.path.basename(path)} mangler, "
              "hopper over")
        return None
    df = pd.read_csv(path)
    last = df.iloc[-1]  # nyeste vintage = siste rad
    ki = float(last["ki"])
    se = float(last["se"])
    # Baandet regnes som ki +/- 1.96*se, samme metode som Appendix-
    # figuren i artikkelen (fig:recursive_kiindeks) beskriver: "+/-1.96
    # occupation cluster-bootstrap standard errors". CSV-kolonnene
    # ci_lo/ci_hi er persentil-bootstrap og brukes bevisst IKKE, slik at
    # nettsidens intervall er identisk med det artikkelen rapporterer.
    return {
        "spec": "sa",
        "vintage": str(last["cutoff"]),  # siste maaned, f.eks. "2026-02"
        "ki": round(ki, 3),
        "se": round(se, 3),
        "ci_lo": round(ki - 1.96 * se, 3),
        "ci_hi": round(ki + 1.96 * se, 3),
    }


def main():
    releases = sorted(d for d in os.listdir(REL_BASE)
                      if os.path.isdir(os.path.join(REL_BASE, d)))
    release = sys.argv[1] if len(sys.argv) > 1 else releases[-1]
    print(f"Forbereder data fra release {release}")

    data = {"release": release, "base_month": "2022-11-01",
            "packages": {}, "snapshots": {}}
    for name, (facets, _) in TS_PACKAGES.items():
        data["packages"][name] = load_ts(release, name, facets)
        data["packages"][name]["facets"] = facets
        print(f"  {name}: {len(data['packages'][name]['dates'])} mnd")
    for name in SNAP_PACKAGES:
        data["snapshots"][name] = load_snapshot(release, name)
        print(f"  {name}: snapshot")
    data["download_files"] = build_download_manifest(release)
    data["headline_uncertainty"] = load_headline_uncertainty()
    # Per maal (maalvelgeren): app.js slaar opp paa state.measure og
    # skjuler baandet for maal uten bootstrap.
    data["headline_uncertainty_by_measure"] = {
        m: load_headline_uncertainty(path)
        for m, path in HEADLINE_SE_CSV_BY_MEASURE.items()}

    out_dir = os.path.join(SITE_DIR, "public", "data")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "dashboard.json"), "w",
              encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(os.path.join(out_dir, "dashboard.json"))
    print(f"  dashboard.json: {size/1024:.0f} kB")

    # Yrkesvelgeren: egen fil, hentes av app.js etter dashboard.json.
    occ = load_occupations(release)
    if occ is not None:
        with open(os.path.join(out_dir, "occupations.json"), "w",
                  encoding="utf-8") as f:
            json.dump(occ, f, ensure_ascii=False, separators=(",", ":"))
        size = os.path.getsize(os.path.join(out_dir, "occupations.json"))
        print(f"  occupations.json: {len(occ['occupations'])} yrker, "
              f"{size/1024:.0f} kB")

    # Kopier CSV-ene for nedlasting.
    dl_dir = os.path.join(out_dir, "releases", release)
    if os.path.exists(dl_dir):
        shutil.rmtree(dl_dir)
    shutil.copytree(os.path.join(REL_BASE, release), dl_dir)
    print(f"  nedlastbare filer -> data/releases/{release}/")
    print("Ferdig.")


if __name__ == "__main__":
    main()
