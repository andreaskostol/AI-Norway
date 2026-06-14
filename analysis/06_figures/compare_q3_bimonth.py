"""
compare_q3_bimonth.py: Side-by-side of the base Q3 event-study (no seasonal
controls) vs. the Q3 + bimonth-x-quintile FE variant.

Run after both of:
  Rscript analysis/06_figures/microdata_es_decade_q3.R
  Rscript analysis/06_figures/microdata_es_decade_q3_bimonth.R

Reads:
  analysis/output/coefficients/coef_microdata_es_decade_q3.csv
  analysis/output/coefficients/coef_microdata_es_decade_q3_bimonth.csv

Reports per (age_group, ai_q):
  - Median SE, base vs bimonth
  - Number of NA coefs (collinear, dropped by fixest)
  - Pre-period |coef| sup-norm (proxy for pre-trend noise)
  - Post-period sup-norm
"""
import csv
from pathlib import Path
from collections import defaultdict
import statistics as st

BASE = Path("analysis/output/coefficients")
BASE_FILE  = BASE / "coef_microdata_es_decade_q3.csv"
BIM_FILE   = BASE / "coef_microdata_es_decade_q3_bimonth.csv"

def load(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "age": int(r["age_group"]),
                    "q":   int(r["ai_q"]),
                    "k":   int(r["k"]),
                    "coef": float(r["coef"]) if r["coef"] not in ("", "NA") else None,
                    "se":   float(r["se"])   if r["se"]   not in ("", "NA") else None,
                })
            except (ValueError, KeyError):
                continue
    return rows

def summarize(rows):
    out = defaultdict(lambda: {"se": [], "pre": [], "post": [], "na": 0, "n": 0})
    for r in rows:
        if r["k"] == -1:    # reference, skip
            continue
        key = (r["age"], r["q"])
        out[key]["n"] += 1
        if r["coef"] is None or r["se"] is None:
            out[key]["na"] += 1
            continue
        out[key]["se"].append(r["se"])
        if r["k"] < -1:
            out[key]["pre"].append(abs(r["coef"]))
        else:
            out[key]["post"].append(abs(r["coef"]))
    return out

def fmt(v, f=".4f"):
    return "  -  " if v is None else format(v, f)

base = summarize(load(BASE_FILE))
bim  = summarize(load(BIM_FILE))

keys = sorted(set(base) | set(bim))
age_labels = {1: "21-30", 2: "31-40", 3: "41-50", 4: "51-60"}

print(f"{'age':>6} {'q':>2}  "
      f"{'med SE base':>11} {'med SE bim':>11}  "
      f"{'NA base':>7} {'NA bim':>7}  "
      f"{'sup pre b':>9} {'sup pre m':>9}  "
      f"{'sup post b':>10} {'sup post m':>10}")
print("-" * 100)
for k in keys:
    a, q = k
    b, m = base.get(k, {}), bim.get(k, {})
    print(f"{age_labels.get(a, a):>6} Q{q}  "
          f"{fmt(st.median(b['se']) if b.get('se') else None):>11} "
          f"{fmt(st.median(m['se']) if m.get('se') else None):>11}  "
          f"{b.get('na', 0):>7} {m.get('na', 0):>7}  "
          f"{fmt(max(b['pre']) if b.get('pre') else None):>9} "
          f"{fmt(max(m['pre']) if m.get('pre') else None):>9}  "
          f"{fmt(max(b['post']) if b.get('post') else None):>10} "
          f"{fmt(max(m['post']) if m.get('post') else None):>10}")
