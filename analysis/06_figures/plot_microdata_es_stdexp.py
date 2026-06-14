"""Event-study plots (per age group) for the continuous standardized-exposure
Poisson specification. Mirrors figure_microdata_poisson_es_grid_q3 and
figure_microdata_es_decade_agentic_q3, but the treatment is z(exposure) rather
than quintiles, so each age group has a single delta_k path.

Estimating equation (per decade age group a; estimated in the R scripts):

    log E[count_{j,t}] = alpha_j + beta_t
                       + sum_{k != -1} delta_k * z(exp_j) * 1{k(t)=k}

    j = occupation (STYRK08 4-digit), t = month, alpha_j occ FE, beta_t month FE,
    z(exp_j) = Eloundou beta standardized across occupations (mean 0, SD 1),
    k = event time relative to the reference month (k = -1 omitted),
    delta_k = effect on log employment per 1 SD exposure at event time k.
    Private sector; SE clustered at occupation.

PDF only.
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients"
FIGS = BASE / "analysis" / "output" / "figures"
AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}

SPECS = [
    dict(csv="coef_microdata_es_decade_stdexp.csv",
         out="figure_microdata_es_grid_stdexp.pdf",
         ref_ym=2022 * 12 + 10, launch=datetime(2022, 11, 1),
         title="Cell-level Poisson event study, continuous exposure "
               "(ref. Oct 2022 = ChatGPT)"),
    dict(csv="coef_microdata_es_decade_agentic_stdexp.csv",
         out="figure_microdata_es_decade_agentic_stdexp.pdf",
         ref_ym=2025 * 12 + 4, launch=datetime(2025, 5, 1),
         title="Cell-level Poisson event study, continuous exposure "
               "(re-anchored to Apr 2025 = agentic)"),
]


def k_to_date(k, ref_ym):
    ym = ref_ym + 1 + k          # k = ym - (ref_ym + 1)
    y, m = (ym - 1) // 12, (ym - 1) % 12 + 1
    return datetime(y, m, 1)


for spec in SPECS:
    df = pd.read_csv(COEF / spec["csv"])
    df["date"] = df["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))
    df["lo"] = df["coef"] - 1.96 * df["se"]
    df["hi"] = df["coef"] + 1.96 * df["se"]

    plt.rcParams.update({"font.size": 12, "axes.titlesize": 14})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), sharex=True, sharey=True)
    for ax, (code, lab) in zip(axes.flat, AGE.items()):
        d = df[df.age_group == code].sort_values("date")
        ax.fill_between(d.date, d.lo, d.hi, color="#6BAED6", alpha=0.35)
        ax.plot(d.date, d.coef, color="#08519C", lw=1.6, marker="o", ms=3)
        ax.axhline(0, color="black", lw=0.7)
        ax.axvline(spec["launch"], color="#CB181D", ls="--", lw=1.2)
        ax.set_title(f"{lab}   (n_occ={int(d.n_occ.iloc[0])})")
        ax.grid(alpha=0.2)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    for ax in axes[:, 0]:
        ax.set_ylabel(r"$\delta_k$: $\Delta$log emp. per SD exposure")
    fig.suptitle(spec["title"], fontsize=14)
    fig.text(0.5, 0.005,
             "Private sector. Poisson PPML with occupation + month FE; "
             "treatment = z(Eloundou β) × event-time dummies; "
             "95% CI, SE clustered at occupation. Dashed line = reference launch.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=[0, 0.02, 1, 0.97])
    fig.savefig(FIGS / spec["out"], bbox_inches="tight")
    print(f"wrote {FIGS / spec['out']}")
