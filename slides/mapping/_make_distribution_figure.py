"""Build the Eloundou β distribution figure for the slides.

Two panels side-by-side:
  Left:  unweighted distribution (one observation per STYRK code)
  Right: employment-weighted distribution (weighted by Dec 2025 employment),
         with the dominant Norwegian occupations annotated on the largest spikes.
"""

import csv
import textwrap
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent  # slides/mapping/_make_distribution_figure.py -> repo root
DATA = BASE / 'data'
OUT = HERE / 'eloundou_distribution.pdf'


def load_beta():
    out = {}
    with open(DATA / 'ai_exposure' / 'styrk08_eloundou_beta_mapping.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                out[r['styrk08']] = float(r['eloundou_beta'])
            except ValueError:
                pass
    return out


def load_employment_dec2025():
    out = defaultdict(int)
    with open(DATA / '01_occ_agemonth_count_2021_2026.csv', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['date'].startswith('2025-12'):
                try:
                    out[r['yrke4']] += int(r['count'])
                except ValueError:
                    pass
    return out


def load_titles():
    titles = {}
    with open(DATA / 'ai_exposure' / 'styrk08_codes.csv', encoding='cp1252') as f:
        for row in csv.DictReader(f):
            if row['level'] == '4':
                titles[row['code']] = row['name']
    return titles


def wrap_label(title, emp_k, width=20):
    """Wrap a Norwegian title onto multiple lines and append (NK) suffix."""
    title = title.split(' mv.')[0].split(',')[0].strip()
    lines = textwrap.wrap(title, width=width, break_long_words=False)
    if not lines:
        lines = [title]
    lines[-1] = f'{lines[-1]} ({emp_k:.0f}K)'
    return '\n'.join(lines)


def main():
    beta = load_beta()
    emp = load_employment_dec2025()
    titles = load_titles()

    pairs = [(s, b, emp.get(s, 0)) for s, b in beta.items()]
    n_total = len(pairs)
    total_emp = sum(e for _, _, e in pairs)

    betas = np.array([b for _, b, _ in pairs])
    weights = np.array([e for _, _, e in pairs], dtype=float)

    fig, axes = plt.subplots(1, 2, figsize=(11, 5.0), sharey=False)
    fc_unw = '#7B9FCB'
    fc_w = '#E07A2B'

    bins = np.linspace(0, 1, 21)

    # Left: unweighted
    ax = axes[0]
    counts_u, _, _ = ax.hist(betas, bins=bins, color=fc_unw,
                              edgecolor='white', linewidth=0.5)
    ax.set_title(f'Unweighted (N = {n_total} STYRK codes)', fontsize=11)
    ax.set_xlabel(r'Eloundou occupation $\beta$')
    ax.set_ylabel('Number of STYRK-08 codes')
    ymax_u = max(counts_u) * 1.20
    ax.set_ylim(0, ymax_u)
    umean = float(np.mean(betas))
    ax.axvline(umean, color='black', linewidth=0.8, linestyle='--')
    ax.text(umean + 0.01, ymax_u * 0.03,
            f'mean = {umean:.3f}', fontsize=9, va='bottom', ha='left')

    # Right: employment-weighted
    ax = axes[1]
    counts_w, edges, _ = ax.hist(
        betas, bins=bins, weights=weights / 1000, color=fc_w,
        edgecolor='white', linewidth=0.5,
    )
    wmean = float(np.average(betas, weights=weights))
    ax.set_title(f'Weighted by Dec 2025 employment ({total_emp / 1e6:.2f}M workers)', fontsize=11)
    ax.set_xlabel(r'Eloundou occupation $\beta$')
    ax.set_ylabel('Employment (thousands)')

    # --- Annotate the dominant occupations on the largest spikes ---
    bin_to_occs = defaultdict(list)
    for s, b, e in pairs:
        if e <= 0:
            continue
        bi = min(int(b * 20), 19)
        bin_to_occs[bi].append((e, s, b))

    # Y-axis stops just above the tallest spike. All labels sit tight against
    # their bars (above for the two leftmost, to the right for the three on
    # the right side) and stay inside this range.
    ymax = 660
    ax.set_ylim(0, ymax)

    # mean tag sits just above the x-axis (may overlap small bars)
    ax.axvline(wmean, color='black', linewidth=0.8, linestyle='--')
    ax.text(wmean + 0.01, ymax * 0.03,
            f'mean = {wmean:.3f}', fontsize=9, va='bottom', ha='left')

    top_bins = sorted(range(len(counts_w)), key=lambda i: -counts_w[i])[:5]
    annot_data = []
    for bi in top_bins:
        occs = sorted(bin_to_occs[bi], key=lambda x: -x[0])
        e, s, _ = occs[0]
        label = wrap_label(titles.get(s, s), e / 1000)
        x_center = edges[bi] + (edges[bi+1] - edges[bi]) / 2
        annot_data.append((bi, x_center, counts_w[bi], label))

    annot_data.sort(key=lambda a: a[1])
    left = [a for a in annot_data if a[1] < 0.28]
    right = [a for a in annot_data if a[1] >= 0.28]

    # Left side: label sits just above the bar, with a small fixed gap
    gap_left = ymax * 0.02
    for bi, x, y, label in left:
        ax.annotate(
            label, xy=(x, y), xytext=(x, y + gap_left),
            ha='center', va='bottom', fontsize=7,
            arrowprops=dict(arrowstyle='-', color='black', linewidth=0.4,
                            shrinkA=0, shrinkB=0),
            bbox=dict(boxstyle='round,pad=0.20', fc='white',
                      ec='black', lw=0.3, alpha=0.95),
        )

    # Right side: label sits immediately to the right of the bar, at bar top
    bw = edges[1] - edges[0]
    for bi, x, y, label in right:
        ax.annotate(
            label, xy=(x + bw / 2, y * 0.98), xytext=(x + bw * 0.7, y),
            ha='left', va='top', fontsize=7,
            arrowprops=dict(arrowstyle='-', color='black', linewidth=0.4,
                            shrinkA=0, shrinkB=0),
            bbox=dict(boxstyle='round,pad=0.20', fc='white',
                      ec='black', lw=0.3, alpha=0.95),
        )

    for ax in axes:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_xlim(0, 1)

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches='tight')
    print(f'Wrote {OUT}')
    print(f'  N STYRK codes with beta: {n_total}')
    print(f'  Unweighted mean beta: {umean:.4f}')
    print(f'  Employment-weighted mean beta: {wmean:.4f}')


if __name__ == '__main__':
    main()
