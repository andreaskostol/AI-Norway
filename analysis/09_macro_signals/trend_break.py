"""
Felles trendbruddstest for maaneds-, kvartals- og aarsserier, etter Steam- og itch.io-figurene.

Modell: log(y) paa lineaer trend og maaneds- eller kvartalsdummyer, estimert paa forperioden.
Forperioden slutter perioden for den som inneholder bruddmaaneden. Projeksjonen har 95 prosent
prediksjonsbaand: Var(x'b) med HAC-kovarians (Newey-West, lag = perioder per aar) pluss
residualvariansen i forperioden.

Klassifisering per brudd:
  for kort      forperioden er under fire aar
  for stoyete   snittet av baandets halvbredde i siste tolv maaneder er over 25 prosent
  brudd opp     minst halvparten av de siste tolv maanedene ligger over baandet
  brudd ned     minst halvparten ligger under baandet
  ingen brudd   ellers
For kvartal brukes siste fire kvartaler og for aar siste aar.

Bruk som modul: test(df, breaks) med df som har kolonnene period og value. Fra kommandolinjen:
  python analysis/09_macro_signals/trend_break.py serie.csv navn ["Tittel"]
skriver figur til analysis/output/macro_signals/fig_<navn>.png/.pdf og en rad per brudd til summary.csv.
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter
import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "analysis" / "output" / "macro_signals"
BREAKS = {"2022m11": pd.Period("2022-11", "M"), "2025m02": pd.Period("2025-02", "M")}
PER_YEAR = {"M": 12, "Q": 4, "Y": 1, "A": 1}
BAND_MAX = 25.0

BLUE, GRAY, INK, MUTED = "#0072B2", "#777777", "#222222", "#666666"
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "DejaVu Sans"], "font.size": 11, "axes.titlesize": 12,
    "axes.titleweight": "semibold", "lines.linewidth": 1.8, "axes.edgecolor": "#999999",
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
})


def to_period(s):
    s = s.astype(str)
    if s.str.fullmatch(r"\d{4}-\d{2}").all():
        return pd.PeriodIndex(s, freq="M")
    if s.str.fullmatch(r"\d{4}Q\d").all():
        return pd.PeriodIndex(s, freq="Q")
    if s.str.fullmatch(r"\d{4}").all():
        return pd.PeriodIndex(s, freq="Y")
    raise ValueError("ukjent periodeformat: " + s.iloc[0])


def design(idx, t0):
    f = idx.freqstr[0]
    X = pd.DataFrame({"const": 1.0, "trend": (idx - t0).map(lambda d: d.n) / PER_YEAR[f]}, index=idx)
    if f in ("M", "Q"):
        season = idx.month if f == "M" else idx.quarter
        for k in range(2, PER_YEAR[f] + 1):
            X[f"s{k}"] = (season == k).astype(float)
    return X


def fit_break(y, brk):
    """y: Series med PeriodIndex og positive verdier. brk: Period (maaned). Returnerer dict og frames."""
    f = y.index.freqstr[0]
    bp = brk.asfreq(y.index.freqstr)  # perioden som inneholder bruddmaaneden
    pre, post = y[y.index < bp], y[y.index >= bp]
    years_pre = len(pre) / PER_YEAR[f]
    X = design(y.index, y.index[0])
    res = sm.OLS(np.log(pre), X.loc[pre.index]).fit(cov_type="HAC", cov_kwds={"maxlags": PER_YEAR[f]})
    Xp = X.loc[post.index]
    yhat = Xp @ res.params
    se_fit = np.sqrt(np.einsum("ij,jk,ik->i", Xp.values, res.cov_params().values, Xp.values))
    se = np.sqrt(se_fit ** 2 + res.mse_resid)
    proj = pd.DataFrame({"actual": post, "proj": np.exp(yhat), "lo": np.exp(yhat - 1.96 * se),
                         "hi": np.exp(yhat + 1.96 * se)}, index=post.index)
    fitted = pd.Series(np.exp(res.fittedvalues), index=pre.index)
    n_last = PER_YEAR[f]
    last = proj.tail(n_last)
    above, below = (proj.actual > proj.hi), (proj.actual < proj.lo)
    band = 100 * (np.exp(1.96 * se[-n_last:]) - 1).mean()
    share_above_last, share_below_last = (last.actual > last.hi).mean(), (last.actual < last.lo).mean()
    if years_pre < 4:
        cls = "for kort"
    elif band > BAND_MAX:
        cls = "for støyete"
    elif share_above_last >= 0.5:
        cls = "brudd opp"
    elif share_below_last >= 0.5:
        cls = "brudd ned"
    else:
        cls = "ingen brudd"
    row = {"pre_start": str(pre.index[0]), "pre_end": str(pre.index[-1]), "pre_years": round(years_pre, 2),
           "post_end": str(post.index[-1]), "n_post": len(post),
           "trend_growth_pct": round(100 * (np.exp(res.params["trend"]) - 1), 2),
           "gap_last12_pct": round(100 * (last.actual.sum() / last.proj.sum() - 1), 1),
           "band_halfwidth_pct": round(band, 1), "share_outside": round((above | below).mean(), 2),
           "share_above": round(above.mean(), 2), "share_below": round(below.mean(), 2),
           "share_above_last12": round(share_above_last, 2), "share_below_last12": round(share_below_last, 2),
           "class": cls}
    return row, fitted, proj


def xnum(idx):
    return np.array([p.start_time.year + (p.start_time.dayofyear - 1) / 365.25 for p in idx]) + \
        {"M": 1 / 24, "Q": 1 / 8, "Y": 0.5}[idx.freqstr[0]]


def plot(y, results, name, title, source, unit="per måned"):
    fig, axs = plt.subplots(1, len(results), figsize=(6.2 * len(results), 4.4), sharey=True)
    for ax, (bname, (row, fitted, proj)) in zip(np.atleast_1d(axs), results.items()):
        ax.plot(xnum(y.index), y.values, color=BLUE, label="Faktisk")
        ax.plot(xnum(fitted.index), fitted.values, color=GRAY, linewidth=0.9, alpha=0.6)
        xp = xnum(proj.index)
        ax.fill_between(xp, proj.lo, proj.hi, color="#BBBBBB", alpha=0.35, linewidth=0)
        ax.plot(xp, proj.proj, color=GRAY, linestyle="--", label="Trend før brudd")
        if y.index.freqstr[0] in "YA":  # aarsserier: vis punktene, ett aar etter brudd gir ingen linje
            ax.plot(xnum(y.index), y.values, "o", color=BLUE, markersize=4)
            err = np.vstack([(proj.proj - proj.lo).values, (proj.hi - proj.proj).values])
            ax.errorbar(xp, proj.proj.values, yerr=err, fmt="o", color=GRAY, markersize=4, capsize=3, linewidth=1)
        ax.axvline(xnum(pd.PeriodIndex([BREAKS[bname]]))[0] - 1 / 24, color="#AAAAAA", linestyle=":", linewidth=1.1)
        ax.set_yscale("log")
        lims = [min(y.min(), proj.lo.min()) / 1.1 for _, _, proj in results.values()] + \
               [max(y.max(), proj.hi.max()) * 1.1 for _, _, proj in results.values()]
        ax.set_ylim(min(lims), max(lims))
        ax.yaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}".replace(",", " ")))
        ax.yaxis.set_minor_formatter(NullFormatter())
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        ax.grid(True, axis="y", color="#DDDDDD", linewidth=0.8, which="both")
        ax.set_axisbelow(True)
        lab = {"2022m11": "Brudd nov. 2022 (ChatGPT)", "2025m02": "Brudd feb. 2025 (agentisk koding)"}[bname]
        ax.set_title(lab, loc="left")
        gap = f"{row['gap_last12_pct']:+.1f}".replace(".", ",").replace("-", "−")
        ax.text(0.02, 0.97, f"{row['class']}\nsiste år mot trend: {gap} %\nbånd ±{row['band_halfwidth_pct']:.0f} %".replace(".", ","),
                transform=ax.transAxes, va="top", fontsize=9.5, color=INK,
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="none", pad=2))
    np.atleast_1d(axs)[0].set_ylabel(unit)
    np.atleast_1d(axs)[0].legend(loc="lower right", frameon=False, fontsize=9.5)
    fig.suptitle(title, x=0.01, ha="left", fontsize=13.5, fontweight="semibold", color=INK)
    season = " med sesongdummyer" if y.index.freqstr[0] in "MQ" else ""
    fig.text(0.01, -0.02, f"Trend: log-lineær{season}, estimert på førperioden, projisert med 95 % bånd "
             "(HAC). Kilde: " + source, fontsize=8.5, color=MUTED, ha="left", va="top", wrap=True)
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"fig_{name}.{ext}", dpi=150, bbox_inches="tight")
    plt.close(fig)


def test(df, name, title=None, source="", unit="per måned", breaks=BREAKS, start=None, end=None):
    """df: kolonnene period og value. Returnerer liste med en rad per brudd og lagrer figur."""
    y = pd.Series(df["value"].astype(float).values, index=to_period(df["period"])).sort_index()
    if start:
        y = y[y.index >= pd.Period(start, y.index.freqstr)]
    if end:
        y = y[y.index <= pd.Period(end, y.index.freqstr)]
    y = y.dropna()
    if (y <= 0).any():
        raise ValueError(f"{name}: null eller negative verdier, velg senere start")
    results = {b: fit_break(y, p) for b, p in breaks.items()}
    plot(y, results, name, title or name, source, unit)
    return [{"series": name, "title": title or name, "freq": y.index.freqstr[0], "break": b, **r[0]}
            for b, r in results.items()]


if __name__ == "__main__":
    path, name = sys.argv[1], sys.argv[2]
    rows = test(pd.read_csv(path), name, sys.argv[3] if len(sys.argv) > 3 else name, source=path)
    out = OUT / "summary.csv"
    old = pd.read_csv(out) if out.exists() else pd.DataFrame({"series": []})
    pd.concat([old[old.series != name], pd.DataFrame(rows)]).to_csv(out, index=False)
    print(pd.DataFrame(rows).T)
