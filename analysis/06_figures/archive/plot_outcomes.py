"""
Figures 6 and 7 - Outcome variables by occupation/quintile and age.

Figure 6 (a-e): Like Figure 1 (specific occupations by age group) for:
  a=kontantlonn, b=stillingspst, c=timelonn, d=overtid_timer, e=ny_jobb
Figure 7 (a-e): Like Figure 2 (Eloundou quintile × age grid) for same variables.

All quintile-level means are employment-weighted. Weights use population-
adjusted rates (employment per capita * composition factor) rather than
raw headcounts, to remove cohort-size and within-group age shifts.

Style: Same Kieran Healy style as Figures 1-2.
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
COUNT_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
WAGE_FILE = BASE_DIR / 'data' / '02_occ_agem_wage_2021_2026.csv'
OVERTID_FILE = BASE_DIR / 'data' / '06_occ_agem_overtid_nyjobb_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = '2022-10-16'

OI = {
    'grey': '#999999', 'orange': '#E69F00', 'sky': '#56B4E9',
    'green': '#009E73', 'yellow': '#F0E442', 'blue': '#0072B2',
    'red': '#D55E00', 'pink': '#CC79A7',
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

FIGURE6_OCCUPATIONS = [
    ('Software developers (2512\u20132514, 2519)', ['2512', '2513', '2514', '2519']),
    ('Customer service agents (4222)', ['4222']),
    ('ICT systems analysts (2511)', ['2511']),
    ('ICT operations technicians (3511)', ['3511']),
]

VARIABLES = [
    ('kontantlonn', 'a', 'Monthly earnings (kontantlonn)'),
    ('stillingspst', 'b', 'Position percentage (stillingspst)'),
    ('timelonn', 'c', 'Hourly wage (timelonn)'),
    ('overtid_timer', 'd', 'Overtime hours'),
    ('ny_jobb', 'e', 'New job share'),
]


def healy_style():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'axes.linewidth': 0.5,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.edgecolor': '#333333', 'axes.grid': True,
        'grid.color': '#BBBBBB', 'grid.linewidth': 0.7,
        'grid.linestyle': '-',
        'xtick.major.width': 0.4, 'ytick.major.width': 0.4,
        'xtick.color': '#333333', 'ytick.color': '#333333',
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 18, 'axes.titlesize': 20, 'axes.labelsize': 18,
        'xtick.labelsize': 16, 'ytick.labelsize': 16,
        'legend.fontsize': 16, 'figure.titlesize': 22,
        'lines.linewidth': 1.4,
    })


def date_to_dt(date_str):
    return datetime(int(date_str.split('-')[0]), int(date_str.split('-')[1]), 1)


def normalize_series(series, norm_dt):
    ref = series.get(norm_dt)
    if not ref or ref == 0:
        return {}
    return {dt: val / ref for dt, val in series.items()}


def filter_date_range(series):
    start, end = datetime(2021, 1, 1), datetime(2026, 3, 1)
    return {dt: val for dt, val in series.items() if start <= dt <= end}


def add_end_label(ax, dates, vals, label, color):
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=16, color=color, va='center',
                annotation_clip=False)


def load_outcome_data(filepath, target_variable):
    """Load outcome variable data: {(yrke4, alder_gr, date): mean_value}"""
    data = {}
    with open(filepath, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['variable'] != target_variable:
                continue
            val = row['value']
            if not val or val == '-':
                continue
            try:
                data[(row['yrke4'], row['alder_gr'], row['date'])] = float(val)
            except ValueError:
                continue
    return data


def load_counts():
    """Load employment counts: {(yrke4, alder_gr, date): count}"""
    data = {}
    with open(COUNT_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            count = int(row['count']) if row['count'] else 0
            if count > 0:
                data[(row['yrke4'], row['alder_gr'], row['date'])] = count
    return data


def load_exposure():
    """Load Eloundou quintile mapping: yrke4 -> quintile"""
    mapping = {}
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['quintile'] and len(row['styrk08']) == 4:
                mapping[row['styrk08']] = int(row['quintile'])
    return mapping


def compute_weighted_series(outcome_data, counts, codes, age_label,
                            pop=None, factors=None):
    """Compute employment-weighted mean of an outcome variable
    for a set of yrke4 codes and one age label, by date.

    When pop and factors are provided, weights are adjusted rates
    (employment per capita * composition factor) instead of raw counts.

    Returns {datetime: weighted_mean}
    """
    # Find all dates available
    dates = set()
    age_grs = [k for k, v in AGE_MAP.items() if v == age_label]
    if age_label == '50+':
        age_grs = list(AGE_50PLUS)
    for code in codes:
        for ag in age_grs:
            for (y, a, d) in outcome_data:
                if y == code and a == ag:
                    dates.add(d)

    series = {}
    for date_str in dates:
        total_weight = 0
        weighted_sum = 0
        dt = date_to_dt(date_str)
        for code in codes:
            for ag in age_grs:
                key = (code, ag, date_str)
                val = outcome_data.get(key)
                weight = counts.get(key, 0)
                if val is not None and weight > 0:
                    # Adjust weight using population and composition factors
                    if pop is not None and factors is not None:
                        adj = compute_adjusted_rate(weight, age_label, dt,
                                                    pop, factors)
                        if adj is not None:
                            weight = adj
                        else:
                            continue
                    weighted_sum += val * weight
                    total_weight += weight
        if total_weight > 0:
            series[dt] = weighted_sum / total_weight

    return series


# ---------------------------------------------------------------------------
# Figure 6 - specific occupations by age, one variable at a time
# ---------------------------------------------------------------------------
def plot_figure6(outcome_data, counts, var_name, suffix, title_label,
                 pop=None, factors=None):
    norm_dt = date_to_dt(NORM_DATE)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, (occ_label, occ_codes) in zip(axes.flatten(), FIGURE6_OCCUPATIONS):
        for age_label in AGE_LABELS_ORDERED:
            series = compute_weighted_series(outcome_data, counts,
                                             occ_codes, age_label,
                                             pop, factors)
            normed = normalize_series(series, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=AGE_COLORS[age_label], linewidth=1.4)
            add_end_label(ax, dates, vals, age_label, AGE_COLORS[age_label])

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(occ_label)
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'{title_label} by age group (pop.-adjusted weights)\n'
                 '(October 2022 = 1)',
                 fontweight='semibold')

    note = (
        f'Notes: Mean {var_name} from Norwegian A-ordningen register data, '
        'normalized to October 2022 = 1.\n'
        'Weights are employment per capita (SSB table 07459) with '
        'composition adjustment (ref: 2021-Q1).\n'
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        'Multi-code occupations are employment-weighted.'
    )
    fig.tight_layout(w_pad=3, h_pad=3, rect=[0, 0, 1, 0.95])
    place_note(fig, axes, note, y=0.01)
    out = FIG_DIR / f'figure6{suffix}_{var_name}_by_age.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 7 - quintile × age grid, one variable at a time
# ---------------------------------------------------------------------------
def plot_figure7(outcome_data, counts, exposure, var_name, suffix, title_label,
                 pop=None, factors=None):
    norm_dt = date_to_dt(NORM_DATE)

    fig, axes = plt.subplots(3, 2, figsize=(12, 12))
    axes_flat = axes.flatten()

    title_map = {
        '22-25': 'Early Career 1 (22\u201325)',
        '26-30': 'Early Career 2 (26\u201330)',
        '31-34': 'Developing (31\u201334)',
        '35-40': 'Mid-Career 1 (35\u201340)',
        '41-49': 'Mid-Career 2 (41\u201349)',
        '50+': 'Senior (50+)',
    }

    # Group yrke4 codes by quintile
    quintile_codes = defaultdict(list)
    all_codes = []
    for code, q in exposure.items():
        quintile_codes[q].append(code)
        all_codes.append(code)

    for i, age_label in enumerate(AGE_LABELS_ORDERED):
        ax = axes_flat[i]

        for q in range(1, 6):
            series = compute_weighted_series(outcome_data, counts,
                                             quintile_codes[q], age_label,
                                             pop, factors)
            normed = normalize_series(series, norm_dt)
            normed = filter_date_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        # Overall
        series_all = compute_weighted_series(outcome_data, counts,
                                             all_codes, age_label,
                                             pop, factors)
        normed_all = normalize_series(series_all, norm_dt)
        normed_all = filter_date_range(normed_all)
        if normed_all:
            dates_all, vals_all = zip(*sorted(normed_all.items()))
            ax.plot(dates_all, vals_all, color='red', linewidth=2.0)

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(title_map[age_label])
        ax.set_ylabel('')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_minor_locator(mdates.MonthLocator())
        ax.tick_params(axis='x', which='minor', length=2, width=0.4)

    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2.5,
               label='Q1 (least exposed)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2.5, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2.5,
               label='Q5 (most exposed)'),
        Line2D([0], [0], color='red', lw=2.5, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center',
               ncol=4, frameon=False, bbox_to_anchor=(0.5, 0.98),
               fontsize=16)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'{title_label} by age and AI-exposure quintile\n'
                 '(pop.-adjusted weights, October 2022 = 1)',
                 y=1.03, fontweight='semibold')

    note = (
        f'Notes: Employment-weighted mean {var_name} from Norwegian '
        'A-ordningen register data, normalized to '
        'October 2022 = 1.\n'
        'Weights are employment per capita (SSB table 07459) with '
        'composition adjustment (ref: 2021-Q1).\n'
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        'Exposure quintiles based on Eloundou et al. (2024) GPT-4 beta.'
    )
    fig.tight_layout(rect=[0, 0.03, 1, 0.97])
    place_note(fig, axes, note, y=0.03)
    out = FIG_DIR / f'figure7{suffix}_{var_name}_by_quintile.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    exposure = load_exposure()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(counts):,} count cells, {len(exposure)} exposure codes, "
          f"{len(pop)} pop entries")

    for var_name, suffix, title_label in VARIABLES:
        # Determine source file
        if var_name in ('overtid_timer', 'ny_jobb'):
            filepath = OVERTID_FILE
        else:
            filepath = WAGE_FILE

        print(f"\nLoading {var_name}...")
        outcome_data = load_outcome_data(filepath, var_name)
        print(f"  {len(outcome_data):,} outcome cells")

        print(f"Plotting Figure 6{suffix} ({title_label})...")
        plot_figure6(outcome_data, counts, var_name, suffix, title_label,
                     pop, factors)

        print(f"Plotting Figure 7{suffix} ({title_label})...")
        plot_figure7(outcome_data, counts, exposure, var_name, suffix,
                     title_label, pop, factors)


if __name__ == '__main__':
    main()
