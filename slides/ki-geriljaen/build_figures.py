"""
build_figures.py

Tegner figurene til KI-geriljaen-dekket fra dashboard.json (release 2026-10,
data til og med juli 2026) i husstilen fra edutech-dekkene (serif, grå/blå,
ingen topp- og høyreramme). Skriver SVG-filer til figures/ og alle tall som
står på lysbildene til figures/numbers.json, slik at ingen tall skrives for
hånd i HTML-en.

Kjøring:  python3 build_figures.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DASH = os.path.join(REPO, "dashboard", "site", "public", "data", "dashboard.json")
COEF = os.path.join(REPO, "analysis", "output", "coefficients")
OUT = os.path.join(HERE, "figures")
os.makedirs(OUT, exist_ok=True)

# Husstil (samme rcParams som plot_mouchel_vs_eloundou.py og occupation_figure.py)
BLUE, GRAY, LIGHT, LABEL, INK = "#2F6FB0", "#999999", "#C8CED4", "#516274", "#333333"
PURPLE = "#7B3F9E"
plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.linewidth": 0.5, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": INK, "axes.grid": True, "grid.color": "#BBBBBB",
    "grid.linewidth": 0.7, "grid.linestyle": "-", "xtick.major.width": 0.4,
    "ytick.major.width": 0.4, "xtick.color": INK, "ytick.color": INK,
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "font.size": 15, "axes.labelsize": 15, "xtick.labelsize": 13, "ytick.labelsize": 13,
    "svg.fonttype": "none",
})

D = json.load(open(DASH, encoding="utf-8"))
P = D["packages"]
DATES = pd.to_datetime(P["by_exposure"]["dates"])
Q1, Q5 = "Quintile 1 (least exposed)", "Quintile 5 (most exposed)"

# De to referansene, som på kiindeksen.no: ChatGPT = oktober 2022 (måneden før
# lanseringen), agentisk KI = januar 2025 (måneden før Claude Code).
REFS = {
    "chatgpt": {"ref": "2022-10-01", "launch": "2022-11-01", "start": "2021-01-01",
                "label": "ChatGPT", "ref_text": "oktober 2022"},
    "agentisk": {"ref": "2025-01-01", "launch": "2025-02-01", "start": "2024-01-01",
                 "label": "Agentisk KI (Claude Code)", "ref_text": "januar 2025"},
}
HEADLINE_MA = 3   # etterslepende glidende snitt i hovedtallet, som i app.js


def series(pkg, facet, col, adj="sa"):
    """Henter én serie som numpy-array i datoens rekkefølge."""
    return np.array(P[pkg]["series"][adj][facet][col], dtype=float)


def reindex(y, ref):
    """Setter serien til 100 i referansemåneden."""
    i = list(DATES).index(pd.Timestamp(ref))
    return 100.0 * y / y[i]


def moving_average(y, k):
    """Etterslepende snitt av de siste k månedene (movingAverage i app.js)."""
    out = np.full_like(y, np.nan)
    for i in range(len(y)):
        if i >= k - 1:
            out[i] = np.mean(y[i - k + 1:i + 1])
    return out


def growth(y, ref):
    """Vekst i prosent fra glattet nivå i referansemåneden til glattet siste måned."""
    s = moving_average(y, HEADLINE_MA)
    i = list(DATES).index(pd.Timestamp(ref))
    return 100.0 * (s[-1] / s[i] - 1.0)


def ki_index(g5, g1):
    """KI-indeksen: relativ vekst, (1+g5)/(1+g1) - 1, i prosentpoeng."""
    return 100.0 * ((1 + g5 / 100) / (1 + g1 / 100) - 1)


def last_row(name):
    """Siste rad i en bootstrap-fil (standardfeil per vintage)."""
    df = pd.read_csv(os.path.join(COEF, name))
    return df.iloc[-1].to_dict()


def no(x, d=1):
    """Norsk tallformat med komma og minustegn."""
    s = f"{x:.{d}f}".replace(".", ",").replace("-", "−")
    if x > 0:
        s = "+" + s
    return s


def mark_launch(ax, ref, ymin, ymax, text):
    """Stiplet linje i lanseringsmåneden med etikett."""
    x = pd.Timestamp(REFS[ref]["launch"])
    ax.axvline(x, color="#777777", linestyle=":", linewidth=1.2, zorder=1)
    ax.text(x, ymax, " " + text, color="#777777", fontsize=12, va="top", ha="left")


def line_chart(fname, lines, ref, ylabel, ylim=None, end_labels=True):
    """
    Tegner linjer indeksert til referansemåneden. lines = liste av
    (navn, verdier, farge, linjebredde, stiplet).
    """
    fig, ax = plt.subplots(figsize=(11, 5.4))
    start = pd.Timestamp(REFS[ref]["start"])
    m = DATES >= start
    ends = []
    for name, y, color, lw, dashed in lines:
        yi = reindex(y, REFS[ref]["ref"])
        ax.plot(DATES[m], yi[m], color=color, linewidth=lw,
                linestyle="--" if dashed else "-", zorder=3 if lw > 1.6 else 2)
        ends.append([yi[m][-1], name, color])
    if end_labels:
        # Dytter etiketter fra hverandre når de ligger for tett (minst 0,45 enheter mellom).
        lo0, hi0 = ax.get_ylim()
        gap = (hi0 - lo0) * 0.055
        ends.sort(key=lambda e: e[0])
        pos = [e[0] for e in ends]
        for k in range(1, len(pos)):
            if pos[k] - pos[k - 1] < gap:
                pos[k] = pos[k - 1] + gap
        for (v, name, color), yp in zip(ends, pos):
            ax.text(DATES[m][-1] + pd.Timedelta(days=12), yp, name, color=color, fontsize=12, va="center", ha="left")
    ax.axhline(100, color="#555555", linewidth=0.8, zorder=1)
    if ylim:
        ax.set_ylim(*ylim)
    lo, hi = ax.get_ylim()
    mark_launch(ax, ref, lo, hi, REFS[ref]["label"])
    ax.set_ylabel(ylabel)
    ax.set_xlim(start, DATES[-1] + pd.Timedelta(days=300))
    ax.grid(axis="x", visible=False)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=7))
    if ref == "chatgpt":
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
            lambda v, _: mdates.num2date(v).strftime("%b %Y").replace("Jan", "jan.").replace("Jul", "jul.")))
    ax.set_xticks([t for t in ax.get_xticks() if t <= mdates.date2num(DATES[-1]) + 20])
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, fname), format="svg")
    plt.close(fig)


numbers = {}

# --- Hovedtall, begge referanser, begge mål, alle aldre og 21-30 ------------
for meas, pre in [("eloundou", ""), ("mouchel", "mouchel_")]:
    for ref in REFS:
        g1 = growth(series(pre + "by_exposure", "_", Q1), REFS[ref]["ref"])
        g5 = growth(series(pre + "by_exposure", "_", Q5), REFS[ref]["ref"])
        y1 = growth(series(pre + "age_by_exposure", Q1, "21-30"), REFS[ref]["ref"])
        y5 = growth(series(pre + "age_by_exposure", Q5, "21-30"), REFS[ref]["ref"])
        suffix = ("_mouchel" if meas == "mouchel" else "") + ("_claudecode" if ref == "agentisk" else "")
        se_all = last_row(f"coef_recursive_kiindeks_headline{suffix}.csv")
        se_young = last_row(f"coef_recursive_kiindeks_headline{suffix}_young.csv")
        numbers[f"{meas}_{ref}"] = {
            "g1": round(g1, 1), "g5": round(g5, 1), "ki": round(ki_index(g5, g1), 1),
            "se": round(se_all["se"], 1), "ki_boot": round(se_all["ki"], 2),
            "lo": round(se_all["ki"] - 1.96 * se_all["se"], 1),
            "hi": round(se_all["ki"] + 1.96 * se_all["se"], 1),
            "y1": round(y1, 1), "y5": round(y5, 1), "ki_young": round(ki_index(y5, y1), 1),
            "se_young": round(se_young["se"], 1), "ki_young_boot": round(se_young["ki"], 2),
            "lo_young": round(se_young["ki"] - 1.96 * se_young["se"], 1),
            "hi_young": round(se_young["ki"] + 1.96 * se_young["se"], 1),
            "vintage": se_all["cutoff"],
        }

# Samlet privat sektor (vektet med sammensetning, som totalGrowth i app.js)
comp = {r["group"]: 0 for r in D["snapshots"]["composition"]["rows"]}
for r in D["snapshots"]["composition"]["rows"]:
    comp[r["group"]] += r["share"]
cols = P["by_exposure"]["value_cols"]
for ref in REFS:
    tot = sum(comp[c] * reindex(series("by_exposure", "_", c), REFS[ref]["ref"]) for c in cols) / sum(comp.values())
    numbers[f"total_{ref}"] = round(growth(tot, REFS[ref]["ref"]), 1)

# Siste 12 måneder for unge i Q5 (sa)
y5s = series("age_by_exposure", Q5, "21-30")
numbers["young_q5_yoy"] = round(100 * (y5s[-1] / y5s[-13] - 1), 1)

# --- Figur 1-2: alle aldre, Q1 mot Q5 ---------------------------------------
for ref in REFS:
    lines = [(f"Q{i}", series("by_exposure", "_", c), LIGHT, 1.0, False)
             for i, c in enumerate(cols[1:4], start=2)]
    lines.append(("minst eksponert (Q1)", series("by_exposure", "_", Q1), GRAY, 2.4, False))
    lines.append(("mest eksponert (Q5)", series("by_exposure", "_", Q5), BLUE, 2.4, False))
    line_chart(f"alle_{ref}.svg", [l for l in lines if l[0].startswith(("minst", "mest"))] +
               [(n, y, c, lw, d) for n, y, c, lw, d in lines if n.startswith("Q")],
               ref, f"sysselsetting, {REFS[ref]['ref_text']} = 100")

# --- Figur 3-4: 21-30 år, Q1 mot Q5 ------------------------------------------
for ref in REFS:
    lines = [
        ("alle aldre, mest eksponert", series("by_exposure", "_", Q5), BLUE, 1.0, True),
        ("alle aldre, minst eksponert", series("by_exposure", "_", Q1), GRAY, 1.0, True),
        ("21–30 år, minst eksponert", series("age_by_exposure", Q1, "21-30"), GRAY, 2.4, False),
        ("21–30 år, mest eksponert", series("age_by_exposure", Q5, "21-30"), BLUE, 2.4, False),
    ]
    line_chart(f"unge_{ref}.svg", lines, ref, f"sysselsetting, {REFS[ref]['ref_text']} = 100")

# --- Figur 5: etter alder, alle yrker ----------------------------------------
AGE_COL = {"21-30": BLUE, "31-40": "#7FA6D3", "41-50": "#999999", "51-60": "#555555"}
for ref in REFS:
    lines = [(a.replace("-", "–") + " år", series("by_age", "_", a), AGE_COL[a], 2.0, False)
             for a in P["by_age"]["value_cols"]]
    line_chart(f"alder_{ref}.svg", lines, ref, f"sysselsetting, {REFS[ref]['ref_text']} = 100")

# --- Figur 6: programvareutviklere etter alder --------------------------------
for ref in REFS:
    lines = [(a.replace("-", "–") + " år", series("software_developers", "_", a), AGE_COL[a], 2.0, False)
             for a in P["software_developers"]["value_cols"]]
    line_chart(f"utviklere_{ref}.svg", lines, ref, f"ansatte, {REFS[ref]['ref_text']} = 100")
    numbers[f"utviklere_2130_{ref}"] = round(
        reindex(series("software_developers", "_", "21-30"), REFS[ref]["ref"])[-1], 0)
    numbers[f"utviklere_5160_{ref}"] = round(
        reindex(series("software_developers", "_", "51-60"), REFS[ref]["ref"])[-1], 0)

# --- Figur 7: fire yrkescase, 2x2 --------------------------------------------
CASES = [("software_developers", "Programvareutviklere (Q5)"),
         ("customer_service", "Kundesentermedarbeidere (Q5)"),
         ("electricians", "Elektrikere (Q1)"),
         ("home_health_aides", "Hjemmehjelpere (Q2)")]
fig, axes = plt.subplots(2, 2, figsize=(11, 6.6), sharex=True)
for ax, (pkg, title) in zip(axes.flat, CASES):
    for a in P[pkg]["value_cols"]:
        y = reindex(series(pkg, "_", a), REFS["chatgpt"]["ref"])
        ax.plot(DATES, y, color=AGE_COL[a], linewidth=1.8)
        ax.text(DATES[-1] + pd.Timedelta(days=10), y[-1], a.replace("-", "–"),
                color=AGE_COL[a], fontsize=10, va="center")
    ax.axhline(100, color="#555555", linewidth=0.8)
    lo, hi = ax.get_ylim()
    for ref in REFS:
        ax.axvline(pd.Timestamp(REFS[ref]["launch"]), color="#777777", linestyle=":", linewidth=1)
    ax.set_title(title, fontsize=13, loc="left")
    ax.grid(axis="x", visible=False)
    ax.set_xlim(DATES[0], DATES[-1] + pd.Timedelta(days=200))
    ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=6))
    numbers[f"case_{pkg}_2130"] = round(reindex(series(pkg, "_", "21-30"), REFS["chatgpt"]["ref"])[-1], 0)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "yrkescase.svg"), format="svg")
plt.close(fig)

# --- Figur 8: spesifikasjonsgrid som punkt med intervall ----------------------
fig, ax = plt.subplots(figsize=(11, 5.0))
rows = []
for ref, rl in [("chatgpt", "ChatGPT-referanse"), ("agentisk", "agentisk referanse")]:
    for meas, ml in [("eloundou", "Eloundou"), ("mouchel", "Mouchel")]:
        n = numbers[f"{meas}_{ref}"]
        rows.append((f"alle 21–60, {ml}, {rl}", n["ki_boot"], n["lo"], n["hi"], GRAY if meas == "eloundou" else BLUE))
        rows.append((f"21–30 år, {ml}, {rl}", n["ki_young_boot"], n["lo_young"], n["hi_young"], GRAY if meas == "eloundou" else BLUE))
ypos = np.arange(len(rows))[::-1]
for (lab, v, lo, hi, c), yp in zip(rows, ypos):
    ax.plot([lo, hi], [yp, yp], color=c, linewidth=2.2, solid_capstyle="round")
    ax.plot(v, yp, "o", color=c, markersize=9, markeredgecolor="white", markeredgewidth=1.2)
    ax.text(hi + 0.3, yp, no(v), color=LABEL, fontsize=12, va="center")
ax.axvline(0, color="#555555", linewidth=0.8)
ax.set_yticks(ypos)
ax.set_yticklabels([r[0] for r in rows], fontsize=12)
ax.set_xlabel("KI-indeksen, prosentpoeng, med 95 % bootstrap-intervall")
ax.grid(axis="y", visible=False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "spesifikasjoner.svg"), format="svg")
plt.close(fig)

# --- Figur 9: LORV R2 (Lindenlaub mfl. 2026, figur 1, tall lest fra AID-dekkets variabler)
LORV = [("Eloundou mfl. (2024)", 0.302), ("Handa mfl. (2025)", 0.264),
        ("Felten mfl. (2021)", 0.255), ("Webb (2019)", 0.017)]
fig, ax = plt.subplots(figsize=(9, 3.4))
yp = np.arange(len(LORV))[::-1]
ax.barh(yp, [v for _, v in LORV], color=[BLUE, GRAY, GRAY, GRAY], height=0.6)
for y, (_, v) in zip(yp, LORV):
    ax.text(v + 0.006, y, f"{v:.3f}".replace(".", ","), va="center", fontsize=12, color=LABEL)
ax.set_yticks(yp)
ax.set_yticklabels([l for l, _ in LORV], fontsize=12)
ax.set_xlabel("R² mot rapportert KI-bruk per yrke")
ax.set_xlim(0, 0.36)
ax.grid(axis="y", visible=False)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "lorv.svg"), format="svg")
plt.close(fig)

numbers["release"] = D["release"]
numbers["last_month"] = str(DATES[-1].date())
numbers["n_months"] = int(len(DATES))
json.dump(numbers, open(os.path.join(OUT, "numbers.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(numbers, indent=1, ensure_ascii=False))
