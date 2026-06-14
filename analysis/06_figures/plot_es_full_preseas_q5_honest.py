"""
plot_es_full_preseas_q5_honest.py

Q5-vs-Q3 full-window seasonally adjusted (preseas, 2021-2024 step 1)
Poisson event-study coefficients with Rambachan and Roth (2023)
Delta^SDRM(Mbar) sensitivity bounds. Same approximation as
plot_microdata_es_decade_q3_q5_honest.py:

  Smoothness:         |B_{t+1} - 2 B_t + B_{t-1}| <= Mbar * max|second-diff
                      of pre-period|
  Relative magnitude: |B_t| <= Mbar * max|delta_pre|
  Delta^SD approx: linear pre-trend extrapolation +/- M_SD * t (t+1) / 2
  Honest 95% CI for tau_t = delta_hat_t - [B_lo, B_hi] +/- 1.96 * SE.

Seasonal adjustment matters here: M_SD is calibrated from the max
second difference of the pre-period path, which the raw seasonal
sawtooth inflates. The script prints the calibration for both the
adjusted and the raw full-window series.

Output: analysis/output/figures/figure_es_full_preseas_q5_honest.pdf
"""

import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

BASE_DT = datetime(2022, 11, 1)
CHATGPT = mdates.date2num(BASE_DT)
AGENTIC = mdates.date2num(datetime(2025, 5, 1))

BASE_DIR = os.path.join(os.path.dirname(__file__), "..", "..")
COEF_DIR = os.path.join(BASE_DIR, "analysis", "output", "coefficients")
COEF = os.path.join(COEF_DIR, "coef_microdata_es_decade_q3_full_preseas.csv")
COEF_RAW = os.path.join(COEF_DIR, "coef_microdata_es_decade_q3_full.csv")
FIG_DIR = os.path.join(BASE_DIR, "analysis", "output", "figures")

AGE_TITLES = {1: "Early career (21-30)", 2: "31-40",
              3: "41-50", 4: "Senior (51-60)"}
AGE_ORDER = [1, 2, 3, 4]
COL_POINT = "#08306B"
COL_HONEST = "#D55E00"

MBAR = 1.0


def healy_style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.linewidth": 0.5,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#333333", "axes.grid": True,
        "grid.color": "#BBBBBB", "grid.linewidth": 0.7, "grid.linestyle": "-",
        "xtick.major.width": 0.4, "ytick.major.width": 0.4,
        "xtick.color": "#333333", "ytick.color": "#333333",
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
        "font.size": 18, "axes.titlesize": 20, "axes.labelsize": 18,
        "xtick.labelsize": 16, "ytick.labelsize": 16, "legend.fontsize": 18,
        "lines.linewidth": 1.4,
    })


def linear_extrap_slope(pre_k, pre_coef, pre_se):
    w = 1.0 / (pre_se ** 2 + 1e-12)
    W = np.diag(w)
    X = np.vstack([np.ones_like(pre_k), pre_k]).T
    beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ pre_coef)
    return float(beta[1]), float(beta[0])


def sdrm_bias_bounds(pre_k, pre_coef, pre_se, post_k, Mbar):
    M_SD = Mbar * float(np.max(np.abs(np.diff(pre_coef, n=2))))
    M_RM = Mbar * float(np.max(np.abs(pre_coef)))
    slope, intercept = linear_extrap_slope(pre_k, pre_coef, pre_se)

    extrap = intercept + slope * post_k
    t = post_k + 1
    sd_halfwidth = M_SD * t * (t + 1) / 2.0
    sd_lo, sd_hi = extrap - sd_halfwidth, extrap + sd_halfwidth
    rm_lo, rm_hi = -M_RM * np.ones_like(post_k), M_RM * np.ones_like(post_k)

    B_lo = np.maximum(sd_lo, rm_lo)
    B_hi = np.minimum(sd_hi, rm_hi)
    return B_lo, B_hi, M_SD, M_RM


def calib(d, a):
    sub = d[(d["age_group"] == a) & (d["ai_q"] == 5)].sort_values("k")
    pre = sub[sub["k"] < -1]
    return (float(np.max(np.abs(np.diff(pre["coef"].to_numpy(), n=2)))),
            float(np.max(np.abs(pre["coef"].to_numpy()))))


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    healy_style()

    d = pd.read_csv(COEF)
    d_raw = pd.read_csv(COEF_RAW)
    d = d[d["ai_q"] == 5].copy()
    d["date"] = [BASE_DT + pd.DateOffset(months=int(k)) for k in d["k"]]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    sdrm_diag = {}
    for ax, a in zip(axes.flatten(), AGE_ORDER):
        sub = d[d["age_group"] == a].sort_values("k").reset_index(drop=True)
        pre = sub[sub["k"] < -1].reset_index(drop=True)
        post = sub[sub["k"] >= 0].reset_index(drop=True)

        ci_lo = sub["coef"] - 1.96 * sub["se"]
        ci_hi = sub["coef"] + 1.96 * sub["se"]
        ax.fill_between(sub["date"], ci_lo, ci_hi,
                        color=COL_POINT, alpha=0.15)
        ax.plot(sub["date"], sub["coef"], color=COL_POINT, linewidth=1.8)

        post_k = post["k"].to_numpy()
        B_lo, B_hi, M_SD, M_RM = sdrm_bias_bounds(
            pre["k"].to_numpy(), pre["coef"].to_numpy(),
            pre["se"].to_numpy(), post_k, MBAR)
        sdrm_diag[a] = (M_SD, M_RM)

        post_coef = post["coef"].to_numpy()
        post_se = post["se"].to_numpy()
        honest_lo = post_coef - B_hi - 1.96 * post_se
        honest_hi = post_coef - B_lo + 1.96 * post_se
        ax.fill_between(post["date"], honest_lo, honest_hi,
                        color=COL_HONEST, alpha=0.18)

        ax.axhline(y=0.0, color="#AAAAAA", linestyle="-", linewidth=0.5)
        ax.axvline(x=CHATGPT, color="#888888", linestyle="--",
                   linewidth=0.8, alpha=0.7)
        ax.axvline(x=AGENTIC, color="#888888", linestyle=":",
                   linewidth=0.8, alpha=0.7)
        ax.set_title(AGE_TITLES[a])
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(-0.20, 0.10)

    handles = [
        Line2D([0], [0], color=COL_POINT, lw=2.5,
               label="Q5 vs Q3, seasonally adjusted"),
        Patch(facecolor=COL_POINT, alpha=0.15,
              label="95% CI (parallel trends)"),
        Patch(facecolor=COL_HONEST, alpha=0.30,
              label=r"Honest 95% CI, $\Delta^{SDRM}(\bar{M}=1)$"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False,
               bbox_to_anchor=(0.5, 1.02), fontsize=17)
    fig.autofmt_xdate(rotation=0, ha="center")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = os.path.join(FIG_DIR, "figure_es_full_preseas_q5_honest.pdf")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out}")

    print()
    print(f"Delta^SDRM(Mbar={MBAR}) calibration, adjusted vs raw pre-period:")
    print(f"  {'group':25s}  {'M_SD adj':>9s} {'M_SD raw':>9s}"
          f"  {'M_RM adj':>9s} {'M_RM raw':>9s}")
    for a in AGE_ORDER:
        m_sd_r, m_rm_r = calib(d_raw, a)
        m_sd_a, m_rm_a = sdrm_diag[a]
        print(f"  {AGE_TITLES[a]:25s}  {m_sd_a:>9.4f} {m_sd_r:>9.4f}"
              f"  {m_rm_a:>9.4f} {m_rm_r:>9.4f}")


if __name__ == "__main__":
    main()
