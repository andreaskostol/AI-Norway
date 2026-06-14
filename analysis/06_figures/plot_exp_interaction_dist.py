"""Distributions of exposure and exp x std(lnwage), by age group, private sector.

Reads the occupation x age dataset built by plot_exp_lnwage_scatter.py, adds a
within-age-group standardized ln wage and the interaction exp*std(lnwage), and
plots, per age group, the distribution of exposure and of the interaction.

Note: exposure is occupation-level, so its distribution is identical across the
four panels; only the interaction (via the age-specific standardized wage) moves.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / "analysis" / "output" / "occ_age_exp_wage_prechatgpt.csv"
OUT_FIG = BASE / "analysis" / "output" / "figures" / "interaction" / "figure_exp_interaction_dist_by_age"
OUT_FIG.parent.mkdir(parents=True, exist_ok=True)

AGE = ["21–30", "31–40", "41–50", "51–60"]

g = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str})

# standardize ln wage WITHIN each age group, then form the interaction
g["z_lnwage"] = g.groupby("alder_gr")["ln_wage"].transform(
    lambda s: (s - s.mean()) / s.std(ddof=0))
g["exp_x_zwage"] = g["eloundou_beta"] * g["z_lnwage"]

# persist augmented dataset
g.sort_values(["alder_gr", "yrke4"]).to_csv(DATA, index=False)
print(f"updated {DATA} with z_lnwage, exp_x_zwage")

# ---- four-panel distributions --------------------------------------------
bins = np.linspace(-1.1, 1.2, 32)
plt.rcParams.update({"font.size": 12, "axes.titlesize": 14})
fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=True, sharey=True)
for ax, lab in zip(axes.flat, AGE):
    d = g[g.age_label == lab]
    e = d.eloundou_beta.values
    inter = d.exp_x_zwage.values
    ax.hist(e, bins=bins, density=True, alpha=0.5, color="#2171B5",
            label=f"exposure  (sd={e.std():.2f})")
    ax.hist(inter, bins=bins, density=True, alpha=0.5, color="#D94801",
            label=f"exp×std(lnw)  (sd={inter.std():.2f})")
    ax.axvline(0, color="grey", lw=0.8, ls=":")
    ax.set_title(f"{lab}   (n={len(d)} occ.)")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.2)

for ax in axes[-1]:
    ax.set_xlabel("value")
for ax in axes[:, 0]:
    ax.set_ylabel("density")

fig.suptitle("Distribution of exposure vs. exp×std(lnwage) by age group "
             "(private sector)", fontsize=15)
fig.text(0.5, 0.005,
         "Exposure (Eloundou β) is occupation-level → identical across panels. "
         "ln wage standardized within age group; interaction = exposure × z(lnwage).",
         ha="center", fontsize=9)
fig.tight_layout(rect=[0, 0.02, 1, 0.97])
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT_FIG}.{ext}", dpi=150, bbox_inches="tight")
print(f"wrote {OUT_FIG}.pdf / .png")

# quick summary
print(f"\n{'age':7} {'sd_exp':>7} {'sd_inter':>9} {'mean_inter':>11} {'corr(exp,z)':>12}")
for lab in AGE:
    d = g[g.age_label == lab]
    e, inter, z = d.eloundou_beta.values, d.exp_x_zwage.values, d.z_lnwage.values
    print(f"{lab:7} {e.std():7.3f} {inter.std():9.3f} {inter.mean():11.3f} "
          f"{np.corrcoef(e, z)[0, 1]:12.3f}")
