"""Firm-FE CA event-study plots: firm-FE analogue of plot_ca_es_stdexp.py.

For each (outcome, fe_spec) combination produces two PDFs (ChatGPT + agentic)
in the same 2x2 panel format as the cell-level figures. Reads the
secure-server output coef_ca_es_firmfe.csv (timing, outcome, fe, age_bin,
term, k, coef, se, n_obs, n_frtk).

Usage:  python plot_ca_es_firmfe.py
        Produces 8 PDFs: outcome in {count, nyjobb} x fe in {occ, quint}
        x timing in {chatgpt, agentic}.
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
COEF = BASE / "analysis-indiv" / "from_secure_server" / "coefficients" / \
    "coef_ca_es_firmfe.csv"
FIGS = BASE / "analysis" / "output" / "figures" / "interaction"
FIGS.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}

# full-model terms (key, label, colour, marker)
TERMS = [("exp", "exposure", "#08519C", "o"),
         ("wage", "ln wage", "#D94801", "s"),
         ("exp_x_wage", "exp × wage", "#238B45", "^")]

YLAB = {"count": "log emp.", "nyjobb": "log hires"}

# Two FE variants run by 6e_ca_es_firmfe.R.
FE_LABELS = {
    "occ":   "firm × occupation FE",
    "quint": "firm × quintile FE",
}

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


def make_figure(d, outcome, fe, timing, out_path):
    spec = TIMING_SPECS[timing]
    d0 = d[(d.timing == timing) & (d.outcome == outcome) & (d.fe == fe)].copy()
    if d0.empty:
        print(f"[skip] no rows for {outcome}/{fe}/{timing}")
        return
    d0["date"] = d0["k"].map(lambda k: k_to_date(k, spec["ref_ym"]))

    plt.rcParams.update({"font.size": 18, "axes.titlesize": 21})
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    for ax, (code, lab) in zip(axes.flat, AGE.items()):
        # reference: exposure-only (M1), thin black, no CI, drawn first
        r = d0[(d0.age_bin == code) & (d0.term == "exp_only")] \
            .sort_values("date")
        ax.plot(r.date, r.coef, color="black", lw=1.8, ls="-",
                label="exposure (M1, ref.)", zorder=1)
        for term, tlab, col, mk in TERMS:
            dd = d0[(d0.age_bin == code) & (d0.term == term)] \
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
        ax.set_ylabel(rf"$\delta_k$: $\Delta${YLAB[outcome]} per SD")

    title = (f"Firm-FE CA event study, all terms ({outcome}); "
             f"re-anchored {spec['ref_text']} = {spec['tag']}; "
             f"{FE_LABELS[fe]}")
    fig.suptitle(title, fontsize=21)
    note = ("Private sector, individual-level firm panel. Full model: "
            "z(exposure), z(ln FTE wage) and their interaction, each x "
            "event-time dummies (k=−1 ref). Black line = exposure estimated "
            f"alone (M1). Poisson PPML, {FE_LABELS[fe]} + firm × month FE; "
            "95% CI bands; SE clustered at foretak. Dashed = reference "
            "launch.")
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
        for fe in ("occ", "quint"):
            for timing in ("chatgpt", "agentic"):
                tag = "grid" if timing == "chatgpt" else "decade_agentic"
                out = FIGS / \
                    f"figure_ca_es_firmfe_{tag}_{outcome}_{fe}.pdf"
                make_figure(df, outcome, fe, timing, out)


if __name__ == "__main__":
    main()
