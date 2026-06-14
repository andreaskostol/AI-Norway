"""
Share of Norwegian employment in each Eloundou GPT-4 exposure quintile,
latest available month. Bar chart with a 20 % reference line that marks
where each quintile would sit under equal-employment quintiles. The
deviation from 20 % shows whether high-exposure occupations are over- or
under-represented in the workforce.
"""

import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_FILE = BASE_DIR / 'data' / '01_occ_agemonth_count_2021_2026.csv'
EXPOSURE_FILE = BASE_DIR / 'data' / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv'
FIG_DIR = BASE_DIR / 'analysis' / 'output' / 'figures'

REF_DATE = '2026-02-16'
REF_LABEL = 'February 2026'
WORKING_AGES = {'2', '3', '4', '5', '6', '7', '8'}  # 22-69

QUINTILE_COLORS = {
    1: '#C6DBEF',
    2: '#9ECAE1',
    3: '#4292C6',
    4: '#2171B5',
    5: '#08306B',
}


def healy_style() -> None:
    plt.rcParams.update({
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
        'savefig.facecolor': 'white',
        'axes.linewidth':    0.5,
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'axes.edgecolor':    '#333333',
        'axes.grid':         True,
        'axes.axisbelow':    True,
        'grid.color':        '#BBBBBB',
        'grid.linewidth':    0.7,
        'grid.linestyle':    '-',
        'xtick.major.width': 0.4,
        'ytick.major.width': 0.4,
        'xtick.color':       '#333333',
        'ytick.color':       '#333333',
        'font.family':       'serif',
        'font.serif':        ['Times New Roman', 'Times', 'DejaVu Serif'],
        'font.size':         16,
        'axes.titlesize':    20,
        'axes.labelsize':    18,
        'xtick.labelsize':   16,
        'ytick.labelsize':   16,
        'figure.titlesize':  22,
    })


def load_quintiles() -> dict[str, int]:
    with open(EXPOSURE_FILE, encoding='utf-8') as f:
        return {row['styrk08'].zfill(4): int(row['quintile'])
                for row in csv.DictReader(f)
                if row['quintile'] and len(row['styrk08'].zfill(4)) == 4}


def load_employment_by_quintile():
    quintile = load_quintiles()
    by_q = defaultdict(int)
    total = 0
    unmapped = 0
    with open(DATA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['date'] != REF_DATE:
                continue
            if row['alder_gr'] not in WORKING_AGES:
                continue
            n = int(row['count']) if row['count'] else 0
            total += n
            q = quintile.get(row['yrke4'])
            if q is None:
                unmapped += n
            else:
                by_q[q] += n
    return by_q, total, unmapped


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    healy_style()

    by_q, total, unmapped = load_employment_by_quintile()
    quintiles = [1, 2, 3, 4, 5]
    shares = [100 * by_q[q] / total for q in quintiles]
    cum_top = sum(shares[3:])  # Q4+Q5

    fig, ax = plt.subplots(figsize=(10, 6.5))

    bars = ax.bar(quintiles, shares,
                  color=[QUINTILE_COLORS[q] for q in quintiles],
                  edgecolor='#333333', linewidth=0.6, width=0.7)

    # Reference line at 20 % (equal-employment benchmark)
    ax.axhline(y=20, color='#999999', linestyle='--', linewidth=1.0,
               zorder=0)
    ax.text(5.45, 20, 'Equal-employment\nbenchmark (20 %)',
            fontsize=12, color='#666666', va='center', ha='left')

    # Value labels on each bar
    for bar, share in zip(bars, shares):
        ax.text(bar.get_x() + bar.get_width() / 2, share + 0.5,
                f'{share:.1f} %', ha='center', va='bottom',
                fontsize=15, color='#333333')

    ax.set_xticks(quintiles)
    ax.set_xticklabels(['Q1\nleast\nexposed', 'Q2', 'Q3', 'Q4',
                        'Q5\nmost\nexposed'])
    ax.set_ylabel('Share of total employment (%)')
    ax.set_xlabel('Eloundou et al.\\ GPT-4 $\\beta$ exposure quintile')
    ax.set_ylim(0, 31)
    ax.set_xlim(0.4, 6.8)

    ax.set_title(f'Norwegian employment by AI-exposure quintile, {REF_LABEL}\n'
                 f'Q4 + Q5 (top 40 % of occupations) hold '
                 f'{cum_top:.0f} % of total employment',
                 fontweight='semibold', pad=14)

    note = (
        f'Notes: Employment counts for ages 22–69 in {REF_LABEL}. '
        f'Quintiles are equal-occupation: each 4-digit STYRK-08 code counts '
        f'once, with Q5 containing the 20 % of occupations with the highest '
        f'Eloundou et al. (2024) GPT-4 $\\beta$ exposure scores. Under '
        f'equal-employment quintiles every bar would sit at 20 %. The '
        f'{(100*unmapped/total):.1f} % of employment in unmapped occupations '
        f'(military, clergy, small specialties) is excluded from the shares. '
        f'Source: microdata.no.'
    )
    fig.text(0.05, 0.02, note, fontsize=11, color='#555555',
             wrap=True, ha='left', va='bottom')

    fig.tight_layout(rect=(0, 0.10, 1, 1))

    out = FIG_DIR / 'figure_eloundou_employment_share.pdf'
    fig.savefig(str(out), dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {out}')


if __name__ == '__main__':
    main()
