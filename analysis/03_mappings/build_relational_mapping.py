"""
Build a human-relational content mapping to STYRK-08.

This is the *relational axis* of the relational-economy x AI-exposure measure
(see relational-economy/INTEGRATION_PLAN.md). It deliberately contributes ONLY
the relational content; AI exposure comes from the repo's canonical measures
(styrk08_felten_mapping.csv, styrk08_eloundou_beta_mapping.csv). The combined
table + quadrant classification is assembled in build_combined_styrk_exposure.py.

Relational content (O*NET 29.1 importance, Deming 2017 grounding):
  care    = mean importance of
              Establishing & Maintaining Interpersonal Relationships (4.A.4.a.4),
              Assisting & Caring for Others                          (4.A.4.a.5),
              Performing for / Working with the Public               (4.A.4.a.8)   [Work Activities]
              Social Perceptiveness                                  (2.B.1.a),
              Service Orientation                                    (2.B.1.f)      [Skills]
  deming  = mean importance of Deming (2017)'s four social skills:
              Social Perceptiveness (2.B.1.a), Coordination (2.B.1.b),
              Persuasion (2.B.1.c), Negotiation (2.B.1.d)            [Skills]
  relational = mean( z(care), z(deming) ), standardized over the O*NET-SOC universe.

Crosswalk: O*NET-SOC (6-digit) -> SOC 2010 -> ISCO-08 -> STYRK-08, reusing the
exact loaders from build_eloundou_mapping.py so this measure lands on the same
STYRK-08 universe as the canonical exposure series.

Output: data/ai_exposure/styrk08_relational_mapping.csv
"""

import csv
from collections import defaultdict
from pathlib import Path

import pandas as pd

# Reuse the canonical crosswalk loaders + manual corrections (identical chain).
from build_eloundou_mapping import (
    MANUAL_STYRK_MAP,
    MANUAL_STYRK_SOC_MAP,
    load_soc_2018_to_2010,
    load_soc2010_to_isco08,
    load_styrk08_codes,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'
ONET_DIR = DATA_DIR / 'onet_relational'
OUTPUT_FILE = DATA_DIR / 'styrk08_relational_mapping.csv'

# O*NET 29.1 element IDs (verified)
CARE_WA = ['4.A.4.a.4', '4.A.4.a.5', '4.A.4.a.8']   # Work Activities
CARE_SK = ['2.B.1.a', '2.B.1.f']                     # Skills
DEMING_SK = ['2.B.1.a', '2.B.1.b', '2.B.1.c', '2.B.1.d']  # Skills (Deming 2017)


def _importance(path: Path) -> pd.DataFrame:
    """O*NET text file -> rows of (soc6, Element ID, value) for the IM scale."""
    df = pd.read_csv(path, sep='\t', dtype=str)
    df = df[df['Scale ID'] == 'IM'].copy()
    # O*NET-SOC '11-1011.00' -> 6-digit SOC '11-1011' (matches Eloundou handling)
    df['soc6'] = df['O*NET-SOC Code'].str.split('.').str[0]
    df['val'] = pd.to_numeric(df['Data Value'], errors='coerce')
    return df[['soc6', 'Element ID', 'val']]


def relational_by_soc6() -> dict[str, float]:
    """Standardized relational composite per 6-digit O*NET-SOC code."""
    wa = _importance(ONET_DIR / 'Work Activities.txt')
    sk = _importance(ONET_DIR / 'Skills.txt')

    def idx(df, ids):
        return df[df['Element ID'].isin(ids)].groupby('soc6')['val'].mean()

    care = (pd.concat([idx(wa, CARE_WA), idx(sk, CARE_SK)])
            .groupby(level=0).mean())
    deming = idx(sk, DEMING_SK)

    def z(s):
        return (s - s.mean()) / s.std(ddof=0)

    rel = pd.concat([z(care).rename('z_care'),
                     z(deming).rename('z_deming')], axis=1)
    rel['relational'] = rel[['z_care', 'z_deming']].mean(axis=1, skipna=True)
    out = rel['relational'].dropna()
    print(f"  O*NET relational: {len(out)} SOC-6 codes "
          f"(care n={care.notna().sum()}, deming n={deming.notna().sum()})")
    return out.to_dict()


def add_quintiles(results: list[dict]) -> None:
    # Equal-frequency quintiles (each occupation counts once), identical to the
    # rule in build_eloundou_mapping.py / build_handa_mapping.py and the
    # dashboard: pd.qcut on the first-occurrence rank. Callers sort results by
    # styrk08 before this, so ties break deterministically.
    vals = pd.Series([r['relational'] for r in results], dtype=float)
    ranks = vals.rank(method='first')
    quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    pctl = (ranks - 1) / (len(vals) - 1) * 100.0
    for i, r in enumerate(results):
        r['pctl_rank'] = round(float(pctl.iloc[i]), 2)
        r['quintile'] = int(quint.iloc[i])


def build_mapping() -> None:
    print("Loading O*NET 29.1 relational importance...")
    soc6_relational = relational_by_soc6()

    print("Loading SOC 2018 -> SOC 2010 crosswalk...")
    soc18_to_10 = load_soc_2018_to_2010()
    print("Loading SOC 2010 -> ISCO-08 crosswalk...")
    soc10_to_isco, partial_flags = load_soc2010_to_isco08()
    print("Loading STYRK-08 codes...")
    styrk_codes = load_styrk08_codes()
    print(f"  {len(styrk_codes)} valid STYRK-08 codes")

    # Step 1: O*NET-SOC (6-digit, SOC-2018 vintage) -> SOC 2010
    soc2010_scores: dict[str, list[float]] = defaultdict(list)
    unmapped_18 = 0
    for soc18, val in soc6_relational.items():
        if soc18 in soc18_to_10:
            for soc10 in soc18_to_10[soc18]:
                soc2010_scores[soc10].append(val)
        else:
            unmapped_18 += 1
    print(f"\n  O*NET-SOC -> SOC 2010: {len(soc2010_scores)} SOC 2010 codes, "
          f"{unmapped_18} O*NET-SOC codes unmapped (vintage gap)")

    # Step 2: SOC 2010 -> ISCO-08
    isco_contributions: dict[str, list[dict]] = defaultdict(list)
    unmapped_10 = 0
    for soc10, vals in soc2010_scores.items():
        avg = sum(vals) / len(vals)
        if soc10 in soc10_to_isco:
            for isco in soc10_to_isco[soc10]:
                isco_contributions[isco].append({
                    'val': avg,
                    'partial': partial_flags.get((soc10, isco), False),
                })
        else:
            unmapped_10 += 1
    print(f"  SOC 2010 -> ISCO-08: {len(isco_contributions)} ISCO-08 codes, "
          f"{unmapped_10} SOC 2010 codes unmapped")

    # Step 3: filter to valid STYRK-08 codes
    results = []
    for isco, contribs in sorted(isco_contributions.items()):
        if isco not in styrk_codes:
            continue
        results.append({
            'styrk08': isco,
            'relational': round(sum(c['val'] for c in contribs) / len(contribs), 6),
            'n_soc_matched': len(contribs),
            'has_partial_match': 1 if any(c['partial'] for c in contribs) else 0,
            'manual_map': '',
        })

    # Same-code STYRK/ISCO corrections -> use direct SOC sources
    manual_targets = set(MANUAL_STYRK_SOC_MAP)
    results = [r for r in results if r['styrk08'] not in manual_targets]
    for styrk_target, soc_sources in MANUAL_STYRK_SOC_MAP.items():
        if styrk_target not in styrk_codes:
            continue
        vals = [sum(soc2010_scores[s]) / len(soc2010_scores[s])
                for s in soc_sources if soc2010_scores.get(s)]
        used = [s for s in soc_sources if soc2010_scores.get(s)]
        if not vals:
            continue
        results.append({
            'styrk08': styrk_target,
            'relational': round(sum(vals) / len(vals), 6),
            'n_soc_matched': len(used),
            'has_partial_match': 0,
            'manual_map': 'SOC:' + ';'.join(used),
        })
        print(f"  Manual SOC map: {styrk_target} <- {';'.join(used)}")

    # Norway-specific codes without SOC equivalent -> copy from a sibling STYRK code
    mapped = {r['styrk08'] for r in results}
    for styrk_target, styrk_source in MANUAL_STYRK_MAP.items():
        if styrk_target in mapped or styrk_target not in styrk_codes:
            continue
        src = next((r for r in results if r['styrk08'] == styrk_source), None)
        if src:
            row = dict(src)
            row['styrk08'] = styrk_target
            row['manual_map'] = styrk_source
            results.append(row)
            print(f"  Manual map: {styrk_target} <- {styrk_source}")

    results.sort(key=lambda r: r['styrk08'])
    add_quintiles(results)

    print(f"\n  Final: {len(results)} STYRK-08 codes with relational scores "
          f"({100 * len(results) / len(styrk_codes):.1f}% of {len(styrk_codes)})")
    print(f"  Relational range: {min(r['relational'] for r in results):.3f} "
          f"- {max(r['relational'] for r in results):.3f}")

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'styrk08', 'relational', 'pctl_rank', 'quintile',
            'n_soc_matched', 'has_partial_match', 'manual_map',
        ])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    build_mapping()
