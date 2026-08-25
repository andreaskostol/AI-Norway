"""
Build Eloundou et al. (2024) GPT-4 beta exposure mapping to STYRK-08.

Chain: O*NET-SOC 2018 -> SOC 2010 -> ISCO-08 -> STYRK-08

The last step matches overlapping 4-digit ISCO-08 codes to the official
STYRK-08 list by code. STYRK-08 is based on ISCO-08 but includes Norwegian
adaptations, so this is a filtered code match rather than a claim that the
two classifications are exactly the same.

Quality flags per STYRK-08 code:
  - n_soc_matched: number of SOC codes contributing to this STYRK code
  - has_partial_match: 1 if any SOC→ISCO link is partial (*) in BLS crosswalk
  - manual_map: source STYRK code if manually mapped (for Norway-specific codes)

Data source:
- eloundou_occ_level.csv: Eloundou et al. (2024) occupation-level GPT-4 beta
  scores, downloaded from
  https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv

Crosswalk sources:
- SOC 2010 <-> SOC 2018: BLS (November 2017)
  https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx
- SOC 2010 <-> ISCO-08: BLS (August 2012, updated June 2015)
  https://www.bls.gov/soc/isco_soc_crosswalk.xls
"""

import csv
from pathlib import Path
from collections import defaultdict

import openpyxl
import xlrd
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'

ELOUNDOU_FILE = DATA_DIR / 'eloundou_occ_level.csv'
SOC_2010_2018_FILE = DATA_DIR / 'soc_2010_to_2018_crosswalk.xlsx'
SOC_ISCO_FILE = DATA_DIR / 'isco_soc_crosswalk.xls'
STYRK08_FILE = DATA_DIR / 'styrk08_codes.csv'
OUTPUT_FILE = DATA_DIR / 'styrk08_eloundou_beta_mapping.csv'

# Manual mappings for large Norwegian STYRK codes without SOC equivalent
MANUAL_STYRK_MAP = {
    '2223': '2221',  # Sykepleiere -> Nursing professionals
    '2224': '2221',  # Vernepleiere -> Nursing professionals
}

# Manual corrections for Norwegian STYRK adaptations where the same 4-digit
# BLS/ISCO code denotes a different occupation than the Norwegian STYRK code.
MANUAL_STYRK_SOC_MAP = {
    '2267': ['29-1122'],  # Ergoterapeuter -> Occupational Therapists
    '2269': ['29-1011'],  # Kiropraktorer mv. -> Chiropractors
}


def load_eloundou() -> dict[str, float]:
    """Load Eloundou GPT-4 beta scores keyed by 6-digit SOC 2018 code."""
    scores: dict[str, list[float]] = defaultdict(list)
    with open(ELOUNDOU_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            # O*NET codes like '11-1011.00' -> SOC '11-1011'
            onet = row['O*NET-SOC Code']
            soc6 = onet.split('.')[0]  # drop .XX suffix
            beta = float(row['dv_rating_beta'])
            scores[soc6].append(beta)
    # Average across O*NET detail codes within same SOC
    return {soc: sum(vals) / len(vals) for soc, vals in scores.items()}


def load_soc_2018_to_2010() -> dict[str, list[str]]:
    """Load SOC 2018 -> SOC 2010 mapping (reverse of the BLS file)."""
    wb = openpyxl.load_workbook(str(SOC_2010_2018_FILE))
    ws = wb.active
    mapping: dict[str, list[str]] = defaultdict(list)
    for row in ws.iter_rows(min_row=10, values_only=True):
        soc2010 = str(row[0]).strip() if row[0] else ''
        soc2018 = str(row[2]).strip() if row[2] else ''
        if soc2010 and soc2018 and '-' in soc2010:
            mapping[soc2018].append(soc2010)
    return dict(mapping)


def load_soc2010_to_isco08():
    """Load SOC 2010 -> ISCO-08 mapping with partial match flags."""
    wb = xlrd.open_workbook(str(SOC_ISCO_FILE))
    ws = wb.sheet_by_name('2010 SOC to ISCO-08')
    mapping: dict[str, list[str]] = defaultdict(list)
    partial: dict[tuple[str, str], bool] = {}
    for i in range(7, ws.nrows):
        soc2010 = str(ws.cell_value(i, 0)).strip()
        part_flag = str(ws.cell_value(i, 2)).strip()
        isco08 = str(ws.cell_value(i, 3)).strip()
        if soc2010 and isco08 and '-' in soc2010:
            if '.' in isco08:
                isco08 = isco08.split('.')[0]
            isco08 = isco08.zfill(4)
            mapping[soc2010].append(isco08)
            partial[(soc2010, isco08)] = (part_flag == '*')
    return dict(mapping), partial


def load_styrk08_codes() -> set[str]:
    """Load valid STYRK-08 4-digit codes."""
    codes = set()
    with open(STYRK08_FILE, encoding='latin-1') as f:
        for row in csv.DictReader(f):
            code = row.get('styrk08', row.get('code', ''))
            if len(code) == 4:
                codes.add(code)
    return codes


def build_mapping():
    print("Loading Eloundou GPT-4 beta scores...")
    eloundou = load_eloundou()
    print(f"  {len(eloundou)} unique SOC 2018 codes with beta scores")

    print("Loading SOC 2018 -> SOC 2010 crosswalk...")
    soc18_to_10 = load_soc_2018_to_2010()
    print(f"  {len(soc18_to_10)} SOC 2018 codes mapped")

    print("Loading SOC 2010 -> ISCO-08 crosswalk...")
    soc10_to_isco, partial_flags = load_soc2010_to_isco08()
    print(f"  {len(soc10_to_isco)} SOC 2010 codes mapped to ISCO-08")

    print("Loading STYRK-08 codes...")
    styrk_codes = load_styrk08_codes()
    print(f"  {len(styrk_codes)} valid STYRK-08 codes")

    # Step 1: SOC 2018 beta scores -> SOC 2010
    soc2010_scores: dict[str, list[float]] = defaultdict(list)
    unmapped_18 = 0
    for soc18, beta in eloundou.items():
        if soc18 in soc18_to_10:
            for soc10 in soc18_to_10[soc18]:
                soc2010_scores[soc10].append(beta)
        else:
            unmapped_18 += 1
    print(f"\n  SOC 2018 -> 2010: {len(soc2010_scores)} SOC 2010 codes, "
          f"{unmapped_18} SOC 2018 codes unmapped")

    # Step 2: SOC 2010 -> ISCO-08 (then filtered to valid STYRK-08 codes)
    isco_contributions: dict[str, list[dict]] = defaultdict(list)
    unmapped_10 = 0
    for soc10, betas in soc2010_scores.items():
        avg_beta = sum(betas) / len(betas)
        if soc10 in soc10_to_isco:
            fan_out = len(soc10_to_isco[soc10])
            for isco in soc10_to_isco[soc10]:
                is_partial = partial_flags.get((soc10, isco), False)
                isco_contributions[isco].append({
                    'beta': avg_beta,
                    'soc': soc10,
                    'partial': is_partial,
                    'fan_out': fan_out if is_partial else 1,
                    'n_soc_source': len(betas),
                })
        else:
            unmapped_10 += 1
    print(f"  SOC 2010 -> ISCO-08: {len(isco_contributions)} ISCO-08 codes, "
          f"{unmapped_10} SOC 2010 codes unmapped")

    # Step 3: Filter to valid STYRK-08 codes and compute final scores
    results = []
    for isco, contribs in sorted(isco_contributions.items()):
        if isco not in styrk_codes:
            continue
        avg_beta = sum(c['beta'] for c in contribs) / len(contribs)
        results.append({
            'styrk08': isco,
            'eloundou_beta': round(avg_beta, 6),
            'n_soc_matched': len(contribs),
            'has_partial_match': 1 if any(c['partial'] for c in contribs) else 0,
            'max_partial_fanout': max((c['fan_out'] for c in contribs if c['partial']), default=0),
            'manual_map': '',
        })

    # Replace misleading same-code STYRK/ISCO matches with direct SOC sources.
    manual_targets = set(MANUAL_STYRK_SOC_MAP)
    results = [r for r in results if r['styrk08'] not in manual_targets]
    for styrk_target, soc_sources in MANUAL_STYRK_SOC_MAP.items():
        if styrk_target not in styrk_codes:
            continue
        betas = []
        used_socs = []
        for soc in soc_sources:
            vals = soc2010_scores.get(soc)
            if not vals:
                continue
            betas.append(sum(vals) / len(vals))
            used_socs.append(soc)
        if not betas:
            print(f"  Manual SOC map skipped: {styrk_target} has no source scores")
            continue
        results.append({
            'styrk08': styrk_target,
            'eloundou_beta': round(sum(betas) / len(betas), 6),
            'n_soc_matched': len(used_socs),
            'has_partial_match': 0,
            'max_partial_fanout': 0,
            'manual_map': 'SOC:' + ';'.join(used_socs),
        })
        print(f"  Manual SOC map: {styrk_target} <- {';'.join(used_socs)}")

    # Apply manual mappings
    mapped_codes = {r['styrk08'] for r in results}
    for styrk_target, styrk_source in MANUAL_STYRK_MAP.items():
        if styrk_target in mapped_codes:
            continue
        if styrk_target not in styrk_codes:
            continue
        source_row = next((r for r in results if r['styrk08'] == styrk_source), None)
        if source_row:
            manual = dict(source_row)
            manual['styrk08'] = styrk_target
            manual['manual_map'] = styrk_source
            results.append(manual)
            print(f"  Manual map: {styrk_target} <- {styrk_source}")

    results.sort(key=lambda x: x['styrk08'])

    print(f"\n  Final: {len(results)} STYRK-08 codes with Eloundou beta scores")
    print(f"  Coverage: {len(results)}/{len(styrk_codes)} "
          f"({100*len(results)/len(styrk_codes):.1f}%)")

    # Quality summary
    n_partial = sum(1 for r in results if r['has_partial_match'])
    print(f"  With partial SOC->ISCO match: {n_partial}")

    # Assign equal-frequency quintiles (each occupation counts once), identical
    # to the rule in build_handa_mapping.py / build_job_exposure_mapping.py and
    # the companion dashboard (analysis/06_figures/plot_canaries_style_usage.py):
    # pd.qcut on the first-occurrence rank gives five equal-sized groups, and
    # pctl is the matching rank percentile (0-100). Codes are sorted by styrk08
    # first so ties break deterministically, matching the dashboard. The earlier
    # strict-less / pctl<=80 rule produced unequal groups and split borderline
    # codes onto the opposite side from the dashboard.
    results.sort(key=lambda r: r['styrk08'])
    betas = pd.Series([r['eloundou_beta'] for r in results], dtype=float)
    ranks = betas.rank(method='first')
    quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    pctl = (ranks - 1) / (len(betas) - 1) * 100.0
    for i, r in enumerate(results):
        r['pctl_rank'] = round(float(pctl.iloc[i]), 2)
        r['quintile'] = int(quint.iloc[i])

    # Show quintile distribution
    from collections import Counter
    q_dist = Counter(r['quintile'] for r in results)
    print(f"  Quintile distribution: {dict(sorted(q_dist.items()))}")

    # Show beta range
    all_betas = [r['eloundou_beta'] for r in results]
    print(f"  Beta range: {min(all_betas):.3f} - {max(all_betas):.3f}")

    # Save
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'styrk08', 'eloundou_beta', 'pctl_rank', 'quintile',
            'n_soc_matched', 'has_partial_match', 'max_partial_fanout', 'manual_map',
        ])
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: r['styrk08']))

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    build_mapping()
