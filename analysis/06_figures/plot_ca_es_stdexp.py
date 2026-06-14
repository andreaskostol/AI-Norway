"""CA event-study plots: per age group, the three full-model term paths
(exposure, ln wage, exp x wage) plus a thin grey reference line = exposure when
it is the ONLY regressor (model 1). PDF only.

Usage:  python plot_ca_es_stdexp.py [count|nyjobb]   (default count)
Reads coef_ca_es_stdexp[_<outcome>].csv (timing, age_group, term, k, coef, se).
"""
import sys
import textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path

OUTCOME = sys.argv[1] if len(sys.argv) > 1 else "count"
assert OUTCOME in ("count", "nyjobb")
SUF = "" if OUTCOME == "count" else f"_{OUTCOME}"
YLAB = {"count": "log emp.", "nyjobb": "log hires"}[OUTCOME]
ESTIMATOR = sys.argv[2] if len(sys.argv) > 2 else "ppml"
assert ESTIMATOR in ("ppml", "olslog")
ESTTAG = ""
if ESTIMATOR == "olslog":
    SUF += "_olslog"
    ESTTAG = " [OLS log, wtd]"

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients" / f"coef_ca_es_stdexp{SUF}.csv"
FIGS = BASE / "analysis" / "output" / "figures" / "interaction"
FIGS.mkdir(parents=True, exist_ok=True)
AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}

# full-model terms (key, label, colour, marker)
TERMS = [("exp", "exposure", "#08519C", "o"),
         ("wage", "ln wage", "#D94801", "s"),
         ("exp_x_wage", "exp × wage", "#238B45", "^")]

SPECS = [
    dict(timing="chatgpt", out=f"figure_ca_es_grid_stdexp{SUF}.pdf",
         ref_ym=2022 * 12 + 10, launch=datetime(2022, 11, 1),
         title=f"CA event study, all terms ({OUTCOME}){ESTTAG}; ref. Oct 2022 = ChatGPT"),
    dict(timing="agentic", out=f"figure_ca_es_decade_agentic_stdexp{SUF}.pdf",
         ref_ym=2025 * 12 + 4, launch=datetime(2025, 5, 1),
         title=f"CA event study, all terms ({OUTCOME}){ESTTAG}; re-anchored Apr 2025 = agentic"),
]


def k_to_date(k, ref_ym):
    ym = ref_ym + 1 + k
    y, m = (ym - 1) // 12, (ym - 1) % 12 + 1
    return datetime(y, m, 1)


df = pd.read_csv(COEF)
for spec in SPECS:
    d0 = df[df.timing == spec["timing"]].copy()
    d0["date"] = d0["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))

    plt.rcParams.update({"font.size": 18, "axes.titlesize": 21})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    for ax, (code, lab) in zip(axes.flat, AGE.items()):
        # reference: exposure-only (M1), thin grey, no CI, drawn first (behind)
        r = d0[(d0.age_group == code) & (d0.term == "exp_only")].sort_values("date")
        ax.plot(r.date, r.coef, color="black", lw=1.8, ls="-",
                label="exposure (M1, ref.)", zorder=1)
        for term, tlab, col, mk in TERMS:
            d = d0[(d0.age_group == code) & (d0.term == term)].sort_values("date")
            lo, hi = d.coef - 1.96 * d.se, d.coef + 1.96 * d.se
            ax.fill_between(d.date, lo, hi, color=col, alpha=0.12, zorder=2)
            ax.plot(d.date, d.coef, color=col, lw=1.5, marker=mk, ms=3,
                    label=tlab, zorder=3)
        ax.axhline(0, color="black", lw=0.7)
        ax.axvline(spec["launch"], color="grey", ls="--", lw=1.1)
        ax.set_title(lab)
        ax.grid(alpha=0.2)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes.flat[0].legend(loc="lower left", fontsize=12, framealpha=0.0,
                        borderpad=0.3, labelspacing=0.3, handlelength=1.5)
    for ax in axes[:, 0]:
        ax.set_ylabel(rf"$\delta_k$: $\Delta${YLAB} per SD")
    fig.suptitle(spec["title"], fontsize=21)
    note = ("Private sector. Full model: z(exposure), z(ln FTE wage) and their "
            "interaction, each × event-time dummies (k=−1 ref). Black line = "
            "exposure estimated alone (M1). Poisson PPML, occ + month FE; "
            "95% CI bands; SE clustered at occupation. Dashed = reference launch.")
    fig.text(0.5, 0.01, textwrap.fill(note, width=95), ha="center",
             va="bottom", fontsize=18)
    fig.tight_layout(rect=[0, 0.12, 1, 0.96])
    fig.savefig(FIGS / spec["out"], bbox_inches="tight")
    print(f"wrote {FIGS / spec['out']}")
