"""
Build Microsoft (Tomlinson et al. 2025) AI applicability mapping to STYRK-08.

Chain: SOC 2018 -> SOC 2010 -> ISCO-08 -> STYRK-08, reusing the exact
loaders and manual maps from build_eloundou_mapping.py so this measure
lands on the same crosswalk footing as the existing ones. The source is
already keyed by detailed SOC 2018 codes (no O*NET suffixes to strip).

The measure is a revealed-usage measure: 200k de-identified Bing Copilot
conversations (US, Jan-Sep 2024) scored against O*NET intermediate work
activities. Three scores are carried:

  - microsoft_applicability: the headline AI applicability score
    (average of the user-goal and AI-action sides; v1.1 uses nonphysical
    task weights on the AI-action side). Range roughly 0-0.5.
  - microsoft_user:   the user-goal side alone (AI assists the user's
                      own work goal -- augmentation-flavored).
  - microsoft_action: the AI-action side alone (AI performs the work
                      activity -- automation-flavored, nonphysical
                      weights).

Quintiles (equal-occupation, same qcut rule as the other mappings) are
assigned on the headline score. Coverage is somewhat below Eloundou's:
the release covers 785 detailed SOC codes (no military, and 74 civilian
codes without O*NET task data are absent).

Data source:
- microsoft/ai_applicability_scores.csv and microsoft/soc_metrics.csv,
  official release v1.1 (2025-12-22, matches arXiv:2507.07935v6),
  downloaded from github.com/microsoft/working-with-ai at pinned commit
  c94a07c52f (see microsoft/DOWNLOAD_INFO.txt). License CC BY 4.0.

Crosswalk sources: same BLS files as build_eloundou_mapping.py.
"""

import csv                                   # plain CSV reading/writing
from pathlib import Path                     # filesystem-path handling
from collections import defaultdict, Counter  # accumulation + quintile tally

import pandas as pd                          # only used for the qcut quintile rule

# Shared crosswalk loaders and Norway-specific manual maps.
from build_eloundou_mapping import (
    load_soc_2018_to_2010,
    load_soc2010_to_isco08,
    load_styrk08_codes,
    MANUAL_STYRK_MAP,
    MANUAL_STYRK_SOC_MAP,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # repo root (3 levels up)
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'              # exposure-data folder

MS_SCORES_FILE = DATA_DIR / 'microsoft' / 'ai_applicability_scores.csv'  # headline score
MS_METRICS_FILE = DATA_DIR / 'microsoft' / 'soc_metrics.csv'             # per-side components
OUTPUT_FILE = DATA_DIR / 'styrk08_microsoft_mapping.csv'                 # output mapping

# The three score columns we carry, keyed by their output names.
SCORE_COLS = {
    'microsoft_applicability': 'ai_applicability_score',        # headline
    'microsoft_user': 'ai_applicability_score_user',            # user-goal side
    'microsoft_action': 'ai_applicability_score_ai_nonphysical',  # AI-action side
}


def load_microsoft() -> dict[str, dict[str, float]]:
    """Load Microsoft scores keyed by 6-digit SOC 2018 code.

    The headline score lives in ai_applicability_scores.csv and the two
    per-side scores in soc_metrics.csv; both files carry the same 785
    detailed SOC 2018 codes."""
    scores: dict[str, dict[str, float]] = defaultdict(dict)
    # Headline score file: SOC Code, title, ai_applicability_score.
    with open(MS_SCORES_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            soc6 = row['SOC Code'].strip()
            scores[soc6]['microsoft_applicability'] = float(row['ai_applicability_score'])
    # Component file: user-goal and AI-action sides per SOC code.
    with open(MS_METRICS_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            soc6 = row['SOC Code'].strip()
            scores[soc6]['microsoft_user'] = float(row['ai_applicability_score_user'])
            scores[soc6]['microsoft_action'] = float(row['ai_applicability_score_ai_nonphysical'])
    # Every code must carry all three scores (both files cover the same set).
    assert all(len(v) == 3 for v in scores.values()), \
        'SOC code missing from one of the Microsoft files'
    return dict(scores)


def build_mapping():
    # ---- Load all inputs -------------------------------------------------
    print("Loading Microsoft (Tomlinson et al. 2025) AI applicability scores...")
    ms = load_microsoft()
    print(f"  {len(ms)} unique SOC 2018 codes with scores")

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
    for soc18, scores in ms.items():
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
        # Attach the same quality flags as the other mappings.
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
            # Skip sources with no score (74 civilian SOC codes lack data).
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

    print(f"\n  Final: {len(results)} STYRK-08 codes with Microsoft scores")
    print(f"  Coverage: {len(results)}/{len(styrk_codes)} "
          f"({100*len(results)/len(styrk_codes):.1f}%)")

    # Quality summary: how many codes carry a partial SOC->ISCO link.
    n_partial = sum(1 for r in results if r['has_partial_match'])
    print(f"  With partial SOC->ISCO match: {n_partial}")

    # ---- Quintiles (same rule as build_eloundou_mapping.py) --------------
    # Equal-frequency quintiles on the headline score: pd.qcut on
    # first-occurrence ranks gives five equal-sized groups.
    vals = pd.Series([r['microsoft_applicability'] for r in results], dtype=float)
    # Rank with method='first' so ties break by styrk08 sort order.
    ranks = vals.rank(method='first')
    # Cut the ranks into five equal groups labelled 1 (low) to 5 (high).
    quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    # Percentile rank (0-100) for the headline score.
    pctl = (ranks - 1) / (len(vals) - 1) * 100.0
    for i, r in enumerate(results):
        r['quintile'] = int(quint.iloc[i])
        r['pctl_rank'] = round(float(pctl.iloc[i]), 2)

    # Show the quintile distribution as a sanity check.
    q_dist = Counter(r['quintile'] for r in results)
    print(f"  Quintile distribution (headline): {dict(sorted(q_dist.items()))}")

    # Show each measure's range as a sanity check.
    for name in SCORE_COLS:
        vals = [r[name] for r in results]
        print(f"  {name} range: {min(vals):.3f} - {max(vals):.3f}")

    # ---- Save ------------------------------------------------------------
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        # Fixed column order: code, scores, ranks, then quality flags.
        writer = csv.DictWriter(f, fieldnames=[
            'styrk08', 'microsoft_applicability', 'microsoft_user',
            'microsoft_action', 'pctl_rank', 'quintile',
            'n_soc_matched', 'has_partial_match', 'max_partial_fanout', 'manual_map',
        ])
        writer.writeheader()
        writer.writerows(sorted(results, key=lambda r: r['styrk08']))

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    build_mapping()
