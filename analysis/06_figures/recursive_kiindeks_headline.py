"""
recursive_kiindeks_headline.py

Real-time reconstruction of the kiindeksen.no headline number ("KI-indeks") and
its uncertainty, for the dashboard-reliability paragraph in the Discussion
(Section "The Companion Dashboard").

The site's headline (app.js headlineGrowth) is NOT a regression coefficient. It
is the relative employment growth of the most- vs least-exposed quintile:

    g_q   = 100 * ( mean(last 3 months) / level(Oct 2022) - 1 )
    KI    = 100 * ( (1+g5/100)/(1+g1/100) - 1 )          [percentage points]

on the by_exposure series: private sector (sekt 2), ages 21-60 pooled, employment
index, seasonally adjusted (X-11 core, factors FROZEN on 2021-2024, the same
procedure as the dashboard's build_release.py). Because the seasonal factors are
frozen, the SA index is vintage-independent; the only thing that moves across
vintages is which three months form the "last 3". We re-estimate KI on expanding
windows from data through Jan 2025 to the data edge (Feb 2026) and attach an
occupation cluster-bootstrap standard error (the site reports none).

Validation: prints the full-data SA value, which reproduces dashboard.json (-0.23).

Stage-1 estimation script (writes the coefficient artifact); the figure is drawn
by plot_recursive_kiindeks.py.

Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m06_parsed.csv
        data/ai_exposure/styrk08_eloundou_beta_mapping.csv
        dashboard/site/public/data/dashboard.json   (validation only)
Output: analysis/output/coefficients/coef_recursive_kiindeks_headline.csv
          (vintage, cutoff, g1, g5, ki, se, ci_lo, ci_hi, n_post_months)

Usage:  python analysis/06_figures/recursive_kiindeks_headline.py [eloundou|mouchel] [chatgpt|claudecode]
        The first optional argument picks the exposure measure whose quintiles
        define Q1/Q5 (default eloundou). With "mouchel" the quintiles come from
        styrk08_mouchel_mapping.csv, the output gets the suffix _mouchel, and
        the validation reads the mouchel_by_exposure package instead.
        The second picks the site's reference epoch (default chatgpt): "claudecode"
        uses the dashboard's agentic-AI reference, the mean of Feb 2024-Jan 2025
        (EPOCHS.claudecode in app.js), first vintage 2025-04 (three post months),
        and adds the suffix _claudecode to the output.
"""
import sys                                  # command-line argument: exposure measure
import csv                                  # read input mappings/panel, write coefficient CSV
import json                                 # read dashboard.json for validation
from pathlib import Path                    # filesystem-path handling
from collections import defaultdict         # nested auto-initialising count maps

import numpy as np                          # arrays, seasonal adjustment, bootstrap

BASE = Path(__file__).resolve().parents[2]  # repo root (this file is 2 levels below it)
PANEL = BASE / "microdata-output" / "09_occ_agedecade_sektor_kpos_2021m01_2026m06_parsed.csv"  # occ x month counts
MEASURE = sys.argv[1] if len(sys.argv) > 1 else "eloundou"  # which quintiles define Q1/Q5
assert MEASURE in ("eloundou", "mouchel"), "measure must be eloundou or mouchel"
EPOCH = sys.argv[2] if len(sys.argv) > 2 else "chatgpt"  # site reference point
assert EPOCH in ("chatgpt", "claudecode"), "epoch must be chatgpt or claudecode"
# Occupation -> quintile mapping and output file depend on the measure; the
# Eloundou paths are unchanged so existing callers keep working.
EXP = BASE / "data" / "ai_exposure" / ("styrk08_eloundou_beta_mapping.csv" if MEASURE == "eloundou"
                                       else "styrk08_mouchel_mapping.csv")  # occupation -> quintile
DJSON = BASE / "dashboard" / "site" / "public" / "data" / "dashboard.json"  # published numbers (validation)
OUT = BASE / "analysis" / "output" / "coefficients" / (
    "coef_recursive_kiindeks_headline"
    + ("" if MEASURE == "eloundou" else "_mouchel")
    + ("" if EPOCH == "chatgpt" else "_claudecode") + ".csv")  # recursive KI output
# Package in dashboard.json that carries this measure's by_exposure series.
DJSON_PKG = "by_exposure" if MEASURE == "eloundou" else "mouchel_by_exposure"

AGES = {"1", "2", "3", "4"}            # 21-60
SECTOR = "2"                            # private
# Reference window: a single month before ChatGPT, or the twelve months
# before Claude Code (the dashboard's agentic-AI epoch) averaged.
REF_FROM, REF_TO = ("2022-10", "2022-10") if EPOCH == "chatgpt" else ("2024-02", "2025-01")
REF_MONTH = REF_TO                      # last month of the reference window (post months counted after it)
SEAS_FROM, SEAS_TO = "2021-01", "2024-12"  # window the seasonal factors are estimated/frozen on
FIRST_CUT = "2025-01" if EPOCH == "chatgpt" else "2025-04"  # first vintage (>= 3 post months)
LAST_CUT = "2026-06"                    # last vintage data-edge
N_BOOT = 1000                           # bootstrap replications per vintage
SEED = 12345                            # RNG seed for reproducible bootstrap


def ym(date_str):                       # "2021-01-16" -> "2021-01"
    # Take the leading YYYY-MM of the date string.
    return date_str[:7]


def seasonal_adjust(values, months):
    """X-11 core with factors frozen on 2021-2024 (port of build_release.py)."""
    # Ensure a float array of levels.
    values = np.asarray(values, float)
    # Sort order that puts months ascending.
    order = np.argsort(months)
    # Inverse permutation to restore the original order at the end.
    inv = np.argsort(order)
    # Reorder values and months into ascending-month order.
    v = values[order]; mo = np.array(months)[order]
    # Mask of months inside the frozen factor-estimation window.
    est_mask = (mo >= SEAS_FROM) & (mo <= SEAS_TO)
    # Log levels over the estimation window.
    y_est = np.log(v[est_mask])
    # Calendar month (1-12) for each estimation-window observation.
    cal = np.array([int(m[5:7]) for m in mo[est_mask]])
    # Number of estimation-window observations.
    n = len(y_est)
    # 13-term centred moving-average weights (half weight on the endpoints).
    w = np.ones(13); w[0] = w[12] = 0.5; w /= 12.0
    # Trend container, NaN where the centred MA is undefined.
    ma = np.full(n, np.nan)
    # Centred 13-month moving average of the log levels.
    for i in range(6, n - 6):
        ma[i] = (y_est[i - 6:i + 7] * w).sum()
    # Detrended series (log level minus trend).
    d = y_est - ma
    # Mask of finite detrended values (excludes the MA edges).
    ok = np.isfinite(d)
    # Mean detrended value per calendar month = raw seasonal factor.
    fac = np.array([d[ok & (cal == mm)].mean() for mm in range(1, 13)])
    # Centre the factors so they sum to zero (no level shift).
    fac = fac - fac.mean()
    # Calendar month for every month in the full series.
    cal_all = np.array([int(m[5:7]) for m in mo])
    # Apply the frozen factors: SA level = exp(log level - factor).
    sa = np.exp(np.log(v) - fac[cal_all - 1])
    # Restore the caller's original ordering.
    return sa[inv]


def growth(series_by_month, months_sorted, cutoff, adj):
    """KI components for one quintile series. months_sorted ascending, <= cutoff."""
    # Months available at or before this vintage's cutoff.
    keep = [m for m in months_sorted if m <= cutoff]
    # Levels for those months, in ascending order.
    vals = np.array([series_by_month[m] for m in keep], float)
    # Seasonally adjust when requested.
    if adj == "sa":
        vals = seasonal_adjust(vals, keep)
    # Month -> (adjusted) level lookup.
    idx = {m: vals[i] for i, m in enumerate(keep)}
    # Reference level: mean over the reference window (one month for ChatGPT).
    before = np.mean([idx[m] for m in keep if REF_FROM <= m <= REF_TO])
    # The three most recent months of this vintage.
    last3 = keep[-3:]
    # Average level over the last three months.
    after = np.mean([idx[m] for m in last3])
    # Percent growth of the last-3 average relative to the reference.
    return 100.0 * (after / before - 1.0)


def ki_from_quintile_series(q1_series, q5_series, months_sorted, cutoff, adj):
    # Growth of the least-exposed quintile.
    g1 = growth(q1_series, months_sorted, cutoff, adj)
    # Growth of the most-exposed quintile.
    g5 = growth(q5_series, months_sorted, cutoff, adj)
    # KI headline = relative growth of Q5 vs Q1, in percentage points.
    rel = 100.0 * ((1 + g5 / 100) / (1 + g1 / 100) - 1)
    # Return both component growths and the headline.
    return g1, g5, rel


# ---- Load occupation x month counts (private, ages 21-60), with quintile ------
# Map of occupation code -> exposure quintile.
quint = {}
# Read the Eloundou quintile mapping.
with open(EXP) as f:
    # One row per occupation.
    for r in csv.DictReader(f):
        # Keep only occupations with an assigned quintile.
        if r["quintile"] not in ("", "NA"):
            # Zero-pad the code to 4 chars and store its integer quintile.
            quint["%04s" % r["styrk08"]] = int(r["quintile"])

# Nested map: quintile -> occupation -> month -> summed count.
occ_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
# Set of all months seen in the panel.
months_set = set()
# Read the occupation x age x sector x month panel.
with open(PANEL) as f:
    # One row per cell.
    for r in csv.DictReader(f):
        # Keep only employment counts, private sector, ages 21-60.
        if r["variable"] != "count" or r["sekt"] != SECTOR or r["alder_gr"] not in AGES:
            continue
        # Zero-pad the occupation code to 4 chars.
        occ = "%04s" % r["yrke4"]
        # Look up its quintile.
        q = quint.get(occ)
        # Skip occupations without a quintile.
        if q is None:
            continue
        # Reduce the date to YYYY-MM.
        m = ym(r["date"])
        # Accumulate the count into quintile/occupation/month (sum over age groups).
        occ_counts[q][occ][m] += float(r["value"])
        # Record this month.
        months_set.add(m)

# All months in ascending order.
months_sorted = sorted(months_set)
# The vintage cutoffs to evaluate (every month-edge from FIRST_CUT to LAST_CUT).
cutoffs = [m for m in months_sorted if FIRST_CUT <= m <= LAST_CUT]

# ---- Point estimate + bootstrap per vintage -----------------------------------
# Seeded RNG for a reproducible occupation-cluster bootstrap.
rng = np.random.default_rng(SEED)
# Occupation codes in quintile 1.
q1_occs = list(occ_counts[1].keys())
# Occupation codes in quintile 5.
q5_occs = list(occ_counts[5].keys())


def stack(occs, q):
    # Matrix of occupations (rows) x all months (columns), zero-filled.
    M = np.zeros((len(occs), len(months_sorted)))
    # Month -> column-index lookup.
    midx = {m: i for i, m in enumerate(months_sorted)}
    # Fill each occupation's row with its monthly counts.
    for r, occ in enumerate(occs):
        # One (month, count) pair at a time.
        for m, c in occ_counts[q][occ].items():
            # Place the count in the right column.
            M[r, midx[m]] = c
    # Return the dense occupation x month matrix.
    return M


# Quintile-1 occupation x month count matrix.
Q1M = stack(q1_occs, 1)
# Quintile-5 occupation x month count matrix.
Q5M = stack(q5_occs, 5)


def series_from_matrix(M, rows, cols_keep):
    # Sum the selected occupation rows over the kept month columns -> quintile series.
    return M[rows][:, cols_keep].sum(axis=0)


# Output rows, one per vintage.
rows_out = []
# Use the seasonally adjusted basis throughout.
adj = "sa"
# Loop over each vintage cutoff (expanding window).
for cu in cutoffs:
    # Column indices for months at or before this cutoff.
    col_keep = [i for i, m in enumerate(months_sorted) if m <= cu]
    # The corresponding month labels.
    keep_months = [months_sorted[i] for i in col_keep]

    def ki_for(rows1, rows5):
        # Q1 series (month -> level) for the selected occupation rows.
        s1 = {m: series_from_matrix(Q1M, rows1, col_keep)[j]
              for j, m in enumerate(keep_months)}
        # Q5 series (month -> level) for the selected occupation rows.
        s5 = {m: series_from_matrix(Q5M, rows5, col_keep)[j]
              for j, m in enumerate(keep_months)}
        # Compute the KI headline from the two quintile series.
        return ki_from_quintile_series(s1, s5, keep_months, cu, adj)

    # Point estimate: use all occupations in each quintile.
    g1, g5, rel = ki_for(np.arange(len(q1_occs)), np.arange(len(q5_occs)))

    # Bootstrap container.
    boot = np.empty(N_BOOT)
    # Number of occupations in each quintile.
    n1, n5 = len(q1_occs), len(q5_occs)
    # Resample occupations with replacement and recompute KI each time.
    for b in range(N_BOOT):
        # Bootstrap draw of Q1 occupation indices.
        r1 = rng.integers(0, n1, n1)
        # Bootstrap draw of Q5 occupation indices.
        r5 = rng.integers(0, n5, n5)
        # Store the KI headline (third return value) for this draw.
        boot[b] = ki_for(r1, r5)[2]
    # Bootstrap standard error (sample sd).
    se = boot.std(ddof=1)
    # 95% percentile confidence interval.
    lo, hi = np.percentile(boot, [2.5, 97.5])
    # Record this vintage's results.
    rows_out.append(dict(vintage=len(rows_out) + 1, cutoff=cu, g1=g1, g5=g5,
                         ki=rel, se=se, ci_lo=lo, ci_hi=hi,
                         n_post_months=sum(1 for m in keep_months if m > REF_MONTH)))
    # Progress line for this vintage.
    print(f"{cu}  g1={g1:+.2f} g5={g5:+.2f}  KI={rel:+.3f} pp  se={se:.3f}  "
          f"CI=[{lo:+.2f},{hi:+.2f}]")

# ---- Validation against the published number ----------------------------------
# Load the published dashboard payload.
DB = json.load(open(DJSON))
# The validation needs this measure's package; skip gracefully if the site
# has not been rebuilt with it yet.
if DJSON_PKG in DB["packages"]:
    # Pull the by-exposure package: its SA series and date axis.
    be = DB["packages"][DJSON_PKG]; ser = be["series"]["sa"]["_"]; dd = be["dates"]
    # Indices of the reference window and the total number of dates.
    i0 = dd.index(REF_FROM + "-01"); i1 = dd.index(REF_TO + "-01"); n = len(dd)

    def gjson(col):
        # Series for this quintile; growth of last-3 average vs the reference window mean.
        v = ser[col]; base = sum(v[i0:i1 + 1]) / (i1 - i0 + 1)
        return 100 * ((v[n - 3] + v[n - 2] + v[n - 1]) / 3 / base - 1)

    # Published Q1 and Q5 growths.
    gj1, gj5 = gjson("Quintile 1 (least exposed)"), gjson("Quintile 5 (most exposed)")
    # Published KI headline.
    relj = 100 * ((1 + gj5 / 100) / (1 + gj1 / 100) - 1)
    # Print the published reference numbers.
    print(f"\nVALIDATION vs dashboard.json ({DJSON_PKG}, sa, full data): "
          f"g1={gj1:+.2f} g5={gj5:+.2f} KI={relj:+.3f} pp")
    # Print this script's full-window KI for comparison.
    print(f"   my full-window (last vintage): KI={rows_out[-1]['ki']:+.3f} pp")
else:
    print(f"\n(no {DJSON_PKG} package in dashboard.json yet; validation skipped)")

# Ensure the output directory exists.
OUT.parent.mkdir(parents=True, exist_ok=True)
# Write the per-vintage coefficient table.
with open(OUT, "w", newline="") as f:
    # CSV writer keyed on the dict fields.
    w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
    # Header then all vintage rows.
    w.writeheader(); w.writerows(rows_out)
# Confirm the output path.
print(f"\nwrote {OUT}")
