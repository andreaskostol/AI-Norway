"""
build_yagan_ratio.py

Companion to build_figure_data.py. Same cell-level aggregations, but the
reference baseline for each (sector, age_group, ai_q) series is the MEAN
over a 12-month pre-window — either pre-ChatGPT or pre-agentic — instead
of the single reference month (2022-10-16) used by build_figure_data.py.

For each anchor we attach BOTH Yagan relative outcomes:

  *_diff_<anchor>  = y_{c,t} - mean(y_{c, pre})    same unit as y
                                                   (Yagan eq. (2),
                                                    Fig. 4A / 4C / Tab. 2)
  *_ratio_<anchor> = y_{c,t} / mean(y_{c, pre})    unitless, 1 = baseline
                                                   (Yagan Fig. 6B)

Two anchors, each with its own 12-month pre-window:
  chatgpt12 : pre = 2021m11 .. 2022m10  (12 months ending the month
              before ChatGPT's 30 Nov 2022 release)
  agentic12 : pre = 2024m05 .. 2025m04  (12 months ending the agentic
              k=-1 reference used by analysis-indiv/scripts/6e+7c)

Outputs:
  fig_employment_by_age_quintile_yagan.csv
    date, sector, age_group, ai_q, employment, percap,
    emp_diff_chatgpt12, emp_ratio_chatgpt12,
    emp_diff_agentic12, emp_ratio_agentic12
  fig_fte_by_age_quintile_yagan.csv
    date, sector, age_group, ai_q, fte, percap,
    fte_diff_chatgpt12, fte_ratio_chatgpt12,
    fte_diff_agentic12, fte_ratio_agentic12
  fig_outcomes_by_age_quintile_yagan.csv
    date, sector, age_group, ai_q, variable, value,
    value_diff_chatgpt12, value_ratio_chatgpt12,
    value_diff_agentic12, value_ratio_agentic12
  fig_selected_occ_by_age_yagan.csv
    date, occ_group, age_group, count, percap,
    emp_diff_chatgpt12, emp_ratio_chatgpt12,
    emp_diff_agentic12, emp_ratio_agentic12

Diff columns are in the same unit as the underlying outcome:
  emp_diff_*, fte_diff_* : per-capita employment-rate pp (since percap is a
                            share of the cohort population)
  value_diff_*           : NOK for kontantlonn/timelonn, pp for
                            stillingspst, hours for overtid_timer,
                            share-point for ny_jobb (raw variable units)

Usage:
    python analysis/04_timeseries/build_yagan_ratio.py
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
PARSED = os.path.join(BASE_DIR, "microdata-output",
                      "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv")
EXP_FILE = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
POP_FILE = os.path.join(BASE_DIR, "data", "macro",
                        "ssb_population_by_age_quarterly.csv")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "figure_data")

# 12-month pre-windows. Endpoints are inclusive; status-day in the parsed
# file is the 16th, so each YYYY-MM-16 row is one month.
ANCHORS = {
    "chatgpt12": ("2021-11-16", "2022-10-16"),
    "agentic12": ("2024-05-16", "2025-04-16"),
}

AGE_KEEP = ["1", "2", "3", "4"]
DECADE_RANGES = {"1": (21, 30), "2": (31, 40), "3": (41, 50), "4": (51, 60)}
OUTCOME_VARS = ["kontantlonn", "timelonn", "stillingspst",
                "overtid_timer", "ny_jobb"]


def load_pop():
    p = pd.read_csv(POP_FILE)
    out = {}
    for code, (lo, hi) in DECADE_RANGES.items():
        s = (p[(p["age"] >= lo) & (p["age"] <= hi)]
             .groupby("date")["population"].sum())
        for qd, val in s.items():
            out[(code, qd)] = val
    return out


def yq(datestr):
    y, m, _ = datestr.split("-")
    return f"{y}-Q{(int(m) - 1) // 3 + 1}"


def add_per_capita(df, value_col, pop):
    df = df.copy()
    df["percap"] = [v / pop[(str(a), yq(d))]
                    for v, a, d in zip(df[value_col],
                                        df["age_group"], df["date"])]
    return df


def add_yagan_baseline(df, value_col, group_cols, out_prefix):
    """For each anchor, attach both Yagan-style relative outcomes:

      <out_prefix>_diff_<anchor>  = value_col - mean(value_col over pre)
      <out_prefix>_ratio_<anchor> = value_col / mean(value_col over pre)

    Diff is Yagan (2020) eq. (2) (same unit as y); ratio is the Yagan
    Fig. 6B normalization (unitless, 1 = baseline). Pre is the inclusive
    month interval ANCHORS[anchor]; the mean is taken within each group
    (group_cols) over rows whose date falls in that pre-window.
    """
    df = df.copy()
    for anchor, (lo, hi) in ANCHORS.items():
        in_pre = df["date"].between(lo, hi)
        base = (df[in_pre].groupby(group_cols, dropna=False)[value_col]
                .mean()
                .rename("_base"))
        df = df.merge(base, left_on=group_cols, right_index=True, how="left")
        df[f"{out_prefix}_diff_{anchor}"]  = df[value_col] - df["_base"]
        df[f"{out_prefix}_ratio_{anchor}"] = df[value_col] / df["_base"]
        df = df.drop(columns="_base")
    return df


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    df = pd.read_csv(PARSED, dtype={"yrke4": str, "alder_gr": str})
    df = df[df["alder_gr"].isin(AGE_KEEP)]

    exp = pd.read_csv(EXP_FILE, dtype={"styrk08": str})
    exp = exp[exp["quintile"].notna()][["styrk08", "quintile"]]
    exp = exp.rename(columns={"styrk08": "yrke4"})
    exp["ai_q"] = exp["quintile"].astype(int)
    df = df.merge(exp[["yrke4", "ai_q"]], on="yrke4", how="inner")

    counts = (df[df["variable"] == "count"]
              [["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]]
              .rename(columns={"value": "count"}))

    pop = load_pop()

    # ---- Employment by age x quintile (+ pooled 'all') ----
    by_q = (counts.groupby(["date", "sekt", "alder_gr", "ai_q"],
                           as_index=False)["count"].sum())
    by_q["ai_q"] = by_q["ai_q"].astype(str)
    by_all = (counts.groupby(["date", "sekt", "alder_gr"],
                             as_index=False)["count"].sum())
    by_all["ai_q"] = "all"
    emp = pd.concat([by_q, by_all], ignore_index=True)
    emp = emp.rename(columns={"sekt": "sector", "alder_gr": "age_group",
                              "count": "employment"})
    emp = add_per_capita(emp, "employment", pop)
    emp = add_yagan_baseline(emp, "percap",
                          ["sector", "age_group", "ai_q"], "emp")
    emp = emp.sort_values(["sector", "age_group", "ai_q", "date"])
    emp_path = os.path.join(OUT_DIR,
                            "fig_employment_by_age_quintile_yagan.csv")
    emp.to_csv(emp_path, index=False)
    print(f"Wrote {emp_path} ({len(emp):,} rows)")

    # ---- FTE-employment by age x quintile ----
    stp = (df[df["variable"] == "stillingspst"]
           [["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]]
           .rename(columns={"value": "stillingspst"}))
    fte_cell = counts.merge(stp,
                            on=["date", "yrke4", "alder_gr", "sekt", "ai_q"],
                            how="inner")
    fte_cell["fte"] = fte_cell["count"] * fte_cell["stillingspst"]

    by_q_fte = (fte_cell.groupby(["date", "sekt", "alder_gr", "ai_q"],
                                 as_index=False)["fte"].sum())
    by_q_fte["ai_q"] = by_q_fte["ai_q"].astype(str)
    by_all_fte = (fte_cell.groupby(["date", "sekt", "alder_gr"],
                                   as_index=False)["fte"].sum())
    by_all_fte["ai_q"] = "all"
    fte = pd.concat([by_q_fte, by_all_fte], ignore_index=True)
    fte = fte.rename(columns={"sekt": "sector", "alder_gr": "age_group"})
    fte = add_per_capita(fte, "fte", pop)
    fte = add_yagan_baseline(fte, "percap",
                          ["sector", "age_group", "ai_q"], "fte")
    fte = fte.sort_values(["sector", "age_group", "ai_q", "date"])
    fte_path = os.path.join(OUT_DIR,
                            "fig_fte_by_age_quintile_yagan.csv")
    fte.to_csv(fte_path, index=False)
    print(f"Wrote {fte_path} ({len(fte):,} rows)")

    # ---- Outcomes: employment-weighted mean across occupations ----
    cnt_key = counts.rename(columns={"count": "w"})[
        ["date", "yrke4", "alder_gr", "sekt", "w"]
    ]
    out_rows = []
    for var in OUTCOME_VARS:
        v = (df[df["variable"] == var]
             [["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]])
        v = v.merge(cnt_key, on=["date", "yrke4", "alder_gr", "sekt"],
                    how="inner")
        v = v[v["w"] > 0]
        v["wv"] = v["value"] * v["w"]
        for q_label, keys in [("q", ["date", "sekt", "alder_gr", "ai_q"]),
                              ("all", ["date", "sekt", "alder_gr"])]:
            g = v.groupby(keys, as_index=False).agg(wv=("wv", "sum"),
                                                     w=("w", "sum"))
            g["value"] = g["wv"] / g["w"]
            g["variable"] = var
            g["ai_q"] = g["ai_q"].astype(str) if q_label == "q" else "all"
            out_rows.append(g[["date", "sekt", "alder_gr", "ai_q",
                               "variable", "value"]])

    outc = pd.concat(out_rows, ignore_index=True)
    outc = outc.rename(columns={"sekt": "sector", "alder_gr": "age_group"})
    outc = add_yagan_baseline(outc, "value",
                           ["sector", "age_group", "ai_q", "variable"],
                           "value")
    outc = outc.sort_values(["sector", "age_group", "variable",
                              "ai_q", "date"])
    outc_path = os.path.join(OUT_DIR,
                             "fig_outcomes_by_age_quintile_yagan.csv")
    outc.to_csv(outc_path, index=False)
    print(f"Wrote {outc_path} ({len(outc):,} rows)")

    # ---- Selected high-exposure occupations by decade (private) ----
    occ_groups = {
        "Software developers": ["2512", "2513", "2514", "2519"],
        "ICT systems analysts": ["2511"],
        "Customer service agents": ["4222"],
        "ICT operations technicians": ["3511"],
    }
    code2grp = {c: g for g, cs in occ_groups.items() for c in cs}
    sel = counts[(counts["sekt"] == 2) & (counts["yrke4"].isin(code2grp))].copy()
    sel["occ_group"] = sel["yrke4"].map(code2grp)
    sel = (sel.groupby(["date", "occ_group", "alder_gr"], as_index=False)
           ["count"].sum()
           .rename(columns={"alder_gr": "age_group"}))
    sel = add_per_capita(sel, "count", pop)
    sel = add_yagan_baseline(sel, "percap",
                          ["occ_group", "age_group"], "emp")
    sel = sel.sort_values(["occ_group", "age_group", "date"])
    sel_path = os.path.join(OUT_DIR, "fig_selected_occ_by_age_yagan.csv")
    sel.to_csv(sel_path, index=False)
    print(f"Wrote {sel_path} ({len(sel):,} rows)")


if __name__ == "__main__":
    main()
