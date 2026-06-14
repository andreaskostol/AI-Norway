"""Event-study plots for the extended-M3 interaction variants.

Two families, both per timing (ChatGPT / agentic), 4 age panels:
  (1) compare : overlay the INTERACTION path delta3_k of every INT variant,
                each shown per 1 SD of its own construct (coef * sd_int) so the
                paths are on a common Delta-log axis.
  (2) detail  : per variant, the three full-model paths (exposure, ln wage,
                interaction), all per 1 SD. One figure per variant.

All paths are Delta log outcome per 1 SD; k = -1 reference. PDF only.

Usage: python plot_ca_int_es.py [count|nyjobb]   (default count)
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

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients" / f"coef_ca_int_es{SUF}.csv"
FIGS = BASE / "analysis" / "output" / "figures" / "interaction"
FIGS.mkdir(parents=True, exist_ok=True)
AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}

# INT variants: key -> (colour, label, marker, linestyle)
VAR_STYLE = {
    "prod":     ("#999999", "raw product (current M3)", "o", "-"),
    "rect0":    ("#08519C", "rectified, both > mean",   "s", "-"),
    "rect1":    ("#238B45", "rectified, both > +1 SD",  "^", "-"),
    "corner75": ("#D94801", "corner p75 × p75",         "D", "--"),
    "corner80": ("#6A51A3", "corner p80 × p80",         "v", "--"),
}
# full-model terms for the detail figures
TERMS = [("exp", "exposure", "#08519C", "o"),
         ("wage", "ln wage", "#D94801", "s"),
         ("int", "interaction", "#238B45", "^")]

SPECS = [
    dict(timing="chatgpt", ref_ym=2022 * 12 + 10, launch=datetime(2022, 11, 1),
         tag="ref. Oct 2022 = ChatGPT", fn="chatgpt"),
    dict(timing="agentic", ref_ym=2025 * 12 + 4, launch=datetime(2025, 5, 1),
         tag="re-anchored Apr 2025 = agentic", fn="agentic"),
]


def k_to_date(k, ref_ym):
    ym = ref_ym + 1 + k
    y, m = (ym - 1) // 12, (ym - 1) % 12 + 1
    return datetime(y, m, 1)


def disp(d):
    """per-SD display: interaction scaled by sd_int; exp/wage already per-SD."""
    out = d.copy()
    m = out["term"] == "int"
    out.loc[m, "coef"] = out.loc[m, "coef"] * out.loc[m, "sd_int"]
    out.loc[m, "se"] = out.loc[m, "se"] * out.loc[m, "sd_int"]
    return out


df = disp(pd.read_csv(COEF))

note_common = ("Private sector, Poisson PPML, occ + month FE; SE clustered at "
               "occupation. Model: z(exp), z(ln FTE wage) and one interaction "
               "term, each × event-time (k=−1 ref). All paths are Δ{0} per 1 SD "
               "of the construct. Dashed grey = reference launch.")

# ---------------- (1) interaction-comparison figures ----------------
for spec in SPECS:
    d0 = df[(df.timing == spec["timing"]) & (df.term == "int")].copy()
    d0["date"] = d0["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))
    plt.rcParams.update({"font.size": 16, "axes.titlesize": 18})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    for ax, (code, lab) in zip(axes.flat, AGE.items()):
        for v, (col, vlab, mk, ls) in VAR_STYLE.items():
            d = d0[(d0.age_group == code) & (d0.variant == v)].sort_values("date")
            ax.plot(d.date, d.coef, color=col, lw=1.5, marker=mk, ms=3,
                    ls=ls, label=vlab)
        ax.axhline(0, color="black", lw=0.7)
        ax.axvline(spec["launch"], color="grey", ls="--", lw=1.1)
        ax.set_ylim(-0.06, 0.06)   # clip: rect>+1SD is wild in thin youngest tail
        ax.set_title(lab); ax.grid(alpha=0.2)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    axes.flat[0].legend(loc="lower left", fontsize=11, framealpha=0.0,
                        borderpad=0.3, labelspacing=0.3, handlelength=1.8)
    for ax in axes[:, 0]:
        ax.set_ylabel(rf"$\delta_k^{{int}}$: $\Delta${YLAB} per 1 SD")
    fig.suptitle(f"Interaction event study across INT specifications "
                 f"({OUTCOME}); {spec['tag']}", fontsize=20)
    note = ("Each line is the interaction term δ_k from a model that also "
            "includes the free linear z(exp) and z(ln wage) gradients; only the "
            "interaction's definition changes. y-axis clipped to ±0.06; the "
            "rectified-at-+1SD path is noisy in the youngest group (thin tail "
            "support) and runs off-scale pre-period. " + note_common.format(YLAB[-4:]))
    fig.text(0.5, 0.01, textwrap.fill(note, width=110), ha="center",
             va="bottom", fontsize=13)
    fig.tight_layout(rect=[0, 0.10, 1, 0.96])
    out = FIGS / f"figure_ca_int_es_compare_{spec['fn']}{SUF}.pdf"
    fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"wrote {out}")

# ---------------- (2) per-variant detail figures ----------------
for spec in SPECS:
    for v, (vcol, vlab, vmk, vls) in VAR_STYLE.items():
        d0 = df[(df.timing == spec["timing"]) & (df.variant == v)].copy()
        d0["date"] = d0["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))
        plt.rcParams.update({"font.size": 16, "axes.titlesize": 18})
        fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True,
                                 sharey=True)
        for ax, (code, lab) in zip(axes.flat, AGE.items()):
            for term, tlab, col, mk in TERMS:
                d = d0[(d0.age_group == code) & (d0.term == term)
                       ].sort_values("date")
                lo, hi = d.coef - 1.96 * d.se, d.coef + 1.96 * d.se
                ax.fill_between(d.date, lo, hi, color=col, alpha=0.12)
                lw = 2.2 if term == "int" else 1.4
                ax.plot(d.date, d.coef, color=col, lw=lw, marker=mk, ms=3,
                        label=tlab)
            ax.axhline(0, color="black", lw=0.7)
            ax.axvline(spec["launch"], color="grey", ls="--", lw=1.1)
            ax.set_title(lab); ax.grid(alpha=0.2)
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        axes.flat[0].legend(loc="lower left", fontsize=12, framealpha=0.0,
                            borderpad=0.3, labelspacing=0.3, handlelength=1.6)
        for ax in axes[:, 0]:
            ax.set_ylabel(rf"$\delta_k$: $\Delta${YLAB} per 1 SD")
        fig.suptitle(f"Full model, INT = {vlab} ({OUTCOME}); {spec['tag']}",
                     fontsize=20)
        note = ("Interaction term (green, bold) defined as "
                f"{vlab}; shown alongside the free linear exposure and ln-wage "
                "gradients. " + note_common.format(YLAB[-4:]))
        fig.text(0.5, 0.01, textwrap.fill(note, width=110), ha="center",
                 va="bottom", fontsize=13)
        fig.tight_layout(rect=[0, 0.10, 1, 0.96])
        out = FIGS / f"figure_ca_int_es_{v}_{spec['fn']}{SUF}.pdf"
        fig.savefig(out, bbox_inches="tight"); plt.close(fig)
        print(f"wrote {out}")
