"""Yagan-style CA event-study plots: counterpart to plot_ca_es_stdexp.py
but reading the Yagan ratio coefficient file (coef_ca_es_yagan.csv).

For each outcome produces two PDFs:
  ChatGPT-anchored grid:  figure_ca_es_yagan_grid_<outcome>.pdf
  Agentic-anchored:       figure_ca_es_yagan_agentic_<outcome>.pdf

outcome in {count, nyjobb}.

Usage:  python plot_ca_es_yagan.py
        Produces 4 PDFs in analysis/output/figures/interaction/.

Schema of coef_ca_es_yagan.csv:
    outcome, timing, age_group, term, k, coef, se, n_obs
    term in {exp, wage, exp_x_wage, exp_only}
"""
import sys
import textwrap
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients" / "coef_ca_es_yagan.csv"
FIGS = BASE / "analysis" / "output" / "figures" / "interaction"
FIGS.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}

# full-model term key, label, colour, marker
TERMS = [("exp", "exposure", "#08519C", "o"),
         ("wage", "ln wage", "#D94801", "s"),
         ("exp_x_wage", "exp × wage", "#238B45", "^")]

# y-axis labels by outcome
YLAB = {
    "count":  "Δ (headcount / 12-mo pre-baseline) per SD",
    "nyjobb": "Δ (hires / 12-mo pre-baseline) per SD",
}

OUTCOME_LABEL = {"count":  "employment headcount",
                 "nyjobb": "new hires (round count × ny_jobb)"}

TIMING_SPECS = {
    "chatgpt": dict(ref_ym=2022 * 12 + 10, launch=datetime(2022, 11, 1),
                    tag="ChatGPT", ref_text="Oct 2022"),
    "agentic": dict(ref_ym=2025 * 12 + 4, launch=datetime(2025, 5, 1),
                    tag="agentic", ref_text="Apr 2025"),
}


def k_to_date(k, ref_ym):
    ym = ref_ym + 1 + k
    y, m = (ym - 1) // 12, (ym - 1) % 12 + 1
    return datetime(y, m, 1)


def make_figure(df, outcome, timing, out_path):
    spec = TIMING_SPECS[timing]
    d0 = df[(df.outcome == outcome) & (df.timing == timing)].copy()
    if d0.empty:
        print(f"[skip] no rows for {outcome}/{timing}")
        return
    d0["date"] = d0["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))

    plt.rcParams.update({"font.size": 18, "axes.titlesize": 21})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    for ax, (code, lab) in zip(axes.flat, AGE.items()):
        # exposure-only reference path (black, no CI)
        r = d0[(d0.age_group == code) & (d0.term == "exp_only")] \
            .sort_values("date")
        ax.plot(r.date, r.coef, color="black", lw=1.8, ls="-",
                label="exposure (M1, ref.)", zorder=1)
        for term, tlab, col, mk in TERMS:
            dd = d0[(d0.age_group == code) & (d0.term == term)] \
                .sort_values("date")
            lo, hi = dd.coef - 1.96 * dd.se, dd.coef + 1.96 * dd.se
            ax.fill_between(dd.date, lo, hi, color=col, alpha=0.12, zorder=2)
            ax.plot(dd.date, dd.coef, color=col, lw=1.5, marker=mk, ms=3,
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
        ax.set_ylabel(YLAB[outcome])

    title = (f"CA event study, all terms ({OUTCOME_LABEL[outcome]}); "
             f"Yagan ratio (y / 12-month pre-baseline); "
             f"re-anchored {spec['ref_text']} = {spec['tag']}")
    fig.suptitle(title, fontsize=21)
    note = ("Private sector, microdata.no aggregates. Outcome is the Yagan "
            "ratio y_{c,t} / mean(y_{c, pre-12-month}). Full model: "
            "z(exposure), z(ln FTE wage) and their interaction, each × "
            "event-time dummies (k=−1 ref). Black line = exposure estimated "
            "alone (M1). Linear OLS with occupation + month FE, weighted by "
            "pre-window baseline mean count; 95% CI bands; SE clustered at "
            "occupation. Dashed = reference launch.")
    fig.text(0.5, 0.01, textwrap.fill(note, width=95), ha="center",
             va="bottom", fontsize=18)
    fig.tight_layout(rect=[0, 0.12, 1, 0.96])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out_path}")


def main():
    if not COEF.exists():
        sys.exit(f"missing input: {COEF}")
    df = pd.read_csv(COEF)
    for outcome in ("count", "nyjobb"):
        for timing in ("chatgpt", "agentic"):
            tag = "grid" if timing == "chatgpt" else "agentic"
            out = FIGS / f"figure_ca_es_yagan_{tag}_{outcome}.pdf"
            make_figure(df, outcome, timing, out)


if __name__ == "__main__":
    main()
