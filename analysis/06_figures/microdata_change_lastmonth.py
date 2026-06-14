"""
microdata_change_lastmonth.py

Cross-sectional table of per-quintile employment change and the Q5-Q1 "double
difference", using the LAST datapoint only (October 2022 -> February 2026). The
unit of observation is the 4-digit STYRK-08 occupation; because the kiindeksen.no
quintiles are equal-weighted per occupation, an unweighted cross-sectional
regression of each occupation's change on quintile dummies reproduces the index
numbers and gives heteroskedasticity-robust (HC1) standard errors and N.

Two bases are reported: "sa" (seasonally adjusted, exactly as on the index) and
"raw" (no adjustment). Pooled/panel Poisson regressions live elsewhere
(microdata_did_cell.R); this script is the simple cross-sectional descriptive.

Input:  microdata-output/09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv
        data/ai_exposure/styrk08_eloundou_beta_mapping.csv
Output: analysis/output/coefficients/coef_quintile_change_lastmonth.csv
        (schema: basis, ai_q, mean_change, se, n_occ, n_emp)

Usage:
    python analysis/06_figures/microdata_change_lastmonth.py
"""

import os                                   # build file paths
import numpy as np                          # numeric arrays / contrast vector
import pandas as pd                         # data handling
import statsmodels.api as sm                # OLS with HC1-robust standard errors

from seasonal import seasonal_adjust        # shared X-11 core (same as the dashboard)

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")   # repo root
PARSED = os.path.join(BASE_DIR, "microdata-output",              # parsed cell aggregates
                      "09_occ_agedecade_sektor_2021m01_2026m02_parsed.csv")
EXP_FILE = os.path.join(BASE_DIR, "data", "ai_exposure",         # occupation -> quintile
                        "styrk08_eloundou_beta_mapping.csv")
OUT_DIR = os.path.join(BASE_DIR, "analysis", "output", "coefficients")  # output dir
OUT_CSV = os.path.join(OUT_DIR, "coef_quintile_change_lastmonth.csv")   # output file

REF_DATE = "2022-10-16"                      # October 2022 = the baseline month
SEAS_FROM, SEAS_TO = "2021-01-16", "2024-12-16"   # SA factor-estimation window
AGE_KEEP = ["1", "2", "3", "4"]              # decade age groups 21-30 .. 51-60
PRIVATE = 2                                  # sector code 2 = private


def occupation_changes():
    """Return one row per occupation: quintile, last-month headcount, and the
    raw and seasonally-adjusted proportional change Oct 2022 -> last month."""
    df = pd.read_csv(PARSED, dtype={"yrke4": str, "alder_gr": str, "date": str})  # read
    df = df[(df["variable"] == "count")          # employment counts only
            & (df["sekt"] == PRIVATE)            # private sector only
            & (df["alder_gr"].isin(AGE_KEEP))]   # ages 21-60 (decades 1-4)

    # Collapse to one headcount series per occupation x month (sum over ages).
    occ = (df.groupby(["yrke4", "date"], as_index=False)["value"].sum()
             .rename(columns={"value": "emp"}))

    # Attach the Eloundou exposure quintile (same mapping the figures use).
    exp = pd.read_csv(EXP_FILE, dtype={"styrk08": str})        # read the mapping
    exp = exp[exp["quintile"].notna()]                        # drop unmapped occupations
    exp = exp[["styrk08", "quintile"]].rename(columns={"styrk08": "yrke4"})  # rename key
    exp["ai_q"] = exp["quintile"].astype(int)                 # quintile as integer
    occ = occ.merge(exp[["yrke4", "ai_q"]], on="yrke4")       # inner join -> Canaries occ

    last_date = occ["date"].max()                # last month present (2026-02-16)
    print(f"Reference: {REF_DATE}  Last: {last_date}")  # show the endpoints used

    rows = []                                    # collect one record per occupation
    for oid, s in occ.groupby("yrke4"):          # one occupation at a time
        s = s.sort_values("date")                # series in date order
        dates = set(s["date"])                   # months available for this occupation
        if REF_DATE not in dates or last_date not in dates:   # need both endpoints
            continue                             # skip occupations missing an endpoint
        base_raw = s.loc[s["date"] == REF_DATE, "emp"].iloc[0]    # Oct 2022 headcount
        last_raw = s.loc[s["date"] == last_date, "emp"].iloc[0]   # last-month headcount
        if base_raw <= 0 or last_raw <= 0:       # need positive headcount at both ends
            continue
        sa = seasonal_adjust(s[["date", "emp"]]  # seasonally adjust the headcount series
                             .rename(columns={"emp": "value"}), SEAS_FROM, SEAS_TO)
        base_sa = sa.loc[sa["date"] == REF_DATE, "value"].iloc[0]   # SA Oct 2022 level
        last_sa = sa.loc[sa["date"] == last_date, "value"].iloc[0]  # SA last-month level
        rows.append({                            # store this occupation's changes
            "yrke4": oid,                        # occupation code
            "ai_q": int(s["ai_q"].iloc[0]),      # exposure quintile
            "base_emp": base_raw,                # Oct 2022 headcount = regression weight
            "n_emp": last_raw,                   # last-month headcount (for totals)
            "change_raw": last_raw / base_raw - 1,   # raw proportional change
            "change_sa": last_sa / base_sa - 1})     # SA proportional change
    cs = pd.DataFrame(rows)                       # cross-section: one row per occupation
    print(f"Occupations with both endpoints: {len(cs)}")  # report cross-section size
    return cs


def quintile_table(cs, depvar, basis):
    """Per-quintile mean change + HC1-robust SE + N, and the Q5-Q1 contrast,
    via a cross-sectional regression on quintile dummies, each occupation
    weighted by its October 2022 headcount. That base-employment weighting makes
    the per-quintile means reproduce the kiindeksen aggregate index (the index
    sums headcount over occupations within a quintile)."""
    dummies = pd.get_dummies(cs["ai_q"], prefix="Q").astype(float)  # Q_1..Q_5 (0/1)
    dummies.columns = [c.replace("Q_", "Q") for c in dummies.columns]  # -> Q1..Q5
    cols = [f"Q{q}" for q in range(1, 6)]        # fixed column order Q1..Q5
    X = dummies[cols]                            # design matrix (no intercept)
    y = cs[depvar].to_numpy()                    # the change variable for this basis
    wt = cs["base_emp"].to_numpy()               # weights = Oct 2022 headcount
    res = sm.WLS(y, X, weights=wt).fit(cov_type="HC1")  # WLS, HC1-robust; coefs = wtd means

    counts = cs["ai_q"].value_counts()           # occupations per quintile
    emps = cs.groupby("ai_q")["n_emp"].sum()     # total employment per quintile
    out = []                                     # rows for this basis
    for q in range(1, 6):                        # one row per quintile 1..5
        out.append({                             # quintile mean change + robust SE
            "basis": basis, "ai_q": str(q),
            "mean_change": res.params[f"Q{q}"],  # mean change in quintile q
            "se": res.bse[f"Q{q}"],              # HC1-robust SE of that mean
            "n_occ": int(counts.get(q, 0)),      # number of occupations in q
            "n_emp": int(emps.get(q, 0))})       # total employment in q

    contrast = np.array([-1, 0, 0, 0, 1], float)  # Q5 minus Q1 contrast over Q1..Q5
    tt = res.t_test(contrast)                    # estimate + robust SE of the contrast
    out.append({                                 # the double-difference summary row
        "basis": basis, "ai_q": "Q5mQ1",
        "mean_change": float(np.ravel(tt.effect)[0]),  # Q5 - Q1 (double difference)
        "se": float(np.ravel(tt.sd)[0]),               # its HC1-robust SE
        "n_occ": int(len(cs)),                   # total occupations
        "n_emp": int(cs["n_emp"].sum())})        # total employment
    return out


def main():
    cs = occupation_changes()                    # build the cross-section
    rows = (quintile_table(cs, "change_sa", "sa")    # seasonally adjusted basis
            + quintile_table(cs, "change_raw", "raw"))  # raw basis
    out = pd.DataFrame(rows)                      # assemble the output table
    os.makedirs(OUT_DIR, exist_ok=True)          # ensure the output dir exists
    out.to_csv(OUT_CSV, index=False)             # write the coefficient CSV
    print(f"Wrote {OUT_CSV}")                     # progress message
    print(out.to_string(index=False))            # echo numbers for a quick sanity check


if __name__ == "__main__":
    main()
