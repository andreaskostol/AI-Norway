"""
Figure A1: Population in analysis age groups, 2021-2026.

Shows how the size of each age group changes over time, which can
affect employment trends independently of any AI effect.

Data: SSB table 07459 (population by single year of age, annual,
interpolated to quarterly).
"""

import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from _plot_notes import place_note

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / 'macro' / 'ssb_population_by_age_quarterly.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = datetime(2022, 11, 1)
NORM_DATE = datetime(2022, 10, 1)

AGE_GROUPS = {
    '21\u201330': (21, 30),
    '31\u201340': (31, 40),
    '41\u201350': (41, 50),
    '51\u201360': (51, 60),
}

# Okabe-Ito palette
COLORS = {
    '21\u201330': '#0072B2',
    '31\u201340': '#E69F00',
    '41\u201350': '#009E73',
    '51\u201360': '#999999',
}


def quarter_to_dt(q_str):
    """Convert '2021-Q1' to datetime."""
    year, q = q_str.split('-Q')
    month = (int(q) - 1) * 3 + 1
    return datetime(int(year), month, 1)


def load_data():
    """Load and aggregate by age group and quarter."""
    raw = defaultdict(lambda: defaultdict(int))
    with open(DATA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            dt = quarter_to_dt(row['date'])
            age = int(row['age'])
            pop = float(row['population'])
            for label, (lo, hi) in AGE_GROUPS.items():
                if lo <= age <= hi:
                    raw[label][dt] += pop
                    break
    return raw


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 26,
        'axes.titlesize': 32,
        'figure.titlesize': 36,
        'lines.linewidth': 2.0,
    })

    data = load_data()

    # --- Panel 1: Levels (thousands) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 7))

    for label in AGE_GROUPS:
        series = data[label]
        dates, vals = zip(*sorted(series.items()))
        vals_k = [v / 1000 for v in vals]
        ax1.plot(dates, vals_k, color=COLORS[label], linewidth=2.0)
        ax1.annotate(label, xy=(dates[-1], vals_k[-1]),
                     xytext=(8, 0), textcoords='offset points',
                     fontsize=20, color=COLORS[label], va='center',
                     annotation_clip=False)

    ax1.axvline(x=CHATGPT_LAUNCH, color='#999999', linestyle=':',
                linewidth=0.9)
    ax1.set_ylabel('Thousands', fontsize=24, color='#555555')
    ax1.set_title('Population level', fontweight='semibold')
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(True, axis='y', color='#AAAAAA', linewidth=0.9)
    ax1.grid(True, axis='x', color='#BBBBBB', linewidth=0.7)
    ax1.set_axisbelow(True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax1.xaxis.set_major_locator(mdates.YearLocator())
    ax1.tick_params(labelsize=22)

    # --- Panel 2: Normalized to Oct 2022 = 1 ---
    # Find nearest quarter to Oct 2022 -> Q4 2022
    norm_q = datetime(2022, 10, 1)

    for label in AGE_GROUPS:
        series = data[label]
        ref = series.get(norm_q)
        if not ref:
            continue
        dates, vals = zip(*sorted(series.items()))
        normed = [v / ref for v in vals]
        ax2.plot(dates, normed, color=COLORS[label], linewidth=2.0)
        ax2.annotate(label, xy=(dates[-1], normed[-1]),
                     xytext=(8, 0), textcoords='offset points',
                     fontsize=20, color=COLORS[label], va='center',
                     annotation_clip=False)

    ax2.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
    ax2.axvline(x=CHATGPT_LAUNCH, color='#999999', linestyle=':',
                linewidth=0.9)
    ax2.set_ylabel('Oct 2022 = 1', fontsize=24, color='#555555')
    ax2.set_title('Normalized population', fontweight='semibold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(True, axis='y', color='#AAAAAA', linewidth=0.9)
    ax2.grid(True, axis='x', color='#BBBBBB', linewidth=0.7)
    ax2.set_axisbelow(True)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.tick_params(labelsize=22)

    fig.suptitle('Population by age group: Norway 2021\u20132026',
                 fontweight='semibold')

    fig.tight_layout(rect=(0, 0.02, 1, 0.94))
    place_note(fig, (ax1, ax2),
               'Source: SSB table 07459 (population by single year of age, '
               'January 1). Quarterly values interpolated linearly.',
               y=-0.02, color='#888888')
    out = FIG_DIR / 'figureA0b_cohort_sizes.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == '__main__':
    main()
