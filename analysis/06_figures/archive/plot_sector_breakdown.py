"""
Figures 10 and 11 - Employment by sector.

Figure 10 (a/b/c): Like Figure 1 (specific occupations by age group),
  split by sector: a=State, b=Municipal, c=Private.
Figure 11 (a/b/c): Like Figure 2 (Eloundou quintile x age grid),
  split by sector: a=State, b=Municipal, c=Private.

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
SECTOR_FILE = BASE_DIR / 'data' / '04_occ_agem_sector_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
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
AGE_LABELS = ['22-25', '26-30', '31-34', '35-40', '41-49', '50+']
AGE_COLORS = {
    '22-25': OI['blue'], '26-30': OI['orange'], '31-34': OI['green'],
    '35-40': OI['red'], '41-49': OI['pink'], '50+': OI['grey'],
}

QUINTILE_COLORS = {
    1: '#C6DBEF', 2: '#9ECAE1', 3: '#4292C6',
    4: '#2171B5', 5: '#08306B',
}

SECTORS = [
    ('1', 'a', 'State'),
    ('2', 'b', 'Municipal'),
    ('3', 'c', 'Private'),
]

FIGURE10_OCCUPATIONS = [
    ('Software developers (2512\u20132514, 2519)', ['2512', '2513', '2514', '2519']),
    ('Customer service agents (4222)', ['4222']),
    ('ICT systems analysts (2511)', ['2511']),
    ('ICT operations technicians (3511)', ['3511']),
]

TITLE_MAP = {
    '22-25': 'Early Career 1 (22\u201325)', '26-30': 'Early Career 2 (26\u201330)',
    '31-34': 'Developing (31\u201334)', '35-40': 'Mid-Career 1 (35\u201340)',
    '41-49': 'Mid-Career 2 (41\u201349)', '50+': 'Senior (50+)',
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
    if not ref or ref == 0: return {}
    return {dt: v / ref for dt, v in series.items()}


def filter_range(series):
    s, e = datetime(2021, 1, 1), datetime(2026, 3, 1)
    return {dt: v for dt, v in series.items() if s <= dt <= e}


def add_end_label(ax, dates, vals, label, color):
    ax.annotate(label, xy=(dates[-1], vals[-1]),
                xytext=(6, 0), textcoords='offset points',
                fontsize=16, color=color, va='center', annotation_clip=False)


def load_sector_counts():
    """Load sector count data: {(yrke4, alder_gr, sekt, date): count}"""
    data = {}
    with open(SECTOR_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['variable'] != 'count':
                continue
            val = row['value']
            if not val or val == '-':
                continue
            try:
                count = int(val)
            except ValueError:
                try:
                    count = int(float(val))
                except ValueError:
                    continue
            if count > 0:
                data[(row['yrke4'], row['alder_gr'], row['sekt'], row['date'])] = count
    return data


def load_exposure():
    mapping = {}
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['quintile'] and len(row['styrk08']) == 4:
                mapping[row['styrk08']] = int(row['quintile'])
    return mapping


# ---------------------------------------------------------------------------
# Figure 10 - specific occupations by age, per sector
# ---------------------------------------------------------------------------
def plot_figure10(sector_data, sekt_code, suffix, sector_name, pop, factors):
    norm_dt = date_to_dt(NORM_DATE)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    for ax, (occ_label, occ_codes) in zip(axes.flatten(), FIGURE10_OCCUPATIONS):
        for age_label in AGE_LABELS:
            age_grs = [k for k, v in AGE_MAP.items() if v == age_label]
            if age_label == '50+':
                age_grs = list(AGE_50PLUS)

            emp_by_dt = defaultdict(int)
            for code in occ_codes:
                for ag in age_grs:
                    for (y, a, s, d), count in sector_data.items():
                        if y == code and a == ag and s == sekt_code:
                            emp_by_dt[date_to_dt(d)] += count

            raw = {}
            for dt, emp in emp_by_dt.items():
                adj = compute_adjusted_rate(emp, age_label, dt, pop, factors)
                if adj is not None:
                    raw[dt] = adj

            normed = normalize(raw, norm_dt)
            normed = filter_range(normed)
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
        ax.set_ylim(0.4, 1.6)

    fig.autofmt_xdate(rotation=0, ha='center')
    fig.suptitle(f'Employment per capita by age group, {sector_name} sector\n'
                 '(October 2022 = 1)', fontweight='semibold')
    note = (
        f'Notes: Employment per capita (SSB table 07459) with composition '
        f'adjustment (ref: 2021-Q1) in {sector_name.lower()} sector, '
        'normalized to October 2022 = 1.\n'
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        'Sector: State (1110,1120,6100), Municipal (1510,1520,6500), Private (other).'
    )
    fig.tight_layout(w_pad=3, h_pad=3, rect=(0, 0, 1, 0.95))
    place_note(fig, axes, note, y=0.01)
    out = FIG_DIR / f'figure10{suffix}_{sector_name.lower()}_by_age.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


# ---------------------------------------------------------------------------
# Figure 11 - quintile x age grid, per sector
# ---------------------------------------------------------------------------
def plot_figure11(sector_data, exposure, sekt_code, suffix, sector_name,
                  pop, factors):
    norm_dt = date_to_dt(NORM_DATE)

    # Aggregate by quintile
    agg = defaultdict(int)
    agg_all = defaultdict(int)
    for (yrke4, ag, sekt, date_str), count in sector_data.items():
        if sekt != sekt_code:
            continue
        if yrke4 not in exposure:
            continue
        al = get_age_label(ag)
        if not al:
            continue
        dt = date_to_dt(date_str)
        q = exposure[yrke4]
        agg[(al, q, dt)] += count
        agg_all[(al, dt)] += count

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
            normed = filter_range(normed)
            if not normed:
                continue
            dates, vals = zip(*sorted(normed.items()))
            ax.plot(dates, vals, color=QUINTILE_COLORS[q], linewidth=1.6)

        raw_all_emp = {dt: v for (a, dt), v in agg_all.items() if a == al}
        raw_all = {}
        for dt, emp in raw_all_emp.items():
            adj = compute_adjusted_rate(emp, al, dt, pop, factors)
            if adj is not None:
                raw_all[dt] = adj
        normed_all = normalize(raw_all, norm_dt)
        normed_all = filter_range(normed_all)
        if normed_all:
            d, v = zip(*sorted(normed_all.items()))
            ax.plot(d, v, color='red', linewidth=2.0)

        ax.axhline(y=1.0, color='#AAAAAA', linestyle='-', linewidth=0.5)
        ax.axvline(x=CHATGPT_LAUNCH, color='#555555', linestyle='--',
                   linewidth=0.7, alpha=0.8)
        ax.set_title(TITLE_MAP[al])
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
    fig.suptitle(f'Employment per capita by age and AI-exposure quintile, {sector_name} sector\n'
                 '(October 2022 = 1)', y=1.03, fontweight='semibold')
    note = (
        f'Notes: Employment per capita (SSB table 07459) with composition '
        f'adjustment (ref: 2021-Q1) in {sector_name.lower()} sector, '
        'normalized to October 2022 = 1.\n'
        'Dashed vertical line marks the launch of ChatGPT (November 2022). '
        'Exposure quintiles based on Eloundou et al. (2024) GPT-4 beta.'
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    place_note(fig, axes, note, y=0.03)
    out = FIG_DIR / f'figure11{suffix}_{sector_name.lower()}_by_quintile.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved {out}")


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    print("Loading data...")
    sector_data = load_sector_counts()
    exposure = load_exposure()
    pop = load_population_monthly()
    factors = load_composition_factors()
    print(f"  {len(sector_data):,} sector-count cells, {len(exposure)} exposure codes, "
          f"{len(pop)} pop entries")

    for sekt_code, suffix, sector_name in SECTORS:
        n = sum(1 for (y, a, s, d) in sector_data if s == sekt_code)
        print(f"\n{sector_name} sector: {n:,} cells")
        plot_figure10(sector_data, sekt_code, suffix, sector_name, pop, factors)
        plot_figure11(sector_data, exposure, sekt_code, suffix, sector_name,
                      pop, factors)


if __name__ == '__main__':
    main()
