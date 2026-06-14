"""Pick worked-example STYRK codes for each measure.

Selection rule per measure:
  - n_soc_matched == 1
  - has_partial_match == 0
  - max_partial_fanout == 0 (where present)

Run from repo root: python slides/_pick_examples.py
"""

import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent.parent  # slides/mapping/_pick_examples.py -> repo root
DATA = BASE / 'data' / 'ai_exposure'


def load_titles():
    titles = {}
    with open(DATA / 'styrk08_codes.csv', encoding='cp1252') as f:
        for row in csv.DictReader(f):
            if row['level'] == '4':
                titles[row['code']] = row['name']
    return titles


def pick(measure_csv, score_col, label):
    titles = load_titles()
    rows = []
    with open(DATA / measure_csv, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                if int(r['n_soc_matched']) != 1:
                    continue
                if int(r['has_partial_match']) != 0:
                    continue
                if 'max_partial_fanout' in r and r['max_partial_fanout']:
                    if int(r['max_partial_fanout']) != 0:
                        continue
            except (KeyError, ValueError):
                continue
            rows.append(r)
    print(f"\n=== {label}: clean one-to-one (n=1, no partial match) ===")
    print(f"   total candidates: {len(rows)}")
    selected = []
    for r in rows:
        styrk = r['styrk08']
        if not styrk.isdigit() or styrk[0] not in '23':
            continue
        try:
            score = float(r[score_col])
        except (KeyError, ValueError):
            continue
        # quintile in mid-range
        q = r.get('quintile') or r.get('q_overall_exposure') or r.get('q_aioe') or r.get('q_observed_exposure') or ''
        if q in ('3', '4', '5'):
            selected.append((styrk, titles.get(styrk, '?'), score, q, r))
    for styrk, title, score, q, r in selected[:15]:
        print(f"  {styrk}  Q{q}  {score:>7.4f}  {title}")
    return selected


if __name__ == '__main__':
    pick('styrk08_eloundou_beta_mapping.csv', 'eloundou_beta', 'Eloundou')
    pick('styrk08_handa_mapping.csv', 'overall_exposure', 'Handa')
    pick('styrk08_felten_mapping.csv', 'aioe', 'Felten')
    pick('styrk08_job_exposure_mapping.csv', 'observed_exposure', 'Anthropic')
