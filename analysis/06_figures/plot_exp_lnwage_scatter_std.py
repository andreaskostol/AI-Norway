"""Scatter of standardized exposure vs. standardized ln(FTE wage), by age group.

Both axes are z-scored WITHIN age group (unweighted), so panels share a common
scale and the relationship strength is directly comparable across age groups.
Reads the occupation x age dataset built by plot_exp_lnwage_scatter.py.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "analysis" / "output" / "occ_age_exp_wage_prechatgpt.csv"
OUT_FIG = BASE / "analysis" / "output" / "figures" / "interaction" / "figure_exp_lnwage_std_by_age"
OUT_FIG.parent.mkdir(parents=True, exist_ok=True)
AGE = ["21–30", "31–40", "41–50", "51–60"]

g = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str})
# standardize both within age group (self-contained: do not rely on columns that
# another script may or may not have written to the shared dataset)
g["z_exp"] = g.groupby("alder_gr")["eloundou_beta"].transform(
    lambda s: (s - s.mean()) / s.std(ddof=0))
g["z_lnwage"] = g.groupby("alder_gr")["ln_wage"].transform(
    lambda s: (s - s.mean()) / s.std(ddof=0))

plt.rcParams.update({"font.size": 12, "axes.titlesize": 14})
fig, axes = plt.subplots(2, 2, figsize=(10, 10), sharex=True, sharey=True)
# tight, robust symmetric limit (a few outliers fall outside and are clipped
# from view; the fit still uses all points)
LIM = 3.0
for ax, lab in zip(axes.flat, AGE):
    d = g[g.age_label == lab]
    x, y, w = d.z_exp.values, d.z_lnwage.values, d.n_obs.values
    ax.scatter(x, y, s=1.2 * np.sqrt(w), alpha=0.4, color="#2171B5",
               edgecolor="white", linewidth=0.2)
    b1, b0 = np.polyfit(x, y, 1, w=np.sqrt(w))          # person-month-weighted
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, b0 + b1 * xs, color="#08306B", lw=2)
    sw = w / w.sum()
    yhat = b0 + b1 * x
    ybar = np.sum(sw * y)
    r2 = 1 - np.sum(w * (y - yhat) ** 2) / np.sum(w * (y - ybar) ** 2)
    ax.set_title(f"{lab}   (slope={b1:.2f}, $R^2$={r2:.2f}, n={len(d)})")
    ax.axhline(0, color="grey", lw=0.6, ls=":")
    ax.axvline(0, color="grey", lw=0.6, ls=":")
    ax.grid(alpha=0.2)
    ax.set_xlim(-LIM, LIM)
    ax.set_ylim(-LIM, LIM)
    ax.set_aspect("equal", "box")

for ax in axes[-1]:
    ax.set_xlabel("standardized exposure  z(β)")
for ax in axes[:, 0]:
    ax.set_ylabel("standardized ln(FTE wage)  z(lnw)")

fig.suptitle("Standardized AI exposure vs. standardized pre-ChatGPT log "
             "FTE wage by age group (private sector)", fontsize=14)
fig.text(0.5, 0.005,
         "Both axes z-scored within age group (unweighted). Dot size ∝ "
         "√(person-months); fit and R² person-month-weighted. "
         "Wage = full-time-equivalent (kontantlønn ÷ stillingsprosent).",
         ha="center", fontsize=9)
fig.tight_layout(rect=[0, 0.02, 1, 0.97])
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT_FIG}.{ext}", dpi=150, bbox_inches="tight")
print(f"wrote {OUT_FIG}.pdf / .png")

print(f"\n{'age':7} {'wtd slope':>10} {'wtd R2':>7} {'unwtd corr':>11}")
for lab in AGE:
    d = g[g.age_label == lab]
    print(f"{lab:7} {np.polyfit(d.z_exp, d.z_lnwage, 1, w=np.sqrt(d.n_obs))[0]:10.3f} "
          f"{np.corrcoef(d.z_exp, d.z_lnwage)[0,1]**2:7.3f} "
          f"{np.corrcoef(d.z_exp, d.z_lnwage)[0,1]:11.3f}")
