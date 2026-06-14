"""
Figures 4 and 5 - Handa et al. (2025) Anthropic Economic Index measures.

Figure 4 (a/b/c): Like Figure 1 (specific occupations by age group), with
  panels showing occupations ranked by each Handa measure:
  4a = overall exposure, 4b = automation share, 4c = augmentation share.
Figure 5 (a/b/c): Like Figure 2 (age × quintile grid), using Handa quintiles
  for overall exposure, automation share, and augmentation share.

Style: Same Kieran Healy style as Figures 1-2.
"""

import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from _plot_notes import place_note
from _age_adjust import (load_population_monthly, load_composition_factors,
                         get_age_label, compute_adjusted_rate)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.lines import Line2D

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
HANDA_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_handa_mapping.csv'
STYRK_NAMES_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_codes.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = '2022-10-16'
MIN_EMPLOYMENT = 1000  # minimum Oct 2022 employment for Figure 4 panels

OI = {
    'grey':   '#999999',
    'orange': '#E69F00',
    'sky':    '#56B4E9',
    'green':  '#009E73',
    'yellow': '#F0E442',
    'blue':   '#0072B2',
    'red':    '#D55E00',
    'pink':   '#CC79A7',
}

AGE_MAP = {
    '2': '22-25',
    '3': '26-30',
    '4': '31-34',
    '5': '35-40',
    '6': '41-49',
}
AGE_50PLUS = {'7', '8'}
AGE_LABELS_ORDERED = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']
AGE_COLORS = {
    '22-25': OI['blue'],
    '26-30': OI['orange'],
    '31-34': OI['green'],
    '35-40': OI['red'],
    '41-49': OI['pink'],
    '50+':   OI['grey'],
}

QUINTILE_COLORS = {
    1: '#C6DBEF',
    2: '#9ECAE1',
    3: '#4292C6',
    4: '#2171B5',
    5: '#08306B',
}


def healy_style():
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'savefig.facecolor': 'white',
        'axes.linewidth': 0.5,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.edgecolor': '#333333',
        'axes.grid': True,
        'grid.color': '#BBBBBB',
        'grid.linewidth': 0.7,
        'grid.linestyle': '-',
        'xtick.major.width': 0.4,
        'ytick.major.width': 0.4,
        'xtick.color': '#333333',
        'ytick.color': '#333333',
        'xtick.major.size': 3,
        'ytick.major.size': 3,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 18,
        'axes.titlesize': 20,
        'axes.labelsize': 18,
        'xtick.labelsize': 16,
        'ytick.labelsize': 16,
        'legend.fontsize': 16,
        'figure.titlesize': 22,
        'lines.linewidth': 1.4,
    })


def date_to_dt(date_str):
    parts = date_str.split('-')
    return datetime(int(parts[0]), int(parts[1]), 1)


def normalize_series(series, norm_dt):
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: val / ref for dt, val in series.items()}


def filter_date_range(series):
    start = datetime(2021, 1, 1)
    end = datetime(2026, 3, 1)
    return {dt: val for dt, val in series.items() if start <= dt <= end}


def add_end_label(ax, dates, vals, label, color):
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=16, color=color, va='center',
                annotation_clip=False)


def load_counts():
    with open(DATA_FILE, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_handa():
    """Load Handa mapping: styrk08 -> dict with quintiles and scores."""
    mapping = {}
    with open(HANDA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            code = row['styrk08']
            mapping[code] = {
                'q_overall': int(row['q_overall_exposure']),
                'q_auto': int(row['q_automation_share']),
                'q_augm': int(row['q_augmentation_share']),
                'overall_exposure': float(row['overall_exposure']),
                'automation_share': float(row['automation_share']),
                'augmentation_share': float(row['augmentation_share']),
            }
    return mapping


def load_styrk_names():
    """Load STYRK-08 code -> name mapping."""
    names = {}
    with open(STYRK_NAMES_FILE, encoding='latin-1') as f:
        for row in csv.DictReader(f):
            code = row.get('styrk08', row.get('code', ''))
            name = row.get('name', row.get('presentationName', ''))
            if len(code) == 4:
                names[code] = name
    return names


def select_top_occupations(handa, styrk_names, employment, measure_key, n=4):
    """Select top-n single-code occupations by a Handa measure,
    requiring minimum employment and minimum overall exposure for
    automation/augmentation shares (to avoid noisy ratios from
    occupations with near-zero Claude usage)."""
    # Compute median overall exposure as threshold for share measures
    exposures = sorted(h['overall_exposure'] for h in handa.values())
    median_exp = exposures[len(exposures) // 2]

    candidates = []
    for code, h in handa.items():
        emp = employment.get(code, 0)
        if emp < MIN_EMPLOYMENT:
            continue
        # For automation_share / augmentation_share, require meaningful
        # overall exposure so the ratio is not based on a handful of queries
        if measure_key in ('automation_share', 'augmentation_share'):
            if h['overall_exposure'] < median_exp:
                continue
        name = styrk_names.get(code, code)
        candidates.append((code, name, h[measure_key], emp))

    candidates.sort(key=lambda x: -x[2])
    result = []
    for code, name, score, emp in candidates[:n]:
        h = handa[code]
        result.append((
            f'{name} ({code})',
            [code],
            f'Overall: {h["overall_exposure"]:.2f}, '
            f'Auto: {h["automation_share"]:.2f}, '
            f'Augm: {h["augmentation_share"]:.2f}'
        ))
    return result


def compute_oct2022_employment(counts):
    """Count Oct 2022 employment per yrke4 code."""
    emp = defaultdict(int)
    for row in counts:
        if row['date'] == '2022-10-16':
            emp[row['yrke4']] += int(row['count']) if row['count'] else 0
    return dict(emp)


# ---------------------------------------------------------------------------
# Figure 4 - top occupations by each Handa measure
# ---------------------------------------------------------------------------
def plot_figure4(counts, occupations, suffix, measure_label, pop, factors):
    """Plot Figure 4 variant with 4 occupation panels."""
    norm_dt = date_to_dt(NORM_DATE)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, (occ_label, occ_codes, score_text) in zip(axes.flatten(), occupations):
        agg = defaultdict(int)
        for row in counts:
            if row['yrke4'] not in occ_codes:
                continue
            age_label = get_age_label(row['alder_gr'])
            if not age_label:
                continue
            dt = date_to_dt(row['date'])
            count = int(row['count']) if row['count'] else 0
            agg[(age_label, dt)] += count

        for age_label in AGE_LABELS_ORDERED:
            raw = {}
            for (al, dt), emp in agg.items():
                if al != age_label:
                    continue
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj
            if not raw:
                continue
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=AGE_COLORS[age_label], linewidth=1.4)
            add_end_label(ax, dates, vals, age_label, AGE_COLORS[age_label])

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(f'{occ_label}\n({score_text})', fontsize=16)
        ax.set_ylabel('')
        ax.set_xlabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.set_ylim(0.7, 1.2)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'Top occupations by {measure_label}\n'
                 'Employment per capita by age group (October 2022 = 1)',
                 fontweight='semibold')

    note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1. '
        'Dashed vertical line marks the\n'
        'launch of ChatGPT (November 2022). '
        f'Panels show the 4 occupations (>{MIN_EMPLOYMENT:,} employees) '
        f'with highest {measure_label.lower()},\n'
        'from the Anthropic Economic Index, mapped to STYRK-08 via SOC 2010/ISCO-08 crosswalk.'
    )
    fig.tight_layout(w_pad=3, h_pad=3, rect=(0, 0, 1, 0.95))
    place_note(fig, axes, note, y=0.01)
    out = FIG_DIR / f'figure4{suffix}_occupations_handa.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 5 - 3x2 age grid with Handa quintiles
# ---------------------------------------------------------------------------
def plot_figure5(counts, handa, quintile_key, suffix, measure_label,
                 pop, factors):
    """Plot Figure 5 variant - age x quintile grid using Handa measure."""
    norm_dt = date_to_dt(NORM_DATE)

    quintile_map = {}
    for code, h in handa.items():
        quintile_map[code] = h[quintile_key]

    agg = defaultdict(int)
    agg_overall = defaultdict(int)

    for row in counts:
        yrke4 = row['yrke4']
        if yrke4 not in quintile_map:
            continue
        age_label = get_age_label(row['alder_gr'])
        if not age_label:
            continue
        dt = date_to_dt(row['date'])
        count = int(row['count']) if row['count'] else 0
        q = quintile_map[yrke4]
        agg[(age_label, q, dt)] += count
        agg_overall[(age_label, dt)] += count

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    axes_flat = axes.flatten()

    title_map = {
        '22-25': 'Early Career 1 (22\u201325)',
        '26-30': 'Early Career 2 (26\u201330)',
        '31-34': 'Developing (31\u201334)',
        '35-40': 'Mid-Career 1 (35\u201340)',
        '41-49': 'Mid-Career 2 (41\u201349)',
        '50+':   'Senior (50+)',
    }

    for i, age_label in enumerate(AGE_LABELS_ORDERED):
        ax = axes_flat[i]

        for q in range(1, 6):
            raw = {}
            for (al, qq, dt), emp in agg.items():
                if al == age_label and qq == q:
                    adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                    if adj is not None:
                        raw[dt] = adj
            if not raw:
                continue
            normed = normalize_series(raw, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        raw_all = {}
        for (al, dt), emp in agg_overall.items():
            if al == age_label:
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw_all[dt] = adj
        if raw_all:
            normed_all = normalize_series(raw_all, norm_dt)
            normed_all = filter_date_range(normed_all)
            if normed_all:
                dates_all, vals_all = zip(*sorted(normed_all.items()))
                ax.plot(dates_all, vals_all, color='red',
                        linewidth=2.0, linestyle='-')

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)

        ax.set_title(title_map[age_label])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)
        ax.set_ylim(0.7, 1.2)

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5,
               label='Q1 (lowest)'),
        Line2D([0], [0], color=QUINTILE_COLORS[2], lw=2.5, label='Q2'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[4], lw=2.5, label='Q4'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5,
               label='Q5 (highest)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center',
               ncol=6, frameon=False, bbox_to_anchor=(0.5, 0.98),
               fontsize=16)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'Employment per capita by age and {measure_label} quintile\n'
                 '(October 2022 = 1)',
                 y=1.03, fontweight='semibold')

    note_raw = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1), normalized to October 2022 = 1. '
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        f'Quintiles based on {measure_label}, from the Anthropic Economic Index, '
        'mapped to STYRK-08 via SOC 2010/ISCO-08 crosswalk (BLS, 2012). '
        'STYRK-08 = ISCO-08 at 4-digit level (SSB Notater 17/2011). '
        'Darker lines indicate higher values.'
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    place_note(fig, axes_flat, note_raw, y=0.03)
    out = FIG_DIR / f'figure5{suffix}_age_by_quintile_handa.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    handa = load_handa()
    styrk_names = load_styrk_names()
    employment = compute_oct2022_employment(counts)
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count rows, "
          f"{len(handa)} occupations with Handa scores, "
          f"{len(pop)} pop entries")

    # Figure 4a/b/c - top occupations by each measure
    for suffix, measure_key, label in [
        ('a', 'overall_exposure', 'Handa et al. overall exposure'),
        ('b', 'automation_share', 'Handa et al. automation share'),
        ('c', 'augmentation_share', 'Handa et al. augmentation share'),
    ]:
        occs = select_top_occupations(handa, styrk_names, employment,
                                      measure_key, n=4)
        print(f"\nFigure 4{suffix} ({label}):")
        for occ_label, codes, score_text in occs:
            print(f"  {occ_label}: {score_text}")
        plot_figure4(counts, occs, suffix, label, pop, factors)

    # Figure 5a/b/c - age x quintile grids
    print("\nPlotting Figure 5a (overall exposure quintiles)...")
    plot_figure5(counts, handa, 'q_overall', 'a', 'Handa et al. overall exposure',
                 pop, factors)

    print("Plotting Figure 5b (automation quintiles)...")
    plot_figure5(counts, handa, 'q_auto', 'b', 'Handa et al. automation',
                 pop, factors)

    print("Plotting Figure 5c (augmentation quintiles)...")
    plot_figure5(counts, handa, 'q_augm', 'c', 'Handa et al. augmentation',
                 pop, factors)


if __name__ == '__main__':
    main()
