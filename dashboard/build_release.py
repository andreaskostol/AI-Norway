"""
build_release.py

Bygger en komplett datarelease for det norske Canaries-dashboardet, i
samme format som Stanford/ADP Canaries Dashboard (jf.
dashboard/canaries_dashboard_oversikt.md og malene i
data/stanford_canaries/2026-05/).

Datapakker under dashboard/releases/{RELEASE}/, hver med
tidsserie-CSV (+ yoy/annualized der relevant) og data dictionary.
Utvidelse mot Stanford: tidsseriene har en fasettkolonne `adjustment`
med verdiene raw / sa / percap / percap_sa; raw-radene alene
reproduserer deres skjema. Snapshot-pakkene (composition) bygger paa
raa headcount og har ingen varianter. I tillegg til sysselsetting
(Stanford-paritet) bygges nyansettelser (hires_*) og FTE-justert loenn
(wages_*) for hovedkuttene by_exposure, age_by_exposure og by_age, for
de fem yrkescasene og for usage_patterns_by_age. Loenn har bare
variantene raw/sa (per capita er ikke meningsfullt for loenn).
Yrkescase- og usage-figurene viser bare nivaaindeks paa nettsiden, saa
der faar nyansettelser derived=False (ingen yoy/annualized); det
haandterer ogsaa tynne celler med null nyansettelser i enkelte maaneder.

Kjoering:  python dashboard/build_release.py [RELEASE]
           (RELEASE default "2026-06"; pakkemapper som finnes fra foer
            hoppes over uendret -- releaser er uforanderlige vintages,
            men nye pakker kan legges til en eksisterende release)
"""

import os
import sys

import numpy as np
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(BASE_DIR, "microdata-output",
                    "09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv")
ELOUNDOU = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
USAGE = os.path.join(BASE_DIR, "data", "ai_exposure",
                     "styrk08_usage_groups.csv")
POP_SRC = os.path.join(BASE_DIR, "analysis", "output", "figure_data",
                       "fig_employment_by_age_quintile.csv")

RELEASE = sys.argv[1] if len(sys.argv) > 1 else "2026-06"
OUT_BASE = os.path.join(BASE_DIR, "dashboard", "releases", RELEASE)

BASE_MONTH = "2022-11-16"
BASE_OBS = "2022-11-01"
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"
ADJUSTMENTS = ["raw", "sa", "percap", "percap_sa"]
WAGE_ADJUSTMENTS = ["raw", "sa"]

AGE_LABELS = {"1": "21-30", "2": "31-40", "3": "41-50", "4": "51-60"}
AGE_ORDER = ["1", "2", "3", "4"]
EXP_LABELS = {1: "Quintile 1 (least exposed)", 2: "Quintile 2",
              3: "Quintile 3", 4: "Quintile 4",
              5: "Quintile 5 (most exposed)"}
USE_LABELS = {"No usage": "No usage", "Q1": "Quintile 1 (least usage)",
              "Q2": "Quintile 2", "Q3": "Quintile 3", "Q4": "Quintile 4",
              "Q5": "Quintile 5 (most usage)"}
USE_ORDER = ["No usage", "Q1", "Q2", "Q3", "Q4", "Q5"]

OCCUPATIONS = {
    "software_developers": ["2512", "2513", "2514", "2519"],
    "customer_service": ["4222"],
    "stock_clerks": ["4321"],
    "home_health_aides": ["5322"],
    "electricians": ["7411"],
}

DICT_CONVENTIONS = """## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  decade age groups 21-30, 31-40, 41-50, 51-60, monthly from 2021-01.
- The Canaries normalization date is `2022-11-01`; the Employment Index
  is 100 at that date for each series.
- `observation_date` is the first day of the observation month. The
  underlying register reference is the week containing the 16th.
- The canaries sample is the 397 STYRK-08 (= ISCO-08) occupation codes
  with an Eloundou et al. (2024) exposure score, quintiles
  equal-weighted by occupation.
- Time-series files carry an `adjustment` facet column not present in
  the Stanford files: `raw` (headcount, Stanford's method), `sa`
  (seasonally adjusted; X-11 core with factors estimated 2021-2024 and
  frozen), `percap` (headcount divided by the resident population of
  the age group, Statistics Norway table 07459), `percap_sa` (both).
  The `raw` rows alone reproduce the Stanford schema.
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates.
"""

DICT_CONVENTIONS_HIRES = """## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  decade age groups 21-30, 31-40, 41-50, 51-60, monthly from 2021-01.
- The series is the monthly number of new hires: jobs whose registered
  start date (ARBLONN_ARB_START) falls in the window between the
  previous and the current monthly reference date (the 16th). The
  normalization date is `2022-11-01`; the Hiring Index is 100 at that
  date for each series.
- `observation_date` is the first day of the observation month. The
  underlying register reference is the week containing the 16th.
- The canaries sample is the 397 STYRK-08 (= ISCO-08) occupation codes
  with an Eloundou et al. (2024) exposure score, quintiles
  equal-weighted by occupation.
- Time-series files carry an `adjustment` facet column: `raw` (hire
  count), `sa` (seasonally adjusted; X-11 core with factors estimated
  2021-2024 and frozen -- note that hiring is strongly seasonal, so
  prefer `sa` or year-over-year comparisons), `percap` (hires divided
  by the resident population of the age group, Statistics Norway
  table 07459), `percap_sa` (both).
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates.
"""

DICT_CONVENTIONS_WAGES = """## Conventions

- Norwegian counterpart to the Stanford/ADP Canaries Dashboard data
  packages, built from Norwegian register data (A-ordningen via
  microdata.no): the full population of private-sector employees,
  decade age groups 21-30, 31-40, 41-50, 51-60, monthly from 2021-01.
- The series is the FTE-adjusted average monthly cash wage of the
  group: sum(count x mean cash wage) / sum(count x mean contractual
  FTE share) over the occupation-by-age cells in the group, where
  cash wage is ARBLONN_LONN_KONTANT_IMP and the FTE share is
  ARBLONN_ARB_STILLINGSPST / 100. Each cell's average stillingsprosent
  thus weights its wage up to a full-time-equivalent level. The
  normalization date is `2022-11-01`; the Wage Index is 100 at that
  date for each series.
- Caveat: the FTE adjustment corrects for part-time work but not for
  partial first-month pay among new hires; that effect is small and
  seasonally stable.
- `observation_date` is the first day of the observation month. The
  underlying register reference is the week containing the 16th.
- The canaries sample is the 397 STYRK-08 (= ISCO-08) occupation codes
  with an Eloundou et al. (2024) exposure score, quintiles
  equal-weighted by occupation.
- Time-series files carry an `adjustment` facet column with the values
  `raw` (FTE-adjusted wage, not seasonally adjusted) and `sa`
  (seasonally adjusted; X-11 core with factors estimated 2021-2024 and
  frozen). The per-capita variants are not meaningful for wages and
  are not published.
- Annualized growth: (index/100)^(12/k) - 1, k = months since 2022-11,
  published from k = 6. Year-over-year: index_t/index_(t-12) - 1.
  Both stored as signed decimal rates. Wage indices are nominal; no
  deflation is applied.
"""


def seasonal_adjust(values, dates):
    """X-11-kjerne, frosne faktorer (jf. analysis/docs/sesongjustering.md).

    Robust mot nullmaaneder, som kan forekomme i tynne hires-celler:
    faktorene estimeres fra log av positive observasjoner (isfinite-maske,
    saa log(0) = -inf droppes), og en nullmaaned forblir null i den
    justerte serien. For serier uten nuller er dette identisk med foer.
    """
    s = pd.DataFrame({"date": dates, "value": values}).sort_values("date")
    est = s[(s["date"] >= SEAS_FROM) & (s["date"] <= SEAS_TO)]
    with np.errstate(divide="ignore"):
        y = np.log(est["value"].to_numpy())
    m = est["date"].str[5:7].astype(int).to_numpy()
    n = len(est)
    w = np.ones(13)
    w[0] = w[12] = 0.5
    w = w / 12.0
    ma = np.full(n, np.nan)
    for i in range(6, n - 6):
        ma[i] = (y[i - 6:i + 7] * w).sum()
    with np.errstate(invalid="ignore"):
        d = y - ma
    ok = np.isfinite(d)
    fac = np.array([d[ok & (m == mm)].mean() for mm in range(1, 13)])
    fac = fac - fac.mean()
    m_all = s["date"].str[5:7].astype(int).to_numpy()
    with np.errstate(divide="ignore"):
        return np.exp(np.log(s["value"].to_numpy()) - fac[m_all - 1])


def obs_date(d):
    return d.str[:8] + "01"


def variant_index(g, pop_key, pop, adjustments=ADJUSTMENTS):
    """Indeksvarianter (base = 100) for en (date, count)-serie.

    pop_key: aldersgruppe-streng, "all" for samlet, None for ingen
    percap-varianter (brukes ikke her). adjustments: hvilke varianter
    som bygges (loenn har bare raw/sa).
    """
    g = g.sort_values("date")
    out = {}
    for adj in adjustments:
        v = g["count"].to_numpy().astype(float)
        if adj.startswith("percap"):
            denom = np.array([pop[(d, pop_key)] for d in g["date"]])
            v = v / denom
        if adj.endswith("sa"):
            v = seasonal_adjust(v, g["date"])
        base = v[(g["date"] == BASE_MONTH).to_numpy()][0]
        out[adj] = pd.DataFrame({
            "observation_date": obs_date(g["date"]),
            "adjustment": adj,
            "value": np.round(100.0 * v / base, 2)})
    return pd.concat(out.values(), ignore_index=True)


def derive(wide, value_cols, facet_cols):
    """Yoy- og annualized-filer fra en indeks-widetabell."""
    w = wide.sort_values(facet_cols + ["observation_date"]) \
            .reset_index(drop=True)
    k = ((w["observation_date"].str[:4].astype(int) - 2022) * 12
         + w["observation_date"].str[5:7].astype(int) - 11)
    lag = w.groupby(facet_cols)[value_cols].shift(12)
    yoy = w.copy()
    ann = w.copy()
    for c in value_cols:
        yoy[c] = np.round(w[c] / lag[c] - 1, 4)
        ann[c] = np.round((w[c] / 100.0) ** (12.0 / k) - 1, 4)
    yoy = yoy[lag[value_cols[0]].notna().to_numpy()]
    ann = ann[(k >= 6).to_numpy()]
    return yoy, ann


def write_package(name, wide, value_cols, facet_cols, extra_dict,
                  derived=True, conventions=DICT_CONVENTIONS):
    pkg = f"canaries_no_{name}"
    d = os.path.join(OUT_BASE, pkg)
    if os.path.exists(d):
        print(f"  {pkg}: finnes fra foer, hoppes over (vintage)")
        return
    os.makedirs(d)
    wide.to_csv(os.path.join(d, f"{pkg}.csv"), index=False)
    files = [f"- `{pkg}.csv`: Underlying series."]
    if derived:
        yoy, ann = derive(wide, value_cols, facet_cols)
        yoy.to_csv(os.path.join(d, f"{pkg}_yoy_change.csv"), index=False)
        ann.to_csv(os.path.join(d, f"{pkg}_annualized.csv"), index=False)
        files += [f"- `{pkg}_yoy_change.csv`: Year-over-year change.",
                  f"- `{pkg}_annualized.csv`: Annualized growth."]
    files += [f"- `{pkg}_data_dictionary.md`: Documentation."]
    with open(os.path.join(d, f"{pkg}_data_dictionary.md"), "w",
              encoding="utf-8") as f:
        f.write(f"# {pkg} Data Dictionary\n\n## Files Included\n\n"
                + "\n".join(files) + "\n\n" + conventions
                + "\n" + extra_dict + "\n")
    print(f"  {pkg}: {len(wide)} rows")


def pivot_index(long, facet_cols, col_field, col_order):
    wide = long.pivot_table(index=["observation_date", "adjustment"]
                            + facet_cols, columns=col_field,
                            values="value").reset_index()
    return wide[["observation_date", "adjustment"] + facet_cols
                + [c for c in col_order if c in wide.columns]]


def main():
    os.makedirs(OUT_BASE, exist_ok=True)
    print(f"Release {RELEASE} -> {OUT_BASE}")

    d = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str,
                                 "sekt": int})
    d = d[(d["variable"] == "count") & (d["sekt"] == 2)
          & (d["alder_gr"].isin(AGE_ORDER))]
    el = pd.read_csv(ELOUNDOU, dtype={"styrk08": str})
    el = el[el["quintile"].notna()][["styrk08", "quintile"]]
    el["quintile"] = el["quintile"].astype(int)
    use = pd.read_csv(USAGE, dtype={"styrk08": str})
    d = d.merge(el, left_on="yrke4", right_on="styrk08")
    d = d.merge(use[["styrk08", "group_augmentation", "group_automation"]],
                on="styrk08")

    pop_src = pd.read_csv(POP_SRC, dtype={"age_group": str, "ai_q": str})
    pop_src = pop_src[(pop_src["sector"] == 2) & (pop_src["ai_q"] == "1")]
    pop_src["pop"] = pop_src["employment"] / pop_src["percap"]
    pop = pop_src.set_index(["date", "age_group"])["pop"].to_dict()
    for dt in pop_src["date"].unique():
        pop[(dt, "all")] = sum(pop[(dt, a)] for a in AGE_ORDER)

    def collect(df, facet_keys, pop_key_fn):
        rows = []
        for keys, g in df.groupby(facet_keys, observed=True):
            keys = keys if isinstance(keys, tuple) else (keys,)
            g = g.groupby("date", as_index=False)["value"].sum()
            g = g.rename(columns={"value": "count"})
            vi = variant_index(g, pop_key_fn(dict(zip(facet_keys, keys))),
                               pop)
            for k, v in zip(facet_keys, keys):
                vi[k] = v
            rows.append(vi)
        return pd.concat(rows, ignore_index=True)

    # 1. by_exposure: pooled aldre, kvintiler + composition_E-kolonner.
    long = collect(d, ["quintile"], lambda k: "all")
    long["col"] = long["quintile"].map(EXP_LABELS)
    wide = pivot_index(long, [], "col", list(EXP_LABELS.values()))
    comp = d.groupby(["date", "quintile"], as_index=False)["value"].sum()
    comp["share"] = np.round(100 * comp["value"]
                             / comp.groupby("date")["value"]
                             .transform("sum"), 2)
    comp_w = comp.pivot_table(index="date", columns="quintile",
                              values="share")
    comp_w.columns = [f"composition_E{q}" for q in comp_w.columns]
    comp_w.index = comp_w.index.str[:8] + "01"
    wide = wide.merge(comp_w, left_on="observation_date", right_index=True)
    write_package("by_exposure", wide, list(EXP_LABELS.values()),
                  ["adjustment"],
                  "Value columns: Employment Index per Eloundou exposure "
                  "quintile, all ages 21-60 pooled. `composition_E1..E5`: "
                  "each quintile's share of sample employment in percent, "
                  "from raw headcount (identical across adjustment rows).")

    # 2. age_by_exposure: fasett kvintil, verdikolonner aldersgrupper.
    long = collect(d, ["quintile", "alder_gr"],
                   lambda k: k["alder_gr"])
    long["exposure_quintile"] = long["quintile"].map(EXP_LABELS)
    long["col"] = long["alder_gr"].map(AGE_LABELS)
    wide = pivot_index(long, ["exposure_quintile"], "col",
                       list(AGE_LABELS.values()))
    write_package("age_by_exposure", wide, list(AGE_LABELS.values()),
                  ["adjustment", "exposure_quintile"],
                  "Facet `exposure_quintile`; value columns: Employment "
                  "Index per decade age group.")

    # 3. by_age: pooled kvintiler, verdikolonner aldersgrupper.
    long = collect(d, ["alder_gr"], lambda k: k["alder_gr"])
    long["col"] = long["alder_gr"].map(AGE_LABELS)
    wide = pivot_index(long, [], "col", list(AGE_LABELS.values()))
    write_package("by_age", wide, list(AGE_LABELS.values()),
                  ["adjustment"],
                  "Value columns: Employment Index per decade age group, "
                  "all canaries-sample occupations pooled.")

    # 4. composition: snapshot ved basismaaneden, raa headcount.
    base = d[d["date"] == BASE_MONTH]
    tot = base["value"].sum()
    comp = base.groupby(["alder_gr", "quintile"],
                        as_index=False)["value"].sum()
    comp["Share"] = np.round(100 * comp["value"] / tot, 4)
    comp["Age Group"] = comp["alder_gr"].map(AGE_LABELS)
    comp["Exposure Group"] = comp["quintile"].map(EXP_LABELS)
    comp["observation_date"] = BASE_OBS
    comp = comp[["observation_date", "Age Group", "Share",
                 "Exposure Group"]]
    write_package("composition", comp, [], [],
                  "Snapshot at the normalization date: each age-by-"
                  "exposure cell's share of total sample employment, in "
                  "percent (raw headcount). Sums to 100.", derived=False)

    # 5-8. Yrkescase: verdikolonner aldersgrupper.
    d_all = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str,
                                     "sekt": int})
    d_all = d_all[(d_all["variable"] == "count") & (d_all["sekt"] == 2)
                  & (d_all["alder_gr"].isin(AGE_ORDER))]
    for name, codes in OCCUPATIONS.items():
        occ = d_all[d_all["yrke4"].isin(codes)]
        long = collect(occ, ["alder_gr"], lambda k: k["alder_gr"])
        long["col"] = long["alder_gr"].map(AGE_LABELS)
        wide = pivot_index(long, [], "col", list(AGE_LABELS.values()))
        write_package(name, wide, list(AGE_LABELS.values()),
                      ["adjustment"],
                      f"Value columns: Employment Index per decade age "
                      f"group for STYRK-08 {'+'.join(codes)}. Per capita "
                      f"divides by the age group's total resident "
                      f"population.")

    # 9. usage_patterns_by_age: fasetter usage_pattern og age_bucket
    #    (inkl. All ages), verdikolonner bruksgrupper.
    rows = []
    for pat, gcol in [("Augmentation", "group_augmentation"),
                      ("Automation", "group_automation")]:
        long = collect(d, [gcol, "alder_gr"], lambda k: k["alder_gr"])
        long["age_bucket"] = long["alder_gr"].map(AGE_LABELS)
        la = collect(d, [gcol], lambda k: "all")
        la["age_bucket"] = "All ages"
        long = pd.concat([long, la], ignore_index=True)
        long["usage_pattern"] = pat
        long["col"] = long[gcol].map(USE_LABELS)
        rows.append(long)
    long = pd.concat(rows, ignore_index=True)
    wide = pivot_index(long, ["usage_pattern", "age_bucket"], "col",
                       [USE_LABELS[g] for g in USE_ORDER])
    write_package("usage_patterns_by_age", wide,
                  [USE_LABELS[g] for g in USE_ORDER],
                  ["adjustment", "usage_pattern", "age_bucket"],
                  "Occupations grouped by the share of the occupation's "
                  "Claude queries classified as augmentative/automative "
                  "(Handa et al. 2025 via styrk08_usage_groups.csv), "
                  "following BCC (2025) Figure 3. `No usage` = canaries-"
                  "sample occupations below the query threshold.")

    # 10-11. usage ratio composition snapshots.
    for pat, gcol in [("augmentation", "group_augmentation"),
                      ("automation", "group_automation")]:
        comp = base.groupby(["alder_gr", gcol],
                            as_index=False)["value"].sum()
        comp["Share"] = np.round(100 * comp["value"] / tot, 4)
        comp["Age Group"] = comp["alder_gr"].map(AGE_LABELS)
        comp["Usage Group"] = comp[gcol].map(USE_LABELS)
        comp["observation_date"] = BASE_OBS
        comp = comp[["observation_date", "Age Group", "Share",
                     "Usage Group"]]
        write_package(f"usage_{pat}_ratio_composition", comp, [], [],
                      "Snapshot at the normalization date: each age-by-"
                      "usage-group cell's share of total sample "
                      "employment, in percent (raw headcount).",
                      derived=False)

    # 12-17. Nyansettelser og FTE-justert loenn for hovedkuttene.
    #        Nyansettelser per celle = count * ny_jobb (andel med
    #        startdato i vinduet mellom forrige og gjeldende statusdato);
    #        loenn = sum(count*kontantlonn) / sum(count*stillingspst/100),
    #        dvs. cellens snittloenn vektet opp til fulltidsekvivalent
    #        med cellens gjennomsnittlige stillingsprosent.
    cw = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str,
                                  "sekt": int})
    cw = cw[(cw["sekt"] == 2) & (cw["alder_gr"].isin(AGE_ORDER))
            & cw["variable"].isin(["count", "kontantlonn",
                                   "stillingspst", "ny_jobb"])]
    cw = cw.pivot_table(index=["date", "yrke4", "alder_gr"],
                        columns="variable", values="value",
                        aggfunc="first").reset_index()
    assert not cw[["count", "kontantlonn", "stillingspst",
                   "ny_jobb"]].isna().any().any(), \
        "celler mangler en av variablene"
    cw = cw.merge(el, left_on="yrke4", right_on="styrk08")

    def agg_hires(g):
        s = g.assign(level=g["count"] * g["ny_jobb"]) \
             .groupby("date", as_index=False)["level"].sum()
        return s.rename(columns={"level": "count"})

    def agg_fte_wage(g):
        s = g.assign(num=g["count"] * g["kontantlonn"],
                     den=g["count"] * g["stillingspst"] / 100.0) \
             .groupby("date", as_index=False)[["num", "den"]].sum()
        s["count"] = s["num"] / s["den"]
        return s[["date", "count"]]

    def collect_outcome(df, facet_keys, pop_key_fn, agg, adjustments):
        rows = []
        for keys, g in df.groupby(facet_keys, observed=True):
            keys = keys if isinstance(keys, tuple) else (keys,)
            s = agg(g)
            assert (s["count"] >= 0).all(), f"negativ serie: {keys}"
            base = s.loc[s["date"] == BASE_MONTH, "count"]
            assert len(base) == 1 and base.iloc[0] > 0, \
                f"basismaaned ikke positiv: {keys}"
            vi = variant_index(s, pop_key_fn(dict(zip(facet_keys, keys))),
                               pop, adjustments)
            for k, v in zip(facet_keys, keys):
                vi[k] = v
            rows.append(vi)
        return pd.concat(rows, ignore_index=True)

    OUTCOME_SPECS = [
        ("hires", agg_hires, ADJUSTMENTS, DICT_CONVENTIONS_HIRES,
         "Hiring Index (number of new hires)"),
        ("wages", agg_fte_wage, WAGE_ADJUSTMENTS, DICT_CONVENTIONS_WAGES,
         "Wage Index (FTE-adjusted average monthly cash wage)"),
    ]

    # Hovedkutt by_exposure / age_by_exposure / by_age. Disse beholder
    # derived=True; oppsummerings-punktdiagrammet paa nettsiden bruker
    # hires_by_exposure/-age_by_exposure sin yoy_latest.
    for oname, agg_fn, adjs, conv, what in OUTCOME_SPECS:
        long = collect_outcome(cw, ["quintile"], lambda k: "all",
                               agg_fn, adjs)
        long["col"] = long["quintile"].map(EXP_LABELS)
        wide = pivot_index(long, [], "col", list(EXP_LABELS.values()))
        write_package(f"{oname}_by_exposure", wide,
                      list(EXP_LABELS.values()), ["adjustment"],
                      f"Value columns: {what} per Eloundou exposure "
                      "quintile, all ages 21-60 pooled.",
                      conventions=conv)

        long = collect_outcome(cw, ["quintile", "alder_gr"],
                               lambda k: k["alder_gr"], agg_fn, adjs)
        long["exposure_quintile"] = long["quintile"].map(EXP_LABELS)
        long["col"] = long["alder_gr"].map(AGE_LABELS)
        wide = pivot_index(long, ["exposure_quintile"], "col",
                           list(AGE_LABELS.values()))
        write_package(f"{oname}_age_by_exposure", wide,
                      list(AGE_LABELS.values()),
                      ["adjustment", "exposure_quintile"],
                      f"Facet `exposure_quintile`; value columns: {what} "
                      "per decade age group.", conventions=conv)

        long = collect_outcome(cw, ["alder_gr"], lambda k: k["alder_gr"],
                               agg_fn, adjs)
        long["col"] = long["alder_gr"].map(AGE_LABELS)
        wide = pivot_index(long, [], "col", list(AGE_LABELS.values()))
        write_package(f"{oname}_by_age", wide, list(AGE_LABELS.values()),
                      ["adjustment"],
                      f"Value columns: {what} per decade age group, all "
                      "canaries-sample occupations pooled.",
                      conventions=conv)

    # Yrkescase og bruksgrupper: samme to utfall per alder. Figurene viser
    # bare nivaaindeks (yoy brukes ikke der), saa nyansettelser faar
    # derived=False -- det unngaar ogsaa udefinert yoy i tynne celler med
    # nullmaaneder (4222/51-60 har null nyansettelser i juli 2023 og 2025).
    # Loenn har ingen nullmaaneder og beholder derived=True.
    cwu = cw.merge(use[["styrk08", "group_augmentation",
                        "group_automation"]], on="styrk08")
    for oname, agg_fn, adjs, conv, what in OUTCOME_SPECS:
        der = oname == "wages"
        for cname, codes in OCCUPATIONS.items():
            cwo = cw[cw["yrke4"].isin(codes)]
            long = collect_outcome(cwo, ["alder_gr"],
                                   lambda k: k["alder_gr"], agg_fn, adjs)
            long["col"] = long["alder_gr"].map(AGE_LABELS)
            wide = pivot_index(long, [], "col", list(AGE_LABELS.values()))
            write_package(f"{oname}_{cname}", wide,
                          list(AGE_LABELS.values()), ["adjustment"],
                          f"Value columns: {what} per decade age group for "
                          f"STYRK-08 {'+'.join(codes)}.",
                          derived=der, conventions=conv)

        rows = []
        for pat, gcol in [("Augmentation", "group_augmentation"),
                          ("Automation", "group_automation")]:
            long = collect_outcome(cwu, [gcol, "alder_gr"],
                                   lambda k: k["alder_gr"], agg_fn, adjs)
            long["age_bucket"] = long["alder_gr"].map(AGE_LABELS)
            la = collect_outcome(cwu, [gcol], lambda k: "all", agg_fn, adjs)
            la["age_bucket"] = "All ages"
            long = pd.concat([long, la], ignore_index=True)
            long["usage_pattern"] = pat
            long["col"] = long[gcol].map(USE_LABELS)
            rows.append(long)
        long = pd.concat(rows, ignore_index=True)
        wide = pivot_index(long, ["usage_pattern", "age_bucket"], "col",
                           [USE_LABELS[g] for g in USE_ORDER])
        write_package(f"{oname}_usage_patterns_by_age", wide,
                      [USE_LABELS[g] for g in USE_ORDER],
                      ["adjustment", "usage_pattern", "age_bucket"],
                      f"Facets `usage_pattern` and `age_bucket`; value "
                      f"columns: {what} per Claude-usage group (Handa et "
                      f"al. 2025 via styrk08_usage_groups.csv), following "
                      f"BCC (2025) Figure 3. `No usage` = canaries-sample "
                      f"occupations below the query threshold.",
                      derived=der, conventions=conv)

    print("Done.")


if __name__ == "__main__":
    main()
