"""Generate LaTeX task tables for the worked-example slides.

For each SOC code, emit a 2-column tabular environment listing all tasks with
their E rating, β, and an aggregate row.
"""

import csv
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # slides/mapping/_make_task_tables.py -> repo root
TASK_FILE = BASE / 'data' / 'ai_exposure' / 'eloundou' / 'full_labelset.tsv'

SOCS = [
    ('47-2031', 'Carpenters', 'Tømrere og snekkere', '7115'),
    ('25-2031', 'Secondary School Teachers', 'Lektorer (vgs.)', '2330'),
    ('23-1011', 'Lawyers', 'Jurister og advokater', '2611'),
    ('19-3011', 'Economists', 'Forskere/rådgivere, samf.økonomi', '2631'),
]


def shorten(s, n=58):
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'\s*\([^)]{6,}\)', '', s)  # drop long parenthetical notes
    s = s.replace('&', '\\&').replace('%', '\\%').replace('_', '\\_').replace('#', '\\#')
    s = s.replace('—', '--').replace('"', "''")
    if len(s) > n:
        s = s[: n - 1].rsplit(' ', 1)[0].rstrip(',.;:') + '…'
    return s


def load_tasks(soc):
    tasks = []
    with open(TASK_FILE, encoding='utf-8') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['O*NET-SOC Code'].split('.')[0] == soc:
                tasks.append({
                    'onet': r['O*NET-SOC Code'],
                    'task': r['Task'],
                    'E': r['gpt4_exposure'],
                    'beta': float(r['beta']),
                })
    return tasks


def specialty_betas(tasks):
    by = {}
    for t in tasks:
        by.setdefault(t['onet'], []).append(t)
    return {k: sum(t['beta'] for t in v) / len(v) for k, v in by.items()}


def emit_table(soc, eng_title, nor_title, styrk):
    tasks = load_tasks(soc)
    n = len(tasks)
    e0 = sum(1 for t in tasks if t['E'] == 'E0')
    e1 = sum(1 for t in tasks if t['E'] == 'E1')
    e2 = sum(1 for t in tasks if t['E'] == 'E2')
    sp_betas = specialty_betas(tasks)
    soc_beta = sum(sp_betas.values()) / len(sp_betas)

    # Two-column layout: split tasks into two halves
    half = (n + 1) // 2
    left = tasks[:half]
    right = tasks[half:]

    lines = []
    lines.append(r'\begin{tabular}{p{6.0cm}cc @{\hspace{0.4cm}} p{6.0cm}cc}')
    lines.append(r'\toprule')
    lines.append(r'O*NET task & $E$ & $\beta$ & O*NET task & $E$ & $\beta$ \\')
    lines.append(r'\midrule')
    for i in range(max(len(left), len(right))):
        l = left[i] if i < len(left) else None
        r_ = right[i] if i < len(right) else None
        lcell = f"{shorten(l['task'])} & ${l['E'].replace('E','E_')}$ & {l['beta']:.1f}" if l else ' & & '
        rcell = f"{shorten(r_['task'])} & ${r_['E'].replace('E','E_')}$ & {r_['beta']:.1f}" if r_ else ' & & '
        lines.append(f'{lcell} & {rcell} \\\\')
    lines.append(r'\midrule')
    if len(sp_betas) == 1:
        lines.append(f'\\multicolumn{{6}}{{l}}{{\\textbf{{Counts:}} {e0} $E_0$ \\quad {e1} $E_1$ \\quad {e2} $E_2$\\quad\\quad'
                     f'\\textbf{{SOC $\\beta$ (mean of {n} tasks):}} \\textbf{{{soc_beta:.4f}}}}} \\\\')
    else:
        per_sp = ',\\;\\;'.join(f'{k}: {v:.3f}' for k, v in sp_betas.items())
        lines.append(f'\\multicolumn{{6}}{{l}}{{\\textbf{{Counts:}} {e0} $E_0$ \\quad {e1} $E_1$ \\quad {e2} $E_2$}} \\\\')
        lines.append(f'\\multicolumn{{6}}{{l}}{{\\textbf{{Per O*NET specialty:}} {per_sp}}} \\\\')
        lines.append(f'\\multicolumn{{6}}{{l}}{{\\textbf{{SOC $\\beta$ (mean of {len(sp_betas)} specialties):}} \\textbf{{{soc_beta:.4f}}}}} \\\\')
    lines.append(r'\bottomrule')
    lines.append(r'\end{tabular}')

    return '\n'.join(lines)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    for soc, eng, nor, styrk in SOCS:
        print(f'\n%% ===== {soc} {eng} ({nor}, STYRK {styrk}) =====')
        print(emit_table(soc, eng, nor, styrk))
