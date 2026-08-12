"""
build_figure_data.py

Stage-1 aggregation for the decade-age / sector figures. Reads the parsed
cell files (kpos extract for count/wage/hires/stillingspst, non-kpos extract
for overtid_timer/timelonn) once and writes compact tidy CSVs to
analysis/output/figure_data/. The plot scripts read only these and do no
heavy aggregation themselves (see CLAUDE convention: estimation/prep ->
artifacts -> presentation).

Outputs:
  fig_employment_by_age_quintile.csv
    date, sector, age_group, ai_q, employment, emp_index
    ai_q in {1..5} per quintile, plus 'all' (pooled over quintiles).
    emp_index = employment normalized to October 2022 (= 1.0) within each
    (sector, age_group, ai_q) series.

  fig_outcomes_by_age_quintile.csv
    date, sector, age_group, ai_q, variable, value, value_index
    variable in {kontantlonn, timelonn, stillingspst, overtid_timer, ny_jobb}
    value = employment-weighted mean across occupations within the cell.
    value_index = value normalized to October 2022 (= 1.0).

Age groups kept: alder_gr 1-4 (21-30, 31-40, 41-50, 51-60). Sectors: 1, 2.

Usage:
    python analysis/04_timeseries/build_figure_data.py
"""

import os
import pandas as pd

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")


def _newest(*names):
    """Pick the first existing file from names (newest-window first).

    The kpos decade files are extended incrementally (see
    analysis/02_parse/append_09_2026m03_m04.py), which writes a new
    `_2026m04` file alongside the older `_2026m02` one. Prefer the newest
    window that exists so this builder tracks the data without an edit here.
    """
    md = os.path.join(BASE_DIR, "microdata-output")
    for n in names:
        p = os.path.join(md, n)
        if os.path.exists(p):
            return p
    return os.path.join(md, names[-1])


# Primary source: the kpos (positive-cash-earnings) extract, matching the
# paper's paid-employment count definition and the R event studies
# (microdata_es_decade.R / microdata_did_cell.R both read the kpos file).
PARSED_KPOS = _newest(
    "09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv",
    "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv",
)
# Fallback for the two outcome variables absent from the kpos extract
# (overtid_timer, timelonn): read from the non-kpos extract until they are
# re-extracted in kpos form.
PARSED_NONKPOS = _newest(
    "09_occ_agedecade_sektor_2021m01_2026m04_parsed.csv",
    "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv",
)
NONKPOS_ONLY_VARS = ["overtid_timer", "timelonn"]
EXP_FILE = os.path.join(BASE_DIR, "data", "ai_exposure",
                        "styrk08_eloundou_beta_mapping.csv")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "figure_data")

POP_FILE = os.path.join(BASE_DIR, "data", "macro", "ssb_population_by_age_quarterly.csv")
NORM_DATE = "2022-10-16"
AGE_KEEP = ["1", "2", "3", "4"]
DECADE_RANGES = {"1": (21, 30), "2": (31, 40), "3": (41, 50), "4": (51, 60)}
OUTCOME_VARS = ["kontantlonn", "timelonn", "stillingspst", "overtid_timer", "ny_jobb"]


def load_pop():
    """Resident population by decade age group and quarter, keyed (code, 'YYYY-Qn')."""
    p = pd.read_csv(POP_FILE)
    out = {}
    for code, (lo, hi) in DECADE_RANGES.items():
        s = p[(p["age"] >= lo) & (p["age"] <= hi)].groupby("date")["population"].sum()
        for qd, val in s.items():
            out[(code, qd)] = val
    return out


def yq(datestr):
    """'2021-01-16' -> '2021-Q1' (each month takes its quarter's population)."""
    y, m, _ = datestr.split("-")
    return f"{y}-Q{(int(m) - 1) // 3 + 1}"


def add_per_capita(df, value_col, pop):
    """Add a `percap` column = value / resident population in the age group."""
    df = df.copy()
    df["percap"] = [v / pop[(str(a), yq(d))]
                    for v, a, d in zip(df[value_col], df["age_group"], df["date"])]
    return df


def add_index(df, value_col, group_cols, out_col):
    """Normalize value_col to NORM_DATE (=1.0) within each group."""
    ref = (df[df["date"] == NORM_DATE]
           .set_index(group_cols)[value_col]
           .rename("_ref"))
    df = df.merge(ref, left_on=group_cols, right_index=True, how="left")
    df[out_col] = df[value_col] / df["_ref"]
    return df.drop(columns="_ref")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # count / kontantlonn / stillingspst / ny_jobb come from the kpos extract;
    # overtid_timer and timelonn (not in kpos) come from the non-kpos extract.
    df = pd.read_csv(PARSED_KPOS, dtype={"yrke4": str, "alder_gr": str})
    df_extra = pd.read_csv(PARSED_NONKPOS, dtype={"yrke4": str, "alder_gr": str})
    df_extra = df_extra[df_extra["variable"].isin(NONKPOS_ONLY_VARS)]
    df = pd.concat([df, df_extra], ignore_index=True)
    df = df[df["alder_gr"].isin(AGE_KEEP)]

    exp = pd.read_csv(EXP_FILE, dtype={"styrk08": str})
    exp = exp[exp["quintile"].notna()][["styrk08", "quintile"]]
    exp = exp.rename(columns={"styrk08": "yrke4"})
    exp["ai_q"] = exp["quintile"].astype(int)
    df = df.merge(exp[["yrke4", "ai_q"]], on="yrke4", how="inner")

    counts = df[df["variable"] == "count"][
        ["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]
    ].rename(columns={"value": "count"})

    # ---- Employment by age x quintile (+ pooled 'all') ----
    by_q = (counts.groupby(["date", "sekt", "alder_gr", "ai_q"], as_index=False)
            ["count"].sum())
    by_q["ai_q"] = by_q["ai_q"].astype(str)
    by_all = (counts.groupby(["date", "sekt", "alder_gr"], as_index=False)
              ["count"].sum())
    by_all["ai_q"] = "all"
    emp = pd.concat([by_q, by_all], ignore_index=True)
    emp = emp.rename(columns={"sekt": "sector", "alder_gr": "age_group",
                              "count": "employment"})
    pop = load_pop()
    emp = add_per_capita(emp, "employment", pop)
    emp = add_index(emp, "percap", ["sector", "age_group", "ai_q"], "emp_index")
    emp = emp.sort_values(["sector", "age_group", "ai_q", "date"])
    emp_path = os.path.join(OUT_DIR, "fig_employment_by_age_quintile.csv")
    emp.to_csv(emp_path, index=False)
    print(f"Wrote {emp_path} ({len(emp):,} rows)")

    # ---- FTE-employment (stillingsprosent-weighted) by age x quintile ----
    # Per-cell FTE = headcount * mean stillingspst within
    # (date, yrke4, alder_gr, sekt). Indexed to October 2022 within each
    # (sector, age_group, ai_q) series, same convention as the count version.
    stp = df[df["variable"] == "stillingspst"][
        ["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]
    ].rename(columns={"value": "stillingspst"})
    fte_cell = counts.merge(stp, on=["date", "yrke4", "alder_gr", "sekt", "ai_q"],
                            how="inner")
    fte_cell["fte"] = fte_cell["count"] * fte_cell["stillingspst"]

    by_q_fte = (fte_cell.groupby(["date", "sekt", "alder_gr", "ai_q"], as_index=False)
                ["fte"].sum())
    by_q_fte["ai_q"] = by_q_fte["ai_q"].astype(str)
    by_all_fte = (fte_cell.groupby(["date", "sekt", "alder_gr"], as_index=False)
                  ["fte"].sum())
    by_all_fte["ai_q"] = "all"
    fte = pd.concat([by_q_fte, by_all_fte], ignore_index=True)
    fte = fte.rename(columns={"sekt": "sector", "alder_gr": "age_group"})
    fte = add_per_capita(fte, "fte", pop)
    fte = add_index(fte, "percap", ["sector", "age_group", "ai_q"], "fte_index")
    fte = fte.sort_values(["sector", "age_group", "ai_q", "date"])
    fte_path = os.path.join(OUT_DIR, "fig_fte_by_age_quintile.csv")
    fte.to_csv(fte_path, index=False)
    print(f"Wrote {fte_path} ({len(fte):,} rows)")

    # ---- Outcomes: employment-weighted mean across occupations ----
    cnt_key = counts.rename(columns={"count": "w"})[
        ["date", "yrke4", "alder_gr", "sekt", "w"]
    ]
    out_rows = []
    for var in OUTCOME_VARS:
        v = df[df["variable"] == var][
            ["date", "yrke4", "alder_gr", "sekt", "ai_q", "value"]
        ]
        v = v.merge(cnt_key, on=["date", "yrke4", "alder_gr", "sekt"], how="inner")
        v = v[v["w"] > 0]
        v["wv"] = v["value"] * v["w"]
        for q_label, keys in [("q", ["date", "sekt", "alder_gr", "ai_q"]),
                              ("all", ["date", "sekt", "alder_gr"])]:
            g = v.groupby(keys, as_index=False).agg(wv=("wv", "sum"), w=("w", "sum"))
            g["value"] = g["wv"] / g["w"]
            g["variable"] = var
            if q_label == "all":
                g["ai_q"] = "all"
            else:
                g["ai_q"] = g["ai_q"].astype(str)
            out_rows.append(g[["date", "sekt", "alder_gr", "ai_q", "variable", "value"]])

    outc = pd.concat(out_rows, ignore_index=True)
    outc = outc.rename(columns={"sekt": "sector", "alder_gr": "age_group"})
    outc = add_index(outc, "value", ["sector", "age_group", "ai_q", "variable"],
                     "value_index")
    outc = outc.sort_values(["sector", "age_group", "variable", "ai_q", "date"])
    outc_path = os.path.join(OUT_DIR, "fig_outcomes_by_age_quintile.csv")
    outc.to_csv(outc_path, index=False)
    print(f"Wrote {outc_path} ({len(outc):,} rows)")

    # ---- Selected occupations by decade age group (private) ----
    # Matched exactly to the kiindeksen.no yrkescase set (software developers
    # and customer service = high exposure; electricians and home health aides
    # = low exposure) so the paper and the dashboard show the same occupations.
    occ_groups = {
        "Software developers": ["2512", "2513", "2514", "2519"],   # STYRK 2512-2514, 2519
        "Customer service agents": ["4222"],                       # STYRK 4222
        "Electricians": ["7411"],                                  # STYRK 7411 (low exposure)
        "Home health aides": ["5322"],                             # STYRK 5322 (low exposure)
        # Extra cases for the Arendalsgata talk (single-panel figures via
        # plot_occ_cases_single.py; not part of the paper's four-panel figure).
        "Informasjonsradgivere": ["2432"],                         # communication (high exposure)
        "Designyrker": ["2163", "2166"],                           # product/graphic design (2163 alone too thin)
    }
    code2grp = {c: g for g, cs in occ_groups.items() for c in cs}
    sel = counts[(counts["sekt"] == 2) & (counts["yrke4"].isin(code2grp))].copy()
    sel["occ_group"] = sel["yrke4"].map(code2grp)
    sel = (sel.groupby(["date", "occ_group", "alder_gr"], as_index=False)["count"].sum()
           .rename(columns={"alder_gr": "age_group"}))
    sel = add_per_capita(sel, "count", load_pop())
    sel = add_index(sel, "percap", ["occ_group", "age_group"], "emp_index")
    sel = sel.sort_values(["occ_group", "age_group", "date"])
    sel_path = os.path.join(OUT_DIR, "fig_selected_occ_by_age.csv")
    sel.to_csv(sel_path, index=False)
    print(f"Wrote {sel_path} ({len(sel):,} rows)")


if __name__ == "__main__":
    main()
