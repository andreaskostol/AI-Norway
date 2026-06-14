"""
plot_seasonality_descriptive.py
================================
Descriptive (NON-regression) diagnostic showing the seasonality issue that
motivates the quintile x bimonth FE: how does the raw quintile-level log
employment series move relative to Q3 (the reference), with and without a
simple bimonth-quintile seasonal adjustment?

This is not the Poisson DiD; it is a transparent pre-regression check so we
can see (i) the size of the differential seasonality across quintiles, and
(ii) what a bimonth-level seasonal absorber would visually do.

Inputs:
  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
  data/ai_exposure/styrk08_eloundou_beta_mapping.csv

Output:
  analysis/output/figures/seasonality_descriptive_q3.pdf
"""
import csv
from pathlib import Path
from collections import defaultdict
import math
import matplotlib.pyplot as plt

BASE = Path(".")
DATA = BASE / "microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv"
MAP  = BASE / "data/ai_exposure/styrk08_eloundou_beta_mapping.csv"
OUT  = BASE / "analysis/output/figures/seasonality_descriptive_q3.pdf"

# ----------------------------------------------------------------------------
# Quintile mapping
# ----------------------------------------------------------------------------
yrke_to_q = {}
with open(MAP, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["quintile"] in ("", "NA"):
            continue
        yrke_to_q[r["styrk08"].zfill(4)] = int(r["quintile"])

# ----------------------------------------------------------------------------
# Aggregate counts by (age_decade, quintile, date)
# ----------------------------------------------------------------------------
agg = defaultdict(int)          # (age, q, date) -> count
with open(DATA, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["variable"] != "count":  continue
        if r["sekt"] != "2":          continue
        if r["alder_gr"] not in {"1","2","3","4"}:  continue
        q = yrke_to_q.get(r["yrke4"])
        if q is None:                 continue
        agg[(int(r["alder_gr"]), q, r["date"])] += int(r["value"])

# Pivot into series[(age, q)] -> ordered list of (date, count)
series = defaultdict(list)
for (a, q, date), v in agg.items():
    series[(a, q)].append((date, v))
for k in series:
    series[k].sort()

dates = sorted({d for (_, _, d) in agg})           # 62 months
date_to_idx = {d: i for i, d in enumerate(dates)}
date_to_cm  = {d: int(d[5:7]) for d in dates}      # 1..12
date_to_bm  = {d: (date_to_cm[d] - 1) // 2 + 1 for d in dates}  # 1..6

# Reference: Oct 2022 = "2022-10-16"
REF_DATE = "2022-10-16"

# ----------------------------------------------------------------------------
# Build log-deviation series:  ln(N_{a,q,t}) - ln(N_{a,q,ref})
# ----------------------------------------------------------------------------
log_dev = {}
for (a, q), lst in series.items():
    by_date = dict(lst)
    if REF_DATE not in by_date:    continue
    n_ref = by_date[REF_DATE]
    log_dev[(a, q)] = [
        (d, math.log(n / n_ref) if n > 0 else None) for d, n in lst
    ]

# DiD-style: subtract Q3's path from each other quintile, per age decade
# This is the "no seasonal control" descriptive analogue of gamma_{q,k}.
def did(a, q):
    out = []
    qref = dict(log_dev.get((a, 3), []))
    for d, v in log_dev.get((a, q), []):
        v_ref = qref.get(d)
        if v is None or v_ref is None:
            out.append((d, None))
        else:
            out.append((d, v - v_ref))
    return out

# Bimonth-quintile seasonal adjustment (descriptive):
#   For each (a, q), compute the bimonth average of the did series over the
#   pre-period (dates <= REF_DATE), then subtract it from the full series.
# This is what an ai_q^bimonth FE would absorb under a perfect-pre-trend
# parallel-paths assumption.
def did_seasonally_adjusted(a, q):
    raw = did(a, q)
    pre = [(d, v) for d, v in raw if d <= REF_DATE and v is not None]
    bm_means = {}
    bm_buckets = defaultdict(list)
    for d, v in pre:
        bm_buckets[date_to_bm[d]].append(v)
    for bm, xs in bm_buckets.items():
        bm_means[bm] = sum(xs) / len(xs)
    return [
        (d, (v - bm_means.get(date_to_bm[d], 0.0)) if v is not None else None)
        for d, v in raw
    ]

# ----------------------------------------------------------------------------
# Plot: 4 age decades x 2 panels (raw DiD, seasonally-adjusted DiD)
# ----------------------------------------------------------------------------
AGE_LABELS = {1: "21-30", 2: "31-40", 3: "41-50", 4: "51-60"}
Q_COLORS   = {1: "#1f77b4", 2: "#2ca02c", 4: "#ff7f0e", 5: "#d62728"}

fig, axes = plt.subplots(4, 2, figsize=(11, 11), sharex=True)
xs = list(range(len(dates)))

ref_idx = date_to_idx[REF_DATE]
xticks_idx = [i for i, d in enumerate(dates) if d[5:7] == "01"]
xticklabels = [dates[i][:4] for i in xticks_idx]

for row, a in enumerate([1, 2, 3, 4]):
    for col, (title, fn) in enumerate([
        ("Raw: Qq - Q3, log deviation from Oct 2022",
         did),
        ("With bimonth × quintile pre-period mean removed",
         did_seasonally_adjusted),
    ]):
        ax = axes[row, col]
        ax.axhline(0, color="black", lw=0.4)
        ax.axvline(ref_idx, color="black", lw=0.4, ls="--")
        for q in [1, 2, 4, 5]:
            s = fn(a, q)
            ys = [v for _, v in s]
            ax.plot(xs, ys, color=Q_COLORS[q], lw=1.2, label=f"Q{q}")
        if row == 0:
            ax.set_title(title, fontsize=10)
        if col == 0:
            ax.set_ylabel(f"{AGE_LABELS[a]}", fontsize=10)
        ax.tick_params(axis="both", labelsize=8)
        if row == 3:
            ax.set_xticks(xticks_idx)
            ax.set_xticklabels(xticklabels)
        ax.grid(alpha=0.25, lw=0.3)
        if row == 0 and col == 1:
            ax.legend(loc="upper left", fontsize=8, frameon=False, ncols=4)

fig.suptitle("Differential seasonality across exposure quintiles, "
             "private sector, by age decade\n"
             "Left: raw DiD (Qq - Q3). Right: after removing bimonth × quintile "
             "pre-period mean.", fontsize=11)
fig.tight_layout()
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight")
fig.savefig(OUT.with_suffix(".png"), bbox_inches="tight", dpi=150)
print(f"Saved: {OUT}")
print(f"Saved: {OUT.with_suffix('.png')}")

# Also print the bimonth seasonal pattern per quintile (averaged across age)
print()
print("Pre-period bimonth means of (Qq - Q3), averaged across age decades:")
print(f"{'bimonth':>9}  " + "  ".join(f"Q{q:>2}" for q in [1, 2, 4, 5]))
bm_label = {1: "Jan-Feb", 2: "Mar-Apr", 3: "May-Jun",
            4: "Jul-Aug", 5: "Sep-Oct", 6: "Nov-Dec"}
for bm in range(1, 7):
    vals = []
    for q in [1, 2, 4, 5]:
        ms = []
        for a in [1, 2, 3, 4]:
            raw = did(a, q)
            pre = [v for d, v in raw
                   if d <= REF_DATE and v is not None and date_to_bm[d] == bm]
            if pre:
                ms.append(sum(pre) / len(pre))
        vals.append(sum(ms) / len(ms) if ms else float("nan"))
    print(f"{bm_label[bm]:>9}  " + "  ".join(f"{v:+.4f}" for v in vals))
