"""
Closest occupations by O*NET work content, per STYRK-08 code.

For the "velg et yrke" flow on the occupation panel: the user picks one
occupation and the panel shows the three occupations whose work content is
most similar.

Why not task statements: O*NET task statements are written per occupation
and almost never repeat across SOC codes, so exact task overlap is zero for
most pairs (2512 software developers shares two statements with one other
code, 4110 office clerks shares none). O*NET's Work Activities (41
generalized activities) and Skills (35) are scored for every occupation on
the same scale, so they give a dense profile of what the work consists of.

Method
  1. Per O*NET-SOC code: importance (IM) of the 41 work activities and 35
     skills, from data/ai_exposure/onet_relational/.
  2. O*NET-SOC -> SOC 2010 -> ISCO-08 -> STYRK-08 with the crosswalk chain
     from build_eloundou_mapping.py (plus its manual fixes). A STYRK code's
     profile is the mean over contributing SOC codes.
  3. Each element is standardized across STYRK codes (z-score), so common
     activities like "Getting information" do not dominate. Similarity is the
     cosine of the z-scored 76-dimensional profiles.
  4. Codes that share the same SOC set (e.g. the Norwegian nurse codes that
     all point at 2221) get similarity 1 and are listed first.

Output: data/ai_exposure/styrk08_task_neighbours.csv
  styrk08, rank, neighbour, similarity, n_soc, n_soc_neighbour
"""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_eloundou_mapping import (  # noqa: E402
    MANUAL_STYRK_MAP, MANUAL_STYRK_SOC_MAP,
    load_soc_2018_to_2010, load_soc2010_to_isco08, load_styrk08_codes,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'
ONET_DIR = DATA_DIR / 'onet_relational'
OUT = DATA_DIR / 'styrk08_task_neighbours.csv'
TOP_N = 5


ELEMENT_NAMES = {}


def importance(path):
    df = pd.read_csv(path, sep='\t', dtype=str)
    df = df[df['Scale ID'] == 'IM'].copy()
    ELEMENT_NAMES.update(dict(zip(df['Element ID'], df['Element Name'])))
    df['soc6'] = df['O*NET-SOC Code'].str.split('.').str[0]
    df['val'] = pd.to_numeric(df['Data Value'], errors='coerce')
    # Several O*NET-SOC codes (e.g. 15-1252.00 and 15-1252.01) share a
    # 6-digit SOC; average them.
    return df.groupby(['soc6', 'Element ID'])['val'].mean().unstack()


def main():
    prof18 = pd.concat([importance(ONET_DIR / 'Work Activities.txt'),
                        importance(ONET_DIR / 'Skills.txt')], axis=1).dropna()
    print(f'O*NET profiles: {prof18.shape[0]} SOC-6 codes x {prof18.shape[1]} elements')

    soc18_to_10 = load_soc_2018_to_2010()
    soc10_to_isco, _ = load_soc2010_to_isco08()
    styrk_codes = load_styrk08_codes()

    # O*NET-SOC (2018) -> SOC 2010 profiles.
    rows10 = defaultdict(list)
    for soc18, vec in prof18.iterrows():
        for soc10 in soc18_to_10.get(soc18, []):
            rows10[soc10].append(vec)
    prof10 = {s: pd.concat(v, axis=1).mean(axis=1) for s, v in rows10.items()}

    # SOC 2010 -> STYRK-08 (via ISCO), with the manual fixes.
    socs_per_styrk = defaultdict(set)
    for soc10 in prof10:
        for isco in soc10_to_isco.get(soc10, []):
            if isco in styrk_codes:
                socs_per_styrk[isco].add(soc10)
    for target, socs in MANUAL_STYRK_SOC_MAP.items():
        socs_per_styrk[target] = {s for s in socs if s in prof10}
    for target, source in MANUAL_STYRK_MAP.items():
        if target not in socs_per_styrk and source in socs_per_styrk:
            socs_per_styrk[target] = set(socs_per_styrk[source])

    prof = pd.DataFrame({styrk: pd.concat([prof10[s] for s in socs], axis=1).mean(axis=1)
                         for styrk, socs in socs_per_styrk.items() if socs}).T
    z = (prof - prof.mean()) / prof.std(ddof=0)
    z = z.fillna(0.0)
    norms = (z ** 2).sum(axis=1).pow(0.5)
    sim = z.dot(z.T).div(norms, axis=0).div(norms, axis=1)
    print(f'{len(prof)} STYRK-08 codes with profiles')

    rows = []
    for a in sorted(prof.index):
        s = sim.loc[a].drop(a).sort_values(ascending=False)
        for rank, (b, val) in enumerate(s.head(TOP_N).items(), start=1):
            # The elements that pull the pair together: both occupations
            # score high (or both low) on them. Shown on the panel so the
            # similarity is not a black box.
            contrib = (z.loc[a] * z.loc[b])
            top = contrib[(z.loc[a] > 0) & (z.loc[b] > 0)].sort_values(ascending=False).head(3)
            rows.append({'styrk08': a, 'rank': rank, 'neighbour': b,
                         'similarity': round(float(val), 4),
                         'n_soc': len(socs_per_styrk[a]),
                         'n_soc_neighbour': len(socs_per_styrk[b]),
                         'shared_elements': '; '.join(ELEMENT_NAMES.get(e, e) for e in top.index)})
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} neighbour rows -> {OUT.name}')


if __name__ == '__main__':
    main()
