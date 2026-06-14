"""
Figures 8 and 9 - Felten et al. (2021) AIOE measures.

Figure 8 (a/b): Like Figure 1 (specific occupations by age) for:
  a = AIOE (overall), b = AIOE Language Modeling (GenAI-specific)
Figure 9 (a/b): Like Figure 2 (age x quintile grid) for:
  a = AIOE quintiles, b = AIOE Language Modeling quintiles

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
FELTEN_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_felten_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = '2022-10-16'

OI = {
    'grey': '#999999', 'orange': '#E69F00', 'sky': '#56B4E9',
    'green': '#009E73', 'blue': '#0072B2', 'red': '#D55E00',
    'pink': '#CC79A7',
}

AGE_MAP = {'2': '22-25', '3': '26-30', '4': '31-34',
           '5': '35-40', '6': '41-49'}
AGE_50PLUS = {'7', '8'}
AGE_LABELS_ORDERED = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']
AGE_COLORS = {
    '22-25': OI['blue'], '26-30': OI['orange'], '31-34': OI['green'],
    '35-40': OI['red'], '41-49': OI['pink'], '50+': OI['grey'],
}

QUINTILE_COLORS = {
    1: '#C6DBEF', 2: '#9ECAE1', 3: '#4292C6',
    4: '#2171B5', 5: '#08306B',
}

FIGURE8_OCCUPATIONS = [
    ('Software developers (2512\u20132514, 2519)', ['2512', '2513', '2514', '2519']),
    ('Customer service agents (4222)', ['4222']),
    ('ICT systems analysts (2511)', ['2511']),
    ('ICT operations technicians (3511)', ['3511']),
]


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


def normalize_series(series, norm_dt):
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: val / ref for dt, val in series.items()}


def filter_date_range(series):
    s, e = datetime(2021, 1, 1), datetime(2026, 3, 1)
    return {dt: v for dt, v in series.items() if s <= dt <= e}


def add_end_label(ax, dates, vals, label, color):
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=16, color=color, va='center', annotation_clip=False)


def load_counts():
    with open(DATA_FILE, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_felten():
    mapping = {}
    with open(FELTEN_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            code = row['styrk08']
            mapping[code] = {}
            for measure in ['aioe', 'aioe_lm', 'aioe_ig']:
                q_key = f'q_{measure}'
                if row.get(q_key, '') != '':
                    mapping[code][q_key] = int(row[q_key])
                if row.get(measure, '') != '':
                    mapping[code][measure] = float(row[measure])
    return mapping


def plot_figure8(counts, felten, measure_key, score_key, suffix, title_label,
                 pop, factors):
    """Figure 8: same occupations as Figure 1, annotated with Felten scores."""
    norm_dt = date_to_dt(NORM_DATE)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, (occ_label, occ_codes) in zip(axes.flatten(), FIGURE8_OCCUPATIONS):
        scores = [felten[c].get(score_key) for c in occ_codes if c in felten
                  and felten[c].get(score_key) is not None]
        if scores:
            avg = sum(scores) / len(scores)
            score_text = f'{score_key} = {avg:.2f}'
        else:
            score_text = 'No data'

        agg = defaultdict(int)
        for row in counts:
            if row['yrke4'] not in occ_codes:
                continue
            al = get_age_label(row['alder_gr'])
            if not al:
                continue
            dt = date_to_dt(row['date'])
            agg[(al, dt)] += int(row['count']) if row['count'] else 0

        for al in AGE_LABELS_ORDERED:
            raw = {}
            for (a, dt), emp in agg.items():
                if a != al:
                    continue
                adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=AGE_COLORS[al], linewidth=1.4)
            add_end_label(ax, dates, vals, al, AGE_COLORS[al])

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(f'{occ_label}\n({score_text})', fontsize=16)
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.7, 1.2)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'Employment per capita by age group, {title_label}\n'
                 '(October 2022 = 1)', fontweight='semibold')
    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1.\n'
        f'Felten et al. (2021) {title_label} scores in parentheses. '
        'Mapped to STYRK-08 via SOC 2010/ISCO-08 crosswalk.'
    )
    fig.tight_layout(w_pad=3, h_pad=3, rect=(0, 0, 1, 0.95))
    place_note(fig, axes, note, y=0.01)
    out = FIG_DIR / f'figure8{suffix}_occupations_felten.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


def plot_figure9(counts, felten, q_key, suffix, title_label, pop, factors):
    """Figure 9: age x quintile grid."""
    norm_dt = date_to_dt(NORM_DATE)
    quintile_map = {c: felten[c][q_key] for c in felten if q_key in felten[c]}

    agg = defaultdict(int)
    agg_all = defaultdict(int)
    for row in counts:
        y = row['yrke4']
        if y not in quintile_map:
            continue
        al = get_age_label(row['alder_gr'])
        if not al:
            continue
        dt = date_to_dt(row['date'])
        count = int(row['count']) if row['count'] else 0
        agg[(al, quintile_map[y], dt)] += count
        agg_all[(al, dt)] += count

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    title_map = {
        '22-25': 'Early Career 1 (22\u201325)', '26-30': 'Early Career 2 (26\u201330)',
        '31-34': 'Developing (31\u201334)', '35-40': 'Mid-Career 1 (35\u201340)',
        '41-49': 'Mid-Career 2 (41\u201349)', '50+': 'Senior (50+)',
    }

    for i, al in enumerate(AGE_LABELS_ORDERED):
        ax = axes.flatten()[i]
        for q in range(1, 6):
            raw = {}
            for (a, qq, dt), emp in agg.items():
                if a == al and qq == q:
                    adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                    if adj is not None:
                        raw[dt] = adj
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        raw_all = {}
        for (a, dt), emp in agg_all.items():
            if a == al:
                adj = compute_adjusted_rate(emp, al, dt, pop, factors)
                if adj is not None:
                    raw_all[dt] = adj
        normed_all = normalize_series(raw_all, norm_dt)
        normed_all = filter_date_range(normed_all)
        if normed_all:
            d, v = zip(*sorted(normed_all.items()))
            ax.plot(d, v, color='red', linewidth=2.0)

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(title_map[al])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)
        ax.set_ylim(0.7, 1.2)

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5, label='Q1 (least exposed)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5, label='Q5 (most exposed)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 0.98), fontsize=16)
    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'Employment per capita by age and {title_label} quintile\n'
                 '(October 2022 = 1)', y=1.03, fontweight='semibold')
    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1.\n'
        f'{title_label} quintiles from Felten et al. (2021), '
        'mapped to STYRK-08 via SOC 2010/ISCO-08 crosswalk.\n'
        'Darker lines indicate higher AI exposure.'
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    place_note(fig, axes, note, y=0.03)
    out = FIG_DIR / f'figure9{suffix}_age_by_quintile_felten.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    felten = load_felten()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count rows, {len(felten)} Felten codes, "
          f"{len(pop)} pop entries")

    print("\nPlotting Figure 8a (AIOE overall)...")
    plot_figure8(counts, felten, 'q_aioe', 'aioe', 'a', 'AIOE', pop, factors)

    print("Plotting Figure 8b (AIOE Language Modeling)...")
    plot_figure8(counts, felten, 'q_aioe_lm', 'aioe_lm', 'b',
                 'AIOE Language Modeling', pop, factors)

    print("\nPlotting Figure 9a (AIOE quintiles)...")
    plot_figure9(counts, felten, 'q_aioe', 'a', 'Felten et al. AIOE',
                 pop, factors)

    print("Plotting Figure 9b (AIOE LM quintiles)...")
    plot_figure9(counts, felten, 'q_aioe_lm', 'b',
                 'Felten et al. AIOE Language Modeling', pop, factors)


if __name__ == '__main__':
    main()
