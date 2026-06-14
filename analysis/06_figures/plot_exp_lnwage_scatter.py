"""Scatter of Eloundou exposure vs. ln(pre-ChatGPT wage), by age group, private sector.

Unit: occupation (STYRK08 4-digit) x age decade.
Wage: full-time-equivalent monthly wage (kontantlonn / stillingspst*100),
count-weighted over 2021m01-2022m10 (pre-ChatGPT).
Sector: sekt==2 (private; sekt==1 is the public residual, see 09_*.mdata).
Age groups (alder_gr): 1=21-30, 2=31-40, 3=41-50, 4=51-60 -> four panels.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
INFILE = BASE / "microdata-output" / "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv"
ELOFILE = BASE / "data" / "ai_exposure" / "styrk08_eloundou_beta_mapping.csv"
OUT_DATA = BASE / "analysis" / "output" / "occ_age_exp_wage_prechatgpt.csv"
OUT_FIG = BASE / "analysis" / "output" / "figures" / "interaction" / "figure_exp_lnwage_by_age"
OUT_FIG.parent.mkdir(parents=True, exist_ok=True)

PRE_END = "2022-10-16"          # last pre-ChatGPT status date
PRIVATE = "2"                    # sekt==2 = private
AGE = {"1": "21–30", "2": "31–40", "3": "41–50", "4": "51–60"}

# ---- load & reshape -------------------------------------------------------
df = pd.read_csv(INFILE, dtype={"yrke4": str, "alder_gr": str, "sekt": str,
                                "variable": str})
df["value"] = pd.to_numeric(df["value"], errors="coerce")
df["date"] = pd.to_datetime(df["date"])
pre = df[df["date"] <= PRE_END]

# sanity check: which sector is larger (private should dominate)
chk = (pre[pre.variable == "count"].groupby("sekt")["value"].sum())
print("person-months by sekt (1=public,2=private):", chk.to_dict())

wide = (pre[pre.variable.isin(["count", "kontantlonn", "stillingspst"])]
        .pivot_table(index=["date", "yrke4", "alder_gr", "sekt"],
                     columns="variable", values="value")
        .reset_index())

priv = wide[wide.sekt == PRIVATE].dropna(
    subset=["count", "kontantlonn", "stillingspst"])
# need positive earnings and a non-marginal position to scale to full time
priv = priv[(priv["count"] > 0) & (priv["kontantlonn"] > 0)
            & (priv["stillingspst"] >= 10)]

# full-time-equivalent monthly wage: scale earnings to a 100% position.
# CAVEAT: kontantlonn and stillingspst are CELL MEANS (over workers), so this is
# a ratio-of-means, not the mean of individual FTE = mean(wage_i/pos_i). With
# positive wage-position covariance (part-timers paid less) this slightly
# UNDERSTATES the FTE mean, and the bias varies across cells. For an exact
# measure, add an individual-level FTE variable to the microdata extract, or use
# the hourly wage (timelonn), which needs no position adjustment.
priv = priv.assign(fte_wage=priv["kontantlonn"] * 100.0 / priv["stillingspst"])

# ---- count-weighted mean FTE wage per occupation x age -------------------
priv = priv.assign(wsum=priv["count"] * priv["fte_wage"])
g = (priv.groupby(["yrke4", "alder_gr"])
         .agg(wsum=("wsum", "sum"), n_obs=("count", "sum"))
         .reset_index())
g["mean_wage"] = g["wsum"] / g["n_obs"]      # full-time-equivalent monthly wage
g["ln_wage"] = np.log(g["mean_wage"])

# ---- merge Eloundou exposure ---------------------------------------------
elo = pd.read_csv(ELOFILE, dtype={"styrk08": str})
g = g.merge(elo[["styrk08", "eloundou_beta"]], left_on="yrke4",
            right_on="styrk08", how="inner").drop(columns="styrk08")

g = g[g.alder_gr.isin(AGE)].copy()
g["age_label"] = g.alder_gr.map(AGE)

out = (g[["yrke4", "alder_gr", "age_label", "eloundou_beta",
          "mean_wage", "ln_wage", "n_obs"]]
       .sort_values(["alder_gr", "yrke4"]))
OUT_DATA.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_DATA, index=False)
print(f"wrote {OUT_DATA}  ({len(out)} occupation-age cells)")

# ---- four-panel scatter ---------------------------------------------------
plt.rcParams.update({"font.size": 12, "axes.titlesize": 14})
fig, axes = plt.subplots(2, 2, figsize=(11, 9), sharex=True, sharey=True)
for ax, (code, label) in zip(axes.flat, AGE.items()):
    d = g[g.alder_gr == code]
    x, y, w = d.eloundou_beta.values, d.ln_wage.values, d.n_obs.values
    ax.scatter(x, y, s=2.5 * np.sqrt(w), alpha=0.35, color="#2171B5",
               edgecolor="none")
    # count-weighted OLS fit
    b1, b0 = np.polyfit(x, y, 1, w=np.sqrt(w))
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, b0 + b1 * xs, color="#08306B", lw=2)
    # weighted R^2
    yhat = b0 + b1 * x
    sw = w / w.sum()
    ybar = np.sum(sw * y)
    r2 = 1 - np.sum(w * (y - yhat) ** 2) / np.sum(w * (y - ybar) ** 2)
    ax.set_title(f"{label}   (slope={b1:.2f}, $R^2$={r2:.2f}, n={len(d)})")
    ax.grid(alpha=0.25)

for ax in axes[-1]:
    ax.set_xlabel("Eloundou AI exposure (β)")
for ax in axes[:, 0]:
    ax.set_ylabel("ln(FTE mean wage), 2021m1–2022m10")

fig.suptitle("AI exposure vs. pre-ChatGPT log wage by age group "
             "(private sector, occupation-level)", fontsize=15)
fig.text(0.5, 0.005,
         "Each dot = STYRK08 4-digit occupation; size ∝ √(person-months). "
         "Wage = count-weighted full-time-equivalent (kontantlønn ÷ stillingsprosent), "
         "private sector. Fit and R² are person-month-weighted.",
         ha="center", fontsize=9)
fig.tight_layout(rect=[0, 0.02, 1, 0.97])
for ext in ("pdf", "png"):
    fig.savefig(f"{OUT_FIG}.{ext}", dpi=150, bbox_inches="tight")
print(f"wrote {OUT_FIG}.pdf / .png")
