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
}
SNAP_PACKAGES = ["composition", "usage_augmentation_ratio_composition",
                 "usage_automation_ratio_composition",
                 "public_composition"]


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


def load_headline_uncertainty():
    """Les bootstrap-standardfeilen for KI-indeksen og returner nyeste
    vintage som en liten dict til dashboard.json. Standardfeilen gjelder
    den sesongjusterte hovedindeksen (spec 'sa'), som er den app.js viser
    som standard. Returnerer None hvis artefakten mangler, slik at
    nettsiden faller tilbake til aa vise indeksen uten baand."""
    if not os.path.exists(HEADLINE_SE_CSV):
        print("  headline_uncertainty: artefakt mangler, hopper over")
        return None
    df = pd.read_csv(HEADLINE_SE_CSV)
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

    out_dir = os.path.join(SITE_DIR, "public", "data")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "dashboard.json"), "w",
              encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    size = os.path.getsize(os.path.join(out_dir, "dashboard.json"))
    print(f"  dashboard.json: {size/1024:.0f} kB")

    # Kopier CSV-ene for nedlasting.
    dl_dir = os.path.join(out_dir, "releases", release)
    if os.path.exists(dl_dir):
        shutil.rmtree(dl_dir)
    shutil.copytree(os.path.join(REL_BASE, release), dl_dir)
    print(f"  nedlastbare filer -> data/releases/{release}/")
    print("Ferdig.")


if __name__ == "__main__":
    main()
