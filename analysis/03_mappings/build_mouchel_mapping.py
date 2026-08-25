"""
Build Mouchel, Bouquet & Sheffi (2026) evidence-grounded AI exposure mapping
to STYRK-08.

Chain: O*NET-SOC 2018 -> SOC 2018 -> SOC 2010 -> ISCO-08 -> STYRK-08
(identical to build_eloundou_mapping.py; the last step is a filtered code
match against the official STYRK-08 list, see that script's docstring).

The measure updates the Eloundou et al. (2024) task rubric to the 2026
agentic-AI frontier (E0/E1/E2 plus a new vision-dependent E3 class) and
grounds the task labels in retrieved news/academic evidence instead of a
single frontier model's priors. Two arms are carried:

  - mouchel_grounded:   arm A1, the unweighted grounded ensemble mean.
                        Never touches Anthropic usage data, so it is the
                        theoretical-exposure arm comparable to Eloundou beta.
  - mouchel_calibrated: arm S0, the headline index calibrated against
                        Anthropic Economic Index task penetration. NOT
                        independent of the revealed-usage measures (Handa,
                        Anthropic 2026) -- use only where that is acceptable.

Quintiles (equal-occupation, pd.qcut on first-occurrence ranks, ties broken
by styrk08 sort order) are assigned on the grounded arm; the calibrated arm
gets its own quintile column for robustness use.

Data source:
- mouchel/calibrated_occupation_exposure_2026-07-20.csv: occupation-level
  scores, 2026-07-20 vintage, downloaded from
  https://raw.githubusercontent.com/MIT-Work-Analytics-Laboratory/RAG-Exposure/main/results/calibrated/2026-07-20/calibrated_occupation_exposure.csv
  (paper: arXiv:2605.15474; also released as HF dataset
  MIT-WAL/evidence-grounded-ai-exposure)

Crosswalk sources: same BLS files as build_eloundou_mapping.py.
"""

import csv                                   # plain CSV reading/writing
from pathlib import Path                     # filesystem-path handling
from collections import defaultdict, Counter  # accumulation + quintile tally

import openpyxl                              # reads the .xlsx SOC 2010<->2018 crosswalk
import xlrd                                  # reads the legacy .xls SOC<->ISCO crosswalk
import pandas as pd                          # only used for the qcut quintile rule

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root (3 levels up)
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'              # exposure-data folder

MOUCHEL_FILE = DATA_DIR / 'mouchel' / 'calibrated_occupation_exposure_2026-07-20.csv'  # source scores
SOC_2010_2018_FILE = DATA_DIR / 'soc_2010_to_2018_crosswalk.xlsx'  # BLS SOC 2010<->2018
SOC_ISCO_FILE = DATA_DIR / 'isco_soc_crosswalk.xls'                # BLS SOC 2010<->ISCO-08
STYRK08_FILE = DATA_DIR / 'styrk08_codes.csv'                      # official STYRK-08 list
OUTPUT_FILE = DATA_DIR / 'styrk08_mouchel_mapping.csv'             # output mapping

# The two score columns we carry, keyed by their output names.
SCORE_COLS = {
    'mouchel_grounded': 'simple_avg_exposure',    # arm A1: grounded ensemble mean
    'mouchel_calibrated': 'calibrated_exposure',  # arm S0: calibrated headline index
}

# Manual mappings for large Norwegian STYRK codes without SOC equivalent
# (same as build_eloundou_mapping.py).
MANUAL_STYRK_MAP = {
    '2223': '2221',  # Sykepleiere -> Nursing professionals
    '2224': '2221',  # Vernepleiere -> Nursing professionals
}

# Manual corrections for Norwegian STYRK adaptations where the same 4-digit
# BLS/ISCO code denotes a different occupation than the Norwegian STYRK code
# (same as build_eloundou_mapping.py).
MANUAL_STYRK_SOC_MAP = {
    '2267': ['29-1122'],  # Ergoterapeuter -> Occupational Therapists
    '2269': ['29-1011'],  # Kiropraktorer mv. -> Chiropractors
}


def load_mouchel() -> dict[str, dict[str, float]]:
    """Load Mouchel scores keyed by 6-digit SOC 2018 code.

    O*NET detail codes (11-1011.00, 11-1011.03, ...) are averaged within
    their parent SOC 2018 code, exactly as in load_eloundou()."""
    # Collect one list per (SOC code, output measure) before averaging.
    raw: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Open the downloaded occupation-level file.
    with open(MOUCHEL_FILE, encoding='utf-8') as f:
        # Iterate over the 923 O*NET occupation rows.
        for row in csv.DictReader(f):
            # O*NET codes like '11-1011.03' -> SOC 2018 '11-1011'.
            soc6 = row['onet_soc_code'].split('.')[0]
            # Append each carried score to its per-SOC accumulator.
            for out_name, src_col in SCORE_COLS.items():
                raw[soc6][out_name].append(float(row[src_col]))
    # Average across O*NET detail codes within the same SOC 2018 code.
    return {soc: {name: sum(vals) / len(vals) for name, vals in cols.items()}
            for soc, cols in raw.items()}


def load_soc_2018_to_2010() -> dict[str, list[str]]:
    """Load SOC 2018 -> SOC 2010 mapping (reverse of the BLS file)."""
    # Open the BLS crosswalk workbook and take its active sheet.
    wb = openpyxl.load_workbook(str(SOC_2010_2018_FILE))
    ws = wb.active
    # One SOC 2018 code can map back to several SOC 2010 codes.
    mapping: dict[str, list[str]] = defaultdict(list)
    # Data rows start at row 10 (same layout as in build_eloundou_mapping.py).
    for row in ws.iter_rows(min_row=10, values_only=True):
        # Column 0 holds SOC 2010, column 2 holds SOC 2018.
        soc2010 = str(row[0]).strip() if row[0] else ''
        soc2018 = str(row[2]).strip() if row[2] else ''
        # Keep only real code pairs (a dash marks a valid SOC code).
        if soc2010 and soc2018 and '-' in soc2010:
            mapping[soc2018].append(soc2010)
    # Freeze the defaultdict into a plain dict.
    return dict(mapping)


def load_soc2010_to_isco08():
    """Load SOC 2010 -> ISCO-08 mapping with partial match flags."""
    # Open the legacy .xls crosswalk and its SOC-to-ISCO sheet.
    wb = xlrd.open_workbook(str(SOC_ISCO_FILE))
    ws = wb.sheet_by_name('2010 SOC to ISCO-08')
    # One SOC 2010 code can map to several ISCO-08 codes.
    mapping: dict[str, list[str]] = defaultdict(list)
    # Track which (SOC, ISCO) links BLS marks as partial ('*').
    partial: dict[tuple[str, str], bool] = {}
    # Data rows start at row 7 (same layout as in build_eloundou_mapping.py).
    for i in range(7, ws.nrows):
        # Column 0: SOC 2010 code; column 2: partial flag; column 3: ISCO-08.
        soc2010 = str(ws.cell_value(i, 0)).strip()
        part_flag = str(ws.cell_value(i, 2)).strip()
        isco08 = str(ws.cell_value(i, 3)).strip()
        # Keep only real code pairs.
        if soc2010 and isco08 and '-' in soc2010:
            # Excel sometimes renders the ISCO code as a float ('1234.0').
            if '.' in isco08:
                isco08 = isco08.split('.')[0]
            # Left-pad to 4 digits so leading-zero codes survive.
            isco08 = isco08.zfill(4)
            # Record the link and whether it is a partial match.
            mapping[soc2010].append(isco08)
            partial[(soc2010, isco08)] = (part_flag == '*')
    # Freeze the defaultdict into a plain dict.
    return dict(mapping), partial


def load_styrk08_codes() -> set[str]:
    """Load valid STYRK-08 4-digit codes."""
    # Collect the official 4-digit codes into a set for fast membership tests.
    codes = set()
    # The SSB code list is latin-1 encoded.
    with open(STYRK08_FILE, encoding='latin-1') as f:
        for row in csv.DictReader(f):
            # The code column is named 'styrk08' or 'code' depending on export.
            code = row.get('styrk08', row.get('code', ''))
            # Only 4-digit (level 4) codes belong in the mapping.
            if len(code) == 4:
                codes.add(code)
    return codes


def build_mapping():
    # ---- Load all inputs -------------------------------------------------
    print("Loading Mouchel et al. (2026) evidence-grounded exposure scores...")
    mouchel = load_mouchel()
    print(f"  {len(mouchel)} unique SOC 2018 codes with scores")

    print("Loading SOC 2018 -> SOC 2010 crosswalk...")
    soc18_to_10 = load_soc_2018_to_2010()
    print(f"  {len(soc18_to_10)} SOC 2018 codes mapped")

    print("Loading SOC 2010 -> ISCO-08 crosswalk...")
    soc10_to_isco, partial_flags = load_soc2010_to_isco08()
    print(f"  {len(soc10_to_isco)} SOC 2010 codes mapped to ISCO-08")

    print("Loading STYRK-08 codes...")
    styrk_codes = load_styrk08_codes()
    print(f"  {len(styrk_codes)} valid STYRK-08 codes")

    # ---- Step 1: SOC 2018 scores -> SOC 2010 -----------------------------
    # Accumulate, per SOC 2010 code, one score list per carried measure.
    soc2010_scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    # Count SOC 2018 codes that the BLS crosswalk cannot place.
    unmapped_18 = 0
    for soc18, scores in mouchel.items():
        if soc18 in soc18_to_10:
            # A 2018 code fans out to every 2010 code it maps back to.
            for soc10 in soc18_to_10[soc18]:
                for name, val in scores.items():
                    soc2010_scores[soc10][name].append(val)
        else:
            unmapped_18 += 1
    print(f"\n  SOC 2018 -> 2010: {len(soc2010_scores)} SOC 2010 codes, "
          f"{unmapped_18} SOC 2018 codes unmapped")

    # ---- Step 2: SOC 2010 -> ISCO-08 -------------------------------------
    # Collect per-ISCO contribution records (one per contributing SOC code).
    isco_contributions: dict[str, list[dict]] = defaultdict(list)
    # Count SOC 2010 codes that the SOC->ISCO crosswalk cannot place.
    unmapped_10 = 0
    for soc10, score_lists in soc2010_scores.items():
        # Average each measure across the SOC 2018 sources feeding this code.
        avg = {name: sum(vals) / len(vals) for name, vals in score_lists.items()}
        if soc10 in soc10_to_isco:
            # How many ISCO codes this SOC code fans out to (partial-match QC).
            fan_out = len(soc10_to_isco[soc10])
            for isco in soc10_to_isco[soc10]:
                # Was this specific SOC->ISCO link flagged partial by BLS?
                is_partial = partial_flags.get((soc10, isco), False)
                # Record the contribution with its quality metadata.
                isco_contributions[isco].append({
                    'scores': avg,
                    'soc': soc10,
                    'partial': is_partial,
                    'fan_out': fan_out if is_partial else 1,
                })
        else:
            unmapped_10 += 1
    print(f"  SOC 2010 -> ISCO-08: {len(isco_contributions)} ISCO-08 codes, "
          f"{unmapped_10} SOC 2010 codes unmapped")

    # ---- Step 3: filter to valid STYRK-08 codes and average --------------
    results = []
    for isco, contribs in sorted(isco_contributions.items()):
        # Drop ISCO codes that do not exist in the Norwegian STYRK-08 list.
        if isco not in styrk_codes:
            continue
        # Start the output row with the code itself.
        row = {'styrk08': isco}
        # Average each carried measure over all contributing SOC codes.
        for name in SCORE_COLS:
            row[name] = round(sum(c['scores'][name] for c in contribs) / len(contribs), 6)
        # Attach the same quality flags as the Eloundou mapping.
        row['n_soc_matched'] = len(contribs)
        row['has_partial_match'] = 1 if any(c['partial'] for c in contribs) else 0
        row['max_partial_fanout'] = max((c['fan_out'] for c in contribs if c['partial']), default=0)
        row['manual_map'] = ''
        results.append(row)

    # ---- Manual SOC overrides (Norway-specific code collisions) ----------
    # Drop the misleading same-code STYRK/ISCO matches before re-adding them
    # from their correct direct SOC sources.
    manual_targets = set(MANUAL_STYRK_SOC_MAP)
    results = [r for r in results if r['styrk08'] not in manual_targets]
    for styrk_target, soc_sources in MANUAL_STYRK_SOC_MAP.items():
        # Skip if the target is not a valid STYRK-08 code at all.
        if styrk_target not in styrk_codes:
            continue
        # Gather the scores of the manually chosen SOC 2010 sources.
        per_measure: dict[str, list[float]] = defaultdict(list)
        used_socs = []
        for soc in soc_sources:
            lists = soc2010_scores.get(soc)
            # Skip sources with no score (should not happen with full coverage).
            if not lists:
                continue
            # Average each measure within this source SOC code.
            for name, vals in lists.items():
                per_measure[name].append(sum(vals) / len(vals))
            used_socs.append(soc)
        # If no source had scores, report and leave the code unmapped.
        if not used_socs:
            print(f"  Manual SOC map skipped: {styrk_target} has no source scores")
            continue
        # Build the override row (clean full match, provenance in manual_map).
        row = {'styrk08': styrk_target}
        for name in SCORE_COLS:
            row[name] = round(sum(per_measure[name]) / len(per_measure[name]), 6)
        row['n_soc_matched'] = len(used_socs)
        row['has_partial_match'] = 0
        row['max_partial_fanout'] = 0
        row['manual_map'] = 'SOC:' + ';'.join(used_socs)
        results.append(row)
        print(f"  Manual SOC map: {styrk_target} <- {';'.join(used_socs)}")

    # ---- Manual STYRK-to-STYRK copies (nurses etc.) ----------------------
    # Codes already mapped stay untouched; only fill genuine gaps.
    mapped_codes = {r['styrk08'] for r in results}
    for styrk_target, styrk_source in MANUAL_STYRK_MAP.items():
        if styrk_target in mapped_codes:
            continue
        if styrk_target not in styrk_codes:
            continue
        # Copy the source row and mark its provenance.
        source_row = next((r for r in results if r['styrk08'] == styrk_source), None)
        if source_row:
            manual = dict(source_row)
            manual['styrk08'] = styrk_target
            manual['manual_map'] = styrk_source
            results.append(manual)
            print(f"  Manual map: {styrk_target} <- {styrk_source}")

    # Deterministic order before quintile assignment (ties break by code).
    results.sort(key=lambda r: r['styrk08'])

    print(f"\n  Final: {len(results)} STYRK-08 codes with Mouchel scores")
    print(f"  Coverage: {len(results)}/{len(styrk_codes)} "
          f"({100*len(results)/len(styrk_codes):.1f}%)")

    # Quality summary: how many codes carry a partial SOC->ISCO link.
    n_partial = sum(1 for r in results if r['has_partial_match'])
    print(f"  With partial SOC->ISCO match: {n_partial}")

    # ---- Quintiles (same rule as build_eloundou_mapping.py) --------------
    # Equal-frequency quintiles per measure: pd.qcut on first-occurrence
    # ranks gives five equal-sized groups; pctl_rank is reported for the
    # grounded (A1) arm, which is the headline measure of this mapping.
    for name, q_col in [('mouchel_grounded', 'quintile'),
                        ('mouchel_calibrated', 'quintile_calibrated')]:
        # Pull the measure into a Series aligned with the sorted results.
        vals = pd.Series([r[name] for r in results], dtype=float)
        # Rank with method='first' so ties break by styrk08 sort order.
        ranks = vals.rank(method='first')
        # Cut the ranks into five equal groups labelled 1 (low) to 5 (high).
        quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
        # Store the quintile on each result row.
        for i, r in enumerate(results):
            r[q_col] = int(quint.iloc[i])
        # Percentile rank (0-100) only for the grounded headline arm.
        if name == 'mouchel_grounded':
            pctl = (ranks - 1) / (len(vals) - 1) * 100.0
            for i, r in enumerate(results):
                r['pctl_rank'] = round(float(pctl.iloc[i]), 2)

    # Show the grounded-arm quintile distribution as a sanity check.
    q_dist = Counter(r['quintile'] for r in results)
    print(f"  Quintile distribution (grounded): {dict(sorted(q_dist.items()))}")

    # Show each measure's range as a sanity check.
    for name in SCORE_COLS:
        vals = [r[name] for r in results]
        print(f"  {name} range: {min(vals):.3f} - {max(vals):.3f}")

    # ---- Save ------------------------------------------------------------
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        # Fixed column order: code, scores, ranks, then quality flags.
        writer = csv.DictWriter(f, fieldnames=[
            'styrk08', 'mouchel_grounded', 'mouchel_calibrated',
            'pctl_rank', 'quintile', 'quintile_calibrated',
            'n_soc_matched', 'has_partial_match', 'max_partial_fanout', 'manual_map',
        ])
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: r['styrk08']))

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    build_mapping()
