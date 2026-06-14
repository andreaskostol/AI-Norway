"""
Build Eloundou et al. (2024) GPT-4 beta exposure mapping to STYRK-08.

Chain: O*NET-SOC 2018 -> SOC 2010 -> ISCO-08 -> STYRK-08

Since STYRK-08 = ISCO-08 at the 4-digit level (SSB Notater 17/2011),
the last step is a direct identity mapping.

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

    # Step 2: SOC 2010 -> ISCO-08 (= STYRK-08)
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

    # Assign percentile ranks and quintiles
    betas_sorted = sorted(r['eloundou_beta'] for r in results)
    n = len(betas_sorted)
    for r in results:
        rank = sum(1 for b in betas_sorted if b < r['eloundou_beta'])
        pctl = 100 * rank / n
        r['pctl_rank'] = round(pctl, 2)
        if pctl <= 20:
            r['quintile'] = 1
        elif pctl <= 40:
            r['quintile'] = 2
        elif pctl <= 60:
            r['quintile'] = 3
        elif pctl <= 80:
            r['quintile'] = 4
        else:
            r['quintile'] = 5

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
