"""
Appendix figure: Employment by AI exposure and job dimensionality (2x2 grid).

Tests the Imas & Shukla (2026) / Gans & Goldfarb (2025) O-Ring prediction:
employment decline should concentrate in high exposure + low dimensionality.

Each panel shows age groups separately, normalized to October 2022 = 1.
Style matches Figure 2 (Healy style, serif, same rcParams).
"""

import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D
from _plot_notes import place_note
from _age_adjust import (load_population_monthly, load_composition_factors,
                         get_age_label, compute_adjusted_rate)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
DIM_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_dimensionality.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = datetime(2022, 10, 1)

OI = {
    'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
    'red': '#D55E00', 'pink': '#CC79A7', 'grey': '#999999',
}

AGE_MAP = {'2': '22-25', '3': '26-30', '4': '31-34', '5': '35-40', '6': '41-49'}
AGE_50PLUS = {'7', '8'}
AGE_LABELS = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']
AGE_COLORS = {
    '22-25': OI['blue'], '26-30': OI['orange'], '31-34': OI['green'],
    '35-40': OI['red'], '41-49': OI['pink'], '50+': OI['grey'],
}

QUADRANT_ORDER = [
    'High exposure, Low dimensionality',
    'High exposure, High dimensionality',
    'Low exposure, Low dimensionality',
    'Low exposure, High dimensionality',
]
QUADRANT_TITLES = {
    'High exposure, Low dimensionality':  'High AI exposure, Few tasks',
    'High exposure, High dimensionality': 'High AI exposure, Many tasks',
    'Low exposure, Low dimensionality':   'Low AI exposure, Few tasks',
    'Low exposure, High dimensionality':  'Low AI exposure, Many tasks',
}


def healy_style():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'axes.linewidth': 0.5,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#333333', 'axes.grid': True,
        'grid.color': '#BBBBBB', 'grid.linewidth': 0.7, 'grid.linestyle': '-',
        'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
        'xtick.color': '#333333', 'ytick.color': '#333333',
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 18, 'axes.titlesize': 20, 'axes.labelsize': 18,
        'xtick.labelsize': 16, 'ytick.labelsize': 16,
        'legend.fontsize': 16, 'figure.titlesize': 22, 'lines.linewidth': 1.4,
    })


def date_to_dt(s: str) -> datetime:
    return datetime(int(s.split('-')[0]), int(s.split('-')[1]), 1)


def normalize(series, norm_dt):
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: v / ref for dt, v in series.items()}


def filter_range(series):
    s, e = datetime(2021, 1, 1), datetime(2026, 3, 1)
    return {dt: v for dt, v in series.items() if s <= dt <= e}


def add_end_label(ax, dates, vals, label, color):
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=16, color=color, va='center', annotation_clip=False)


def main():
    healy_style()

    quadrants = {}
    with open(DIM_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            quadrants[row['styrk08']] = row['quadrant']

    counts = []
    with open(DATA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            counts.append(row)

    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"Loaded {len(counts)} count rows, {len(quadrants)} quadrant assignments, "
          f"{len(pop)} pop entries")

    norm_dt = date_to_dt('2022-10-16')

    agg = defaultdict(int)
    for row in counts:
        yrke4 = row['yrke4']
        if yrke4 not in quadrants:
            continue
        ag = get_age_label(row['alder_gr'])
        if not ag:
            continue
        q = quadrants[yrke4]
        dt = date_to_dt(row['date'])
        c = int(row['count']) if row['count'] else 0
        agg[(q, ag, dt)] += c

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, quad in zip(axes.flatten(), QUADRANT_ORDER):
        for age_label in AGE_LABELS:
            raw_emp = {dt: val for (q, al, dt), val in agg.items()
                       if q == quad and al == age_label}
            if not raw_emp:
                continue
            raw = {}
            for dt, emp in raw_emp.items():
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj
            normed = normalize(raw, norm_dt)
            normed = filter_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=AGE_COLORS[age_label],
                    linewidth=1.4)
            add_end_label(ax, dates, vals, age_label, AGE_COLORS[age_label])

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(QUADRANT_TITLES[quad])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)
        ax.set_ylim(0.8, 1.15)

    legend_handles = [Line2D([0], [0], color=AGE_COLORS[al], lw=2.5, label=al)
                      for al in AGE_LABELS]
    fig.legend(handles=legend_handles, loc='upper center', ncol=6,
               frameon=False, bbox_to_anchor=(0.5, 1.0), fontsize=16)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle('Employment per capita by AI exposure and job dimensionality\n'
                 '(October 2022 = 1)',
                 y=1.06, fontweight='semibold')

    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1. '
        'Dashed line marks ChatGPT launch (November 2022).\n'
        'AI exposure: Eloundou et al. (2024) GPT-4 beta, median split. '
        'Dimensionality: O*NET task count per occupation, median split (22 tasks).\n'
        'Residual SOC categories excluded. '
        'O-ring prediction (Gans & Goldfarb 2025; Imas & Shukla 2026): '
        'decline concentrates in top-left panel.'
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.96))
    place_note(fig, axes, note, y=0.03)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    out = FIG_DIR / 'figure12_dimensionality_2x2.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")

    # Summary stats
    print("\nAge 22-25, employment counts:")
    print(f"{'Quadrant':<45} {'Oct 2022':>10} {'Feb 2026':>10} {'Change':>8}")
    for quad in QUADRANT_ORDER:
        oct22 = agg.get((quad, '22-25', datetime(2022, 10, 1)), 0)
        feb26 = agg.get((quad, '22-25', datetime(2026, 2, 1)), 0)
        pct = (feb26 / oct22 - 1) * 100 if oct22 else 0
        print(f"  {quad:<43} {oct22:>10} {feb26:>10} {pct:>7.1f}%")


if __name__ == '__main__':
    main()
