"""
Figure 3: Employment by AI-exposure quintile and sector (1x3 grid).
Reads parsed sector CSV, maps yrke4 to Eloundou quintiles, aggregates.
Style matches other figures.
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

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECTOR_FILE = BASE_DIR / 'data' / '04_occ_agem_sector_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = datetime(2022, 10, 1)

QUINTILE_COLORS = {
    1: '#C6DBEF', 2: '#9ECAE1', 3: '#4292C6',
    4: '#2171B5', 5: '#08306B',
}

SECTOR_ORDER = [('3', 'Private'), ('2', 'Municipal'), ('1', 'State')]


def healy_style():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'axes.linewidth': 0.5,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#333333', 'axes.grid': True,
        'grid.color': '#BBBBBB', 'grid.linewidth': 0.7, 'grid.linestyle': '-',
        'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
        'xtick.color': '#333333', 'ytick.color': '#333333',
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


def main():
    healy_style()

    # Load exposure quintiles
    exposure = {}
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['quintile'] and len(row['styrk08']) == 4:
                exposure[row['styrk08']] = int(row['quintile'])

    # Load sector counts and aggregate by quintile x sector x date (all ages pooled)
    agg = defaultdict(int)
    agg_all = defaultdict(int)
    with open(SECTOR_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['variable'] != 'count':
                continue
            yrke4 = row['yrke4']
            if yrke4 not in exposure:
                continue
            val = row['value']
            if not val or val == '-':
                continue
            try:
                count = int(float(val))
            except ValueError:
                continue
            sekt = row['sekt']
            dt = date_to_dt(row['date'])
            q = exposure[yrke4]
            agg[(q, sekt, dt)] += count
            agg_all[(sekt, dt)] += count

    print(f"Loaded {len(agg)} quintile-sector-date cells")

    # Plot 1x3
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    for col, (sekt_code, sekt_label) in enumerate(SECTOR_ORDER):
        ax = axes[col]

        for q in range(1, 6):
            raw = {dt: v for (qq, s, dt), v in agg.items()
                   if qq == q and s == sekt_code}
            normed = normalize(raw, NORM_DATE)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        # Overall
        raw_all = {dt: v for (s, dt), v in agg_all.items() if s == sekt_code}
        normed_all = normalize(raw_all, NORM_DATE)
        if normed_all:
            d, v = zip(*sorted(normed_all.items()))
            ax.plot(d, v, color='red', linewidth=2.0)

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(sekt_label)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.7, 1.2)

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5,
               label='Q1 (least exposed)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5,
               label='Q5 (most exposed)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center',
               ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.04),
               fontsize=16)

    fig.suptitle('Employment by sector and AI-exposure quintile\n'
                 'Headcount (October 2022 = 1)',
                 y=1.12, fontweight='semibold')

    note = (
        'Notes: Employment counts normalized to October 2022 = 1. '
        'Dashed vertical line marks the launch of ChatGPT (November 2022).\n'
        'Exposure quintiles based on Eloundou et al. (2024) GPT-4 beta, '
        'mapped to STYRK-08. '
        'Darker lines indicate higher AI exposure.'
    )
    place_note(fig, axes, note, y=-0.04)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.tight_layout(rect=(0, 0.04, 1, 0.94))
    out = FIG_DIR / 'figure3_sector_by_quintile.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == '__main__':
    main()
