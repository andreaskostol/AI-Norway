"""
build_data.py

Builds the data files for the data-pipeline animations: the real series at every stage from raw
cells to the indexed figure. The animation reads only these files, so the slides render without
the microdata files.

Two variants, one file each:
  data/pipeline-data.js         all ages 21-60 pooled (the headline index)
  data/pipeline-data-young.js   age group 21-30 on its own (the young index, "Alder x KI-eksponering")

Stages (same recipe as dashboard/build_release.py, adjustment "percap_sa"):
  1. cells     count of private-sector employees per STYRK-08 occupation x
               decade age group x month, kpos extract
  2. sum       sum of cells within each Eloundou exposure quintile
  3. pc        sum divided by resident population in the age range (SSB, quarterly)
  4. sa        pc with frozen X-11 seasonal factors removed (est. 2021-2024), per quintile series
  5. idx       sa indexed to November 2022 = 100

Also checks each final index series against the newest dashboard release and prints the headline
number by the formula in dashboard/site/public/app.js.

Usage (from anywhere):
    python slides/data-pipeline/build_data.py                    # up to the newest dashboard release
    python slides/data-pipeline/build_data.py --through latest   # every month in the newest file
    python slides/data-pipeline/build_data.py --through 2026-04  # a specific last month
"""

import glob                                   # pick the newest parsed kpos file
import json                                   # write the data payload
import os                                     # path handling
import sys                                    # console encoding on Windows

import numpy as np                            # seasonal-factor maths
import pandas as pd                           # data handling

sys.stdout.reconfigure(encoding="utf-8")      # Norwegian characters in the console

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

EXPOSURE = os.path.join(REPO, "data", "ai_exposure", "styrk08_eloundou_beta_mapping.csv")
CODES = os.path.join(REPO, "data", "ai_exposure", "styrk08_codes.csv")
POP = os.path.join(REPO, "data", "macro", "ssb_population_by_age_quarterly.csv")
RELEASES = os.path.join(REPO, "dashboard", "releases")

BASE_MONTH = "2022-11-16"                     # index = 100 here (as on kiindeksen.no)
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"   # factor-estimation window (frozen)
AGES = ["1", "2", "3", "4"]                   # decade age groups 21-30 ... 51-60
AGE_LABELS = {"1": "21–30", "2": "31–40", "3": "41–50", "4": "51–60"}

# Cells shown as named lines. First one is the cell the raw-data table opens with.
# Chosen to span the level range (about 150 to 66 000) and four of the five quintiles.
NAMED = [("2512", "1"), ("7411", "2"), ("5223", "1"), ("2163", "1")]
TABLE_MONTHS = 12                             # rows shown in the raw-data table

# The site's headline: growth of the trailing 3-month mean, last month vs. reference month
HEADLINE_REF = "2022-10-01"
HEADLINE_MA = 3

# One animation per variant: all ages pooled (the headline index), and the 21-30 group on its own.
VARIANTS = [
    {"key": "all", "ages": AGES, "pop_range": (21, 60), "label": "21–60",
     "named": NAMED, "out": "pipeline-data.js", "var": "PIPELINE_DATA", "pkg": "by_exposure"},
    {"key": "young", "ages": ["1"], "pop_range": (21, 30), "label": "21–30",
     "named": [("2512", "1"), ("7411", "1"), ("5223", "1"), ("2163", "1")],
     "out": "pipeline-data-young.js", "var": "PIPELINE_DATA_YOUNG", "pkg": "age_by_exposure"},
]

SRC = [None]                                  # path of the cell file, for the meta block


def newest_kpos():
    """Newest parsed kpos extract (same family the dashboard and figure scripts read)."""
    files = sorted(glob.glob(os.path.join(REPO, "microdata-output",
                                          "09_occ_agedecade_sektor_kpos_*_parsed.csv")))
    if not files:
        raise SystemExit("Fant ingen 09_occ_agedecade_sektor_kpos_*_parsed.csv i microdata-output")
    return files[-1]


def seasonal_adjust(values, dates):
    """X-11 core with frozen factors (copy of dashboard/build_release.py).

    Returns the adjusted series, the 12 log factors, and two full-length arrays (NaN outside
    the estimation window): the log trend (centred 2x12 moving average) and the log deviation
    from it, which the animation shows step by step.
    """
    s = pd.DataFrame({"date": dates, "value": values}).sort_values("date")
    in_win = ((s["date"] >= SEAS_FROM) & (s["date"] <= SEAS_TO)).to_numpy()
    est = s[in_win]
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
        adj = np.exp(np.log(s["value"].to_numpy()) - fac[m_all - 1])
    ma_full = np.full(len(s), np.nan)
    d_full = np.full(len(s), np.nan)
    ma_full[in_win] = ma
    d_full[in_win] = d
    return adj, fac, ma_full, d_full


def read_codes():
    """Occupation names by 4-digit STYRK-08 code (the file is cp1252)."""
    c = pd.read_csv(CODES, dtype=str, encoding="cp1252")
    c = c[c["level"] == "4"]
    return dict(zip(c["code"], c["name"]))


def moving_average(values, k):
    """Trailing mean with partial windows at the start, rounded to 2 decimals (as app.js)."""
    out = []
    for i in range(len(values)):
        win = values[max(0, i - k + 1):i + 1]
        out.append(np.floor(100 * np.mean(win) + 0.5) / 100)
    return out


def release_pkg(name):
    """Newest dashboard release's package csv (e.g. 'by_exposure'), or None."""
    for rd in sorted(glob.glob(os.path.join(RELEASES, "*")), reverse=True):
        f = os.path.join(rd, f"canaries_no_{name}", f"canaries_no_{name}.csv")
        if os.path.exists(f):
            return f
    return None


def release_index(pkg, n_m, ages):
    """The dashboard's percap_sa index per quintile for this variant, shape (5, months), or None."""
    f = release_pkg(pkg)
    if f is None:
        return None, None
    r = pd.read_csv(f)
    r = r[r["adjustment"] == "percap_sa"]
    if pkg == "by_exposure":
        r = r.set_index("observation_date")
        cols = [c for c in r.columns if c.startswith("Quintile")]
        arr = r[cols].to_numpy().T
    else:                                                   # age_by_exposure, column "21-30"
        col = AGE_LABELS[ages[0]].replace("–", "-")
        arr = np.array([r[r["exposure_quintile"].str.startswith(f"Quintile {q}")]
                        .sort_values("observation_date")[col].to_numpy() for q in range(1, 6)])
    return f, (arr if arr.shape[1] == n_m else None)


def build(d0, v):
    """Build one variant's data file from the shared, filtered cell data d0."""
    d = d0[d0["alder_gr"].isin(v["ages"])]
    dates = sorted(d["date"].unique())                     # "YYYY-MM-16"
    months = [x[:7] for x in dates]
    n_m = len(dates)
    names = read_codes()
    print(f"\n== {v['key']} ({v['label']}) ==")

    # ---- 1. cells ----
    wide = d.pivot_table(index=["quintile", "yrke4", "alder_gr"], columns="date",
                         values="value", aggfunc="sum").reindex(columns=dates)
    cells = wide.reset_index()
    cell_q = cells["quintile"].astype(int).tolist()
    cell_occ = cells["yrke4"].tolist()
    cell_age = [int(a) for a in cells["alder_gr"]]
    cell_v = [[None if pd.isna(x) else int(x) for x in row]
              for row in cells[dates].to_numpy()]
    n_cells = len(cells)

    named = []
    for occ, age in v["named"]:
        idx = int(cells.index[(cells["yrke4"] == occ) & (cells["alder_gr"] == age)][0])
        named.append({"cell": idx, "occ": occ, "age": AGE_LABELS[age],
                      "name": names.get(occ, occ), "q": cell_q[idx]})

    # ---- raw-data table: first rows of the first named cell, as they sit in the file ----
    a_occ, a_age = v["named"][0]
    rows = (d[(d["yrke4"] == a_occ) & (d["alder_gr"] == a_age)]
            .sort_values("date").head(TABLE_MONTHS))
    table = {"cell": named[0]["cell"],
             "rows": [[r.date, r.yrke4, int(r.alder_gr), int(r.sekt), int(r.value)]
                      for r in rows.itertuples()]}

    # ---- 2. sum per quintile ----
    qsum = (d.groupby(["quintile", "date"])["value"].sum().unstack("date")
            .reindex(columns=dates))
    qsum = qsum.sort_index()

    # ---- 3. per capita (resident population in the age range, quarterly, repeated per month) ----
    lo, hi = v["pop_range"]
    p = pd.read_csv(POP)
    p = p[(p["age"] >= lo) & (p["age"] <= hi)].groupby("date")["population"].sum()
    pop = np.array([p[f"{x[:4]}-Q{(int(x[5:7]) - 1) // 3 + 1}"] for x in dates], dtype=float)
    pc = qsum.to_numpy() / pop                              # share of the population

    # ---- 4. seasonally adjusted, 5. indexed ----
    sa, fac, trend, dev = [], [], [], []
    for k in range(5):
        a, f, ma, d_ = seasonal_adjust(pc[k], dates)
        sa.append(a)
        fac.append(f)
        trend.append(100 * np.exp(ma))                      # trend in percent of the population
        dev.append(100 * (np.exp(d_) - 1))                  # deviation from trend in percent
    sa = np.array(sa)
    base_i = dates.index(BASE_MONTH)
    idx = np.round(100.0 * sa / sa[:, [base_i]], 2)         # rounded as in the release CSVs

    # ---- check against the newest dashboard release ----
    f_rel, arr = release_index(v["pkg"], n_m, v["ages"])
    if f_rel is None:
        check = {"against": None, "max_abs_diff": None}
    elif arr is None:
        check = {"against": os.path.relpath(f_rel, REPO), "max_abs_diff": "ikke sammenlignbar"}
    else:
        check = {"against": os.path.relpath(f_rel, REPO),
                 "max_abs_diff": float(np.abs(arr - idx).max())}
    print("Kontroll mot dashboard:", check)

    # ---- headline by the site's formula (reference Oct 2022, trailing 3-month mean) ----
    ref_i = [x[:7] + "-01" for x in dates].index(HEADLINE_REF)
    g = []
    for k in (0, 4):                                        # Q1 and Q5
        sm = moving_average(list(idx[k]), HEADLINE_MA)
        g.append(100 * (sm[-1] / sm[ref_i] - 1))
    headline = {"g1": round(float(g[0]), 2), "g5": round(float(g[1]), 2),
                "rel": round(float(100 * ((1 + g[1] / 100) / (1 + g[0] / 100) - 1)), 2),
                "ref": HEADLINE_REF[:7], "last": months[-1]}
    print("Hovedtall (nettstedets formel):", headline)

    data = {
        "meta": {"source": os.path.basename(SRC[0]), "nRows": int(len(d)),
                 "nOcc": int(d["yrke4"].nunique()), "nCells": n_cells,
                 "nAges": len(v["ages"]), "ageLabel": v["label"], "variant": v["key"],
                 "first": months[0], "last": months[-1], "ref": BASE_MONTH[:7],
                 "seasFrom": SEAS_FROM[:7], "seasTo": SEAS_TO[:7],
                 "chatgptMonth": "2022-11"},
        "months": months,
        "cells": {"q": cell_q, "occ": cell_occ, "age": cell_age, "v": cell_v},
        "named": named,
        "table": table,
        "sum": [[int(x) for x in row] for row in qsum.to_numpy()],
        "pop": [int(x) for x in pop],
        "pc": np.round(100 * pc, 3).tolist(),               # percent of the population
        "sa": np.round(100 * np.array([s_ for s_ in sa]), 3).tolist(),
        "idx": idx.tolist(),
        "fac": np.round(100 * (np.exp(np.array(fac)) - 1), 3).tolist(),   # percent
        "trend": [[None if np.isnan(x) else round(float(x), 3) for x in row] for row in trend],
        "dev": [[None if np.isnan(x) else round(float(x), 3) for x in row] for row in dev],
        "headline": headline,
        "check": check,
    }
    out = os.path.join(HERE, "data", v["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(f"window.{v['var']} = ")
        json.dump(data, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print(f"Skrev {os.path.relpath(out, REPO)} ({os.path.getsize(out) / 1024:.0f} kB)")
    print(f"{n_cells} serier, {data['meta']['nOcc']} yrker, {n_m} måneder, {len(d):,} rader")


def main():
    SRC[0] = newest_kpos()
    print("Kilde:", os.path.relpath(SRC[0], REPO))
    d = pd.read_csv(SRC[0], dtype={"yrke4": str, "alder_gr": str, "sekt": int})
    d = d[(d["variable"] == "count") & (d["sekt"] == 2) & d["alder_gr"].isin(AGES)]

    # By default stop at the last month of the newest dashboard release, so the final
    # figure matches kiindeksen.no. Pass --through latest to use every month in the file.
    arg = sys.argv[sys.argv.index("--through") + 1] if "--through" in sys.argv else None
    rel = release_pkg("by_exposure")
    if arg is None and rel is not None:
        arg = pd.read_csv(rel)["observation_date"].max()[:7]
    if arg not in (None, "latest"):
        d = d[d["date"].str[:7] <= arg]
        print("Avgrenset til og med", arg)

    el = pd.read_csv(EXPOSURE, dtype={"styrk08": str})
    el = el[el["quintile"].notna()][["styrk08", "quintile"]]
    el["quintile"] = el["quintile"].astype(int)
    d = d.merge(el, left_on="yrke4", right_on="styrk08")

    for v in VARIANTS:
        build(d, v)


if __name__ == "__main__":
    main()
