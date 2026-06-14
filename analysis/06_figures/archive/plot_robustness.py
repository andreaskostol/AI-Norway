"""
Robustness figures for the paper:

Figure 7 (pre-period placebo): Eloundou quintile x age grid, indexed to Oct 2018,
  showing 2015-2022 only. Tests whether a systematic age-exposure gradient
  existed before ChatGPT.

Figure 7b (full period): Same as Figure 2 but showing 2015-2025.

Index-date sensitivity: Repeat the quintile x age grid with three different
  index dates (Sep 2022, Oct 2022, Jan 2023) side by side.

Style: Same Kieran Healy style as other figures.
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
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))

QUINTILE_COLORS = {
    1: '#C6DBEF', 2: '#9ECAE1', 3: '#4292C6',
    4: '#2171B5', 5: '#08306B',
}

AGE_MAP = {'2': '22-25', '3': '26-30', '4': '31-34',
           '5': '35-40', '6': '41-49'}
AGE_50PLUS = {'7', '8'}
AGE_LABELS = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']

TITLE_MAP = {
    '22-25': 'Early Career 1 (22\u201325)',
    '26-30': 'Early Career 2 (26\u201330)',
    '31-34': 'Developing (31\u201334)',
    '35-40': 'Mid-Career 1 (35\u201340)',
    '41-49': 'Mid-Career 2 (41\u201349)',
    '50+': 'Senior (50+)',
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
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 18, 'axes.titlesize': 20, 'axes.labelsize': 18,
        'xtick.labelsize': 16, 'ytick.labelsize': 16,
        'legend.fontsize': 16, 'figure.titlesize': 22, 'lines.linewidth': 1.4,
    })


def date_to_dt(s):
    return datetime(int(s.split('-')[0]), int(s.split('-')[1]), 1)


def normalize(series, norm_dt):
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: v / ref for dt, v in series.items()}


def load_counts():
    with open(DATA_FILE, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_exposure():
    mapping = {}
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['quintile'] and len(row['styrk08']) == 4:
                mapping[row['styrk08']] = int(row['quintile'])
    return mapping


def aggregate_by_quintile(counts, exposure):
    """Returns (agg, agg_all) dicts keyed by (age_label, quintile, datetime)
    and (age_label, datetime)."""
    agg = defaultdict(int)
    agg_all = defaultdict(int)
    for row in counts:
        y = row['yrke4']
        if y not in exposure:
            continue
        al = get_age_label(row['alder_gr'])
        if not al:
            continue
        dt = date_to_dt(row['date'])
        count = int(row['count']) if row['count'] else 0
        q = exposure[y]
        agg[(al, q, dt)] += count
        agg_all[(al, dt)] += count
    return agg, agg_all


def plot_quintile_grid(agg, agg_all, norm_date_str, date_start, date_end,
                       title, note_text, out_path, pop, factors,
                       chatgpt_line=True):
    """Generic quintile x age grid plot."""
    norm_dt = date_to_dt(norm_date_str)

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))

    for i, al in enumerate(AGE_LABELS):
        ax = axes.flatten()[i]
        for q in range(1, 6):
            raw_emp = {dt: v for (a, qq, dt), v in agg.items() if a == al and qq == q}
            raw = {}
            for dt, emp in raw_emp.items():
                adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj
            normed = normalize(raw, norm_dt)
            filtered = {dt: v for dt, v in normed.items()
                        if date_start <= dt <= date_end}
            if not filtered:
                continue
            dates, vals = zip(*sorted(filtered.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        raw_all_emp = {dt: v for (a, dt), v in agg_all.items() if a == al}
        raw_all = {}
        for dt, emp in raw_all_emp.items():
            adj = compute_adjusted_rate(emp, al, dt, pop, factors)
            if adj is not None:
                raw_all[dt] = adj
        normed_all = normalize(raw_all, norm_dt)
        filtered_all = {dt: v for dt, v in normed_all.items()
                        if date_start <= dt <= date_end}
        if filtered_all:
            d, v = zip(*sorted(filtered_all.items()))
            ax.plot(d, v, color='red', linewidth=2.0)

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        if chatgpt_line:
            chatgpt_num = mdates.date2num(datetime(2022, 11, 1))
            if date_start <= datetime(2022, 11, 1) <= date_end:
                ax.axvline(x=chatgpt_num, color='#555555', linestyle='--',
                           linewidth=0.7, alpha=0.8)

        ax.set_title(TITLE_MAP[al])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5, label='Q1 (least exposed)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5, label='Q5 (most exposed)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 0.98), fontsize=16)
    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(title, y=1.03, fontweight='semibold')
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))

    place_note(fig, axes, note_text, y=0.03)
    fig.savefig(str(out_path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out_path}")


def plot_index_sensitivity(agg, agg_all, out_path, pop, factors):
    """3-column figure: same quintile x age grid with three index dates."""
    index_dates = [
        ('2022-09-16', 'Sep 2022'),
        ('2022-10-16', 'Oct 2022'),
        ('2023-01-16', 'Jan 2023'),
    ]
    date_start = datetime(2021, 1, 1)
    date_end = datetime(2026, 3, 1)

    fig, axes = plt.subplots(6, 3, figsize=(18, 16))

    for col, (norm_str, norm_label) in enumerate(index_dates):
        norm_dt = date_to_dt(norm_str)

        for i, al in enumerate(AGE_LABELS):
            ax = axes[i, col]
            for q in range(1, 6):
                raw_emp = {dt: v for (a, qq, dt), v in agg.items()
                           if a == al and qq == q}
                raw = {}
                for dt, emp in raw_emp.items():
                    adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                    if adj is not None:
                        raw[dt] = adj
                normed = normalize(raw, norm_dt)
                filtered = {dt: v for dt, v in normed.items()
                            if date_start <= dt <= date_end}
                if not filtered:
                    continue
                dates, vals = zip(*sorted(filtered.items()))
                ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.2)

            raw_all_emp = {dt: v for (a, dt), v in agg_all.items() if a == al}
            raw_all = {}
            for dt, emp in raw_all_emp.items():
                adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                if adj is not None:
                    raw_all[dt] = adj
            normed_all = normalize(raw_all, norm_dt)
            filtered_all = {dt: v for dt, v in normed_all.items()
                            if date_start <= dt <= date_end}
            if filtered_all:
                d, v = zip(*sorted(filtered_all.items()))
                ax.plot(d, v, color='red', linewidth=1.5)

            ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
            ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                       linewidth=0.5, alpha=0.6)
            ax.set_ylim(0.7, 1.2)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%y'))
            ax.xaxis.set_major_locator(mdates.YearLocator())

            if i == 0:
                ax.set_title(f'Index: {norm_label}', fontsize=18)
            if col == 0:
                ax.set_ylabel(TITLE_MAP[al], fontsize=16)
            else:
                ax.set_ylabel('')

            if i < 5:
                ax.set_xticklabels([])

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5, label='Q1 (least)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5, label='Q5 (most)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 0.98), fontsize=16)
    fig.suptitle('Index-date sensitivity: Eloundou et al. quintile x age\n'
                 'Employment per capita normalized to index month = 1',
                 y=1.03, fontweight='semibold')
    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1). Same analysis as Figure 2 with three '
        'different normalization dates.\n'
        'Dashed line marks ChatGPT launch (Nov 2022). '
        'Eloundou et al. (2024) exposure quintiles mapped to STYRK-08.'
    )
    fig.tight_layout(rect=(0, 0.02, 1, 0.97))
    place_note(fig, axes, note, y=0.01)
    fig.savefig(str(out_path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out_path}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    exposure = load_exposure()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count rows, {len(exposure)} exposure codes, "
          f"{len(pop)} pop entries")

    agg, agg_all = aggregate_by_quintile(counts, exposure)

    # Index-date sensitivity
    print("Plotting index-date sensitivity...")
    plot_index_sensitivity(
        agg, agg_all,
        out_path=FIG_DIR / 'figureS4_index_sensitivity.pdf',
        pop=pop, factors=factors,
    )


if __name__ == '__main__':
    main()
