"""
Sensitivity analysis figures - restricted crosswalk quality.

Replicates Figure 2 (Eloundou) and Figure 5a (Handa overall) with occupations
filtered by crosswalk quality (max_partial_fanout), then compares
main specification vs. restricted specification side by side.

Two filter levels calibrated to approximate Kauhanen (2026):
  - "Strict": max_partial_fanout <= 5  (~80% employment coverage, ~Kauhanen)
  - "Very strict": max_partial_fanout <= 2  (~69% employment coverage)

For Handa, also applies task_coverage >= 0.10 as additional filter.

Output:
  figureS1_eloundou_sensitivity.pdf  - Figure 2 under three specifications
  figureS2_handa_sensitivity.pdf     - Figure 5a under three specifications
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
ELOUNDOU_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
HANDA_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_handa_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

CHATGPT_LAUNCH = mdates.date2num(datetime(2022, 11, 1))
NORM_DATE = '2022-10-16'

AGE_MAP = {'2': '22-25', '3': '26-30', '4': '31-34',
           '5': '35-40', '6': '41-49'}
AGE_50PLUS = {'7', '8'}
AGE_LABELS_ORDERED = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']

QUINTILE_COLORS = {
    1: '#C6DBEF', 2: '#9ECAE1', 3: '#4292C6',
    4: '#2171B5', 5: '#08306B',
}

TITLE_MAP = {
    '22-25': 'Early Career 1 (22\u201325)',
    '26-30': 'Early Career 2 (26\u201330)',
    '31-34': 'Developing (31\u201334)',
    '35-40': 'Mid-Career 1 (35\u201340)',
    '41-49': 'Mid-Career 2 (41\u201349)',
    '50+':   'Senior (50+)',
}


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
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size': 18, 'axes.titlesize': 20,
        'axes.labelsize': 18, 'xtick.labelsize': 16,
        'ytick.labelsize': 16, 'legend.fontsize': 16,
        'figure.titlesize': 22, 'lines.linewidth': 1.4,
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


def load_counts():
    with open(DATA_FILE, encoding='utf-8') as f:
        return list(csv.DictReader(f))


def assign_quintiles(scores_dict):
    """Assign quintiles 1-5 based on values in scores_dict."""
    codes = sorted(scores_dict, key=lambda c: scores_dict[c])
    n = len(codes)
    result = {}
    for i, c in enumerate(codes):
        pctl = 100 * i / n
        if pctl <= 20: result[c] = 1
        elif pctl <= 40: result[c] = 2
        elif pctl <= 60: result[c] = 3
        elif pctl <= 80: result[c] = 4
        else: result[c] = 5
    return result


def compute_employment(counts):
    emp = defaultdict(int)
    for row in counts:
        if row['date'] == '2022-10-16':
            emp[row['yrke4']] += int(row['count']) if row['count'] else 0
    return dict(emp)


def plot_quintile_panel(ax, counts, quintile_map, age_label, norm_dt,
                       pop, factors):
    """Plot quintile lines + overall for one age group on one axis."""
    agg = defaultdict(int)
    agg_all = defaultdict(int)

    for row in counts:
        yrke4 = row['yrke4']
        if yrke4 not in quintile_map:
            continue
        al = get_age_label(row['alder_gr'])
        if al != age_label:
            continue
        dt = date_to_dt(row['date'])
        count = int(row['count']) if row['count'] else 0
        q = quintile_map[yrke4]
        agg[(q, dt)] += count
        agg_all[dt] += count

    for q in range(1, 6):
        raw_emp = {dt: val for (qq, dt), val in agg.items() if qq == q}
        if not raw_emp:
            continue
        raw = {}
        for dt, emp in raw_emp.items():
            adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
            if adj is not None:
                raw[dt] = adj
        normed = normalize_series(raw, norm_dt)
        normed = filter_date_range(normed)
        if not normed:
            continue
        dates, vals = zip(*sorted(normed.items()))
        ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.4)

    if agg_all:
        raw_all = {}
        for dt, emp in agg_all.items():
            adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
            if adj is not None:
                raw_all[dt] = adj
        normed_all = normalize_series(raw_all, norm_dt)
        normed_all = filter_date_range(normed_all)
        if normed_all:
            dates_all, vals_all = zip(*sorted(normed_all.items()))
            ax.plot(dates_all, vals_all, color='red', linewidth=1.8, linestyle='-')


def make_sensitivity_figure(counts, specs, age_groups, fig_title, note_text,
                            out_path, pop, factors, ylim=(0.7, 1.2)):
    """Create a sensitivity figure: rows = age groups, columns = specifications."""
    n_rows = len(age_groups)
    n_cols = len(specs)
    norm_dt = date_to_dt(NORM_DATE)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 3.2 * n_rows),
                             squeeze=False)

    for col, (spec_label, quintile_map, n_codes, emp_pct) in enumerate(specs):
        for row_idx, age_label in enumerate(age_groups):
            ax = axes[row_idx, col]
            plot_quintile_panel(ax, counts, quintile_map, age_label, norm_dt,
                               pop, factors)

            ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
            ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                       linewidth=0.7, alpha=0.8)
            ax.set_ylim(*ylim)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            ax.xaxis.set_major_locator(mdates.YearLocator())
            ax.set_ylabel('')

            if row_idx == 0:
                ax.set_title(f'{spec_label}\n({n_codes} codes, {emp_pct:.0f}% emp)',
                             fontsize=16)
            if col == 0:
                ax.annotate(TITLE_MAP[age_label], xy=(0, 0.5),
                            xytext=(-45, 0), textcoords='offset points',
                            xycoords='axes fraction', fontsize=16,
                            ha='right', va='center', rotation=90)

    # Shared legend
    legend_handles = [
        Line2D([0], [0], color=QUINTILE_COLORS[1], lw=2, label='Q1 (lowest)'),
        Line2D([0], [0], color=QUINTILE_COLORS[3], lw=2, label='Q3'),
        Line2D([0], [0], color=QUINTILE_COLORS[5], lw=2, label='Q5 (highest)'),
        Line2D([0], [0], color='red', lw=2, label='Overall'),
    ]
    fig.legend(handles=legend_handles, loc='upper center', ncol=4,
               frameon=False, bbox_to_anchor=(0.5, 0.98), fontsize=16)

    fig.suptitle(fig_title, y=1.03, fontweight='semibold', fontsize=22)

    place_note(fig, axes, note_text, y=0.01)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.tight_layout(rect=(0.04, 0.02, 1, 0.97))
    fig.savefig(str(out_path), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out_path}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    counts = load_counts()
    pop = load_population_monthly()
    factors = load_composition_factors()
    emp = compute_employment(counts)
    total_emp = sum(emp.values())

    # --- Eloundou ---
    with open(ELOUNDOU_FILE, encoding='utf-8') as f:
        el_rows = list(csv.DictReader(f))

    def el_filter(max_fan):
        codes = {r['styrk08']: float(r['eloundou_beta'])
                 for r in el_rows if int(r['max_partial_fanout']) <= max_fan}
        return assign_quintiles(codes)

    el_all = el_filter(99)
    el_fan5 = el_filter(5)
    el_fan2 = el_filter(2)

    def emp_pct(qmap):
        return 100 * sum(emp.get(c, 0) for c in qmap) / total_emp

    el_specs = [
        ('All codes', el_all, len(el_all), emp_pct(el_all)),
        ('Fan-out $\leq$ 5', el_fan5, len(el_fan5), emp_pct(el_fan5)),
        ('Full match only', el_fan2, len(el_fan2), emp_pct(el_fan2)),
    ]

    print("\nPlotting Eloundou sensitivity (Figure S1)...")
    for label, qmap, n, pct in el_specs:
        print(f"  {n} codes, {pct:.1f}% emp")

    el_note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1). Sensitivity of Figure 2 to crosswalk '
        'quality restrictions.\n'
        'Left: all mapped codes. Center: excluding occupations where any '
        'contributing SOC code partially maps to >5 ISCO codes. '
        'Right: only full SOC-ISCO matches (fan-out <= 2).\n'
        'Quintiles re-assigned within each restricted sample. '
        'Eloundou et al. (2024) GPT-4 beta exposure.'
    )
    make_sensitivity_figure(
        counts, el_specs,
        ['22-25', '26-30', '31-34', '50+'],
        'Sensitivity: Eloundou et al. exposure quintiles by crosswalk quality',
        el_note,
        FIG_DIR / 'figureS1_eloundou_sensitivity.pdf',
        pop, factors,
    )

    # --- Handa overall ---
    with open(HANDA_FILE, encoding='utf-8') as f:
        ha_rows = list(csv.DictReader(f))

    def ha_filter(max_fan, min_task_cov=0.0):
        codes = {r['styrk08']: float(r['overall_exposure'])
                 for r in ha_rows
                 if int(r['max_partial_fanout']) <= max_fan
                 and float(r['task_coverage']) >= min_task_cov}
        return assign_quintiles(codes)

    ha_all = ha_filter(99)
    ha_fan5 = ha_filter(5, min_task_cov=0.10)
    ha_fan2 = ha_filter(2)

    ha_specs = [
        ('All codes', ha_all, len(ha_all), emp_pct(ha_all)),
        ('Fan-out $\leq$ 5 +\ntask cov $\geq$ 10%', ha_fan5, len(ha_fan5), emp_pct(ha_fan5)),
        ('Full match only', ha_fan2, len(ha_fan2), emp_pct(ha_fan2)),
    ]

    print("\nPlotting Handa sensitivity (Figure S2)...")
    for label, qmap, n, pct in ha_specs:
        print(f"  {n} codes, {pct:.1f}% emp")

    ha_note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1). Sensitivity of Figure 5a to crosswalk '
        'quality restrictions.\n'
        'Left: all mapped codes. Center: fan-out <= 5 and task coverage >= 10%.\n'
        'Right: only full SOC-ISCO matches (fan-out <= 2).\n'
        'Quintiles re-assigned within each restricted sample. '
        'Handa et al. (2025) Anthropic Economic Index overall exposure.'
    )
    make_sensitivity_figure(
        counts, ha_specs,
        ['22-25', '26-30', '31-34', '50+'],
        'Sensitivity: Handa et al. overall exposure quintiles by crosswalk quality',
        ha_note,
        FIG_DIR / 'figureS2_handa_sensitivity.pdf',
        pop, factors,
    )

    # --- Handa automation ---
    def ha_auto_filter(max_fan, min_task_cov=0.0):
        codes = {r['styrk08']: float(r['automation_share'])
                 for r in ha_rows
                 if int(r['max_partial_fanout']) <= max_fan
                 and float(r['task_coverage']) >= min_task_cov}
        return assign_quintiles(codes)

    ha_auto_all = ha_auto_filter(99)
    ha_auto_fan5 = ha_auto_filter(5, min_task_cov=0.10)
    ha_auto_fan2 = ha_auto_filter(2)

    ha_auto_specs = [
        ('All codes', ha_auto_all, len(ha_auto_all), emp_pct(ha_auto_all)),
        ('Fan-out $\leq$ 5 +\ntask cov $\geq$ 10%', ha_auto_fan5, len(ha_auto_fan5), emp_pct(ha_auto_fan5)),
        ('Full match only', ha_auto_fan2, len(ha_auto_fan2), emp_pct(ha_auto_fan2)),
    ]

    print("\nPlotting Handa automation sensitivity (Figure S3)...")
    for label, qmap, n, pct in ha_auto_specs:
        print(f"  {n} codes, {pct:.1f}% emp")

    ha_auto_note = (
        'Notes: Employment per capita (SSB table 07459) with composition '
        'adjustment (ref: 2021-Q1). Sensitivity of Figure 5b to crosswalk '
        'quality restrictions.\n'
        'Left: all mapped codes. Center: fan-out <= 5 and task coverage >= 10%.\n'
        'Right: only full SOC-ISCO matches. '
        'Quintiles re-assigned within each restricted sample.\n'
        'Handa et al. (2025) Anthropic Economic Index automation share.'
    )
    make_sensitivity_figure(
        counts, ha_auto_specs,
        ['22-25', '26-30', '31-34', '50+'],
        'Sensitivity: Handa et al. automation quintiles by crosswalk quality',
        ha_auto_note,
        FIG_DIR / 'figureS3_handa_auto_sensitivity.pdf',
        pop, factors,
    )


if __name__ == '__main__':
    main()
