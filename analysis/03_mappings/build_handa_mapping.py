"""
Build Handa et al. (2025) AI exposure mapping to STYRK-08.

Produces three occupation-level measures:
  - overall_exposure: share of Claude conversations involving the occupation's tasks
  - automation_share: fraction of those conversations that are automative (directive)
  - augmentation_share: fraction that are augmentative (feedback_loop + task_iteration +
    validation + learning)

Chain: O*NET tasks → SOC 2010 → ISCO-08 → STYRK-08
(O*NET task statements already use SOC 2010 codes.)

Quality flags per STYRK-08 code:
  - n_soc_matched: number of SOC 2010 codes contributing scores
  - n_tasks_matched: O*NET tasks with nonzero task_pct match
  - n_tasks_total: total O*NET tasks for the contributing SOC codes
  - task_coverage: n_tasks_matched / n_tasks_total
  - partial_match: 1 if any contributing SOC→ISCO link is partial (*) in BLS crosswalk

Data sources:
  - Handa et al. (2025) via Anthropic/EconomicIndex on Hugging Face (release_2025_03_27)
  - BLS SOC 2010 → ISCO-08 crosswalk (August 2012, updated June 2015)
"""

import csv
from pathlib import Path
from collections import defaultdict

import xlrd
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'
HANDA_DIR = DATA_DIR / 'handa'

TASK_PCT_FILE = HANDA_DIR / 'task_pct_v2.csv'
AVA_FILE = HANDA_DIR / 'automation_vs_augmentation_by_task.csv'
ONET_FILE = HANDA_DIR / 'onet_task_statements.csv'

SOC_ISCO_FILE = DATA_DIR / 'isco_soc_crosswalk.xls'
STYRK08_FILE = DATA_DIR / 'styrk08_codes.csv'

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

OUTPUT_FILE = DATA_DIR / 'styrk08_handa_mapping.csv'


def load_task_pct() -> dict[str, float]:
    with open(TASK_PCT_FILE, encoding='utf-8') as f:
        return {row['task_name']: float(row['pct']) for row in csv.DictReader(f)}


def load_ava() -> dict[str, dict[str, float]]:
    result = {}
    with open(AVA_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            result[row['task_name']] = {
                'directive': float(row['directive']),
                'feedback_loop': float(row['feedback_loop']),
                'task_iteration': float(row['task_iteration']),
                'validation': float(row['validation']),
                'learning': float(row['learning']),
                'filtered': float(row['filtered']),
            }
    return result


def load_onet_task_to_soc() -> dict[str, list[str]]:
    """Map lowercase task text -> list of 6-digit SOC 2010 codes."""
    mapping: dict[str, list[str]] = defaultdict(list)
    with open(ONET_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            task_key = row['Task'].lower().strip()
            soc = row['O*NET-SOC Code'].split('.')[0]
            if soc not in mapping[task_key]:
                mapping[task_key].append(soc)
    return dict(mapping)


def load_onet_tasks_per_soc() -> dict[str, set[str]]:
    """Map SOC 2010 code -> set of lowercase task texts."""
    mapping: dict[str, set[str]] = defaultdict(set)
    with open(ONET_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            soc = row['O*NET-SOC Code'].split('.')[0]
            mapping[soc].add(row['Task'].lower().strip())
    return dict(mapping)


def load_soc2010_to_isco08():
    """Load SOC 2010 → ISCO-08 crosswalk with partial match flags.
    Returns: (mapping dict, partial_flags dict)
      mapping: {soc: [isco, ...]}
      partial_flags: {(soc, isco): bool}  True if partial match (*)
    """
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
    codes = set()
    with open(STYRK08_FILE, encoding='latin-1') as f:
        for row in csv.DictReader(f):
            code = row.get('styrk08', row.get('code', ''))
            if len(code) == 4:
                codes.add(code)
    return codes


def main():
    print("Loading Handa et al. task-level data...")
    task_pct = load_task_pct()
    ava = load_ava()
    onet_task_to_soc = load_onet_task_to_soc()
    onet_tasks_per_soc = load_onet_tasks_per_soc()
    task_pct_keys = {k.lower().strip() for k in task_pct}
    print(f"  {len(task_pct)} tasks with pct, {len(ava)} tasks with ava")

    # Step 1: Aggregate tasks to SOC 2010 level
    soc10_exposure: dict[str, float] = defaultdict(float)
    soc10_auto_wt: dict[str, float] = defaultdict(float)
    soc10_augm_wt: dict[str, float] = defaultdict(float)
    soc10_classifiable_wt: dict[str, float] = defaultdict(float)

    matched = 0
    for task_name, pct in task_pct.items():
        task_key = task_name.lower().strip()
        soc_codes = onet_task_to_soc.get(task_key)
        if not soc_codes:
            continue
        matched += 1

        task_ava = ava.get(task_name)
        if not task_ava:
            continue

        auto = task_ava['directive']
        augm = (task_ava['feedback_loop'] + task_ava['task_iteration'] +
                task_ava['validation'] + task_ava['learning'])
        classifiable = 1.0 - task_ava['filtered']

        n_soc = len(soc_codes)
        for soc in soc_codes:
            soc10_exposure[soc] += pct / n_soc
            soc10_auto_wt[soc] += pct * auto / n_soc
            soc10_augm_wt[soc] += pct * augm / n_soc
            soc10_classifiable_wt[soc] += pct * classifiable / n_soc

    print(f"  {matched} tasks matched to O*NET SOC 2010 codes")
    print(f"  {len(soc10_exposure)} unique SOC 2010 codes")

    # Compute scores + task coverage per SOC 2010
    soc10_scores: dict[str, dict] = {}
    for soc in soc10_exposure:
        exp = soc10_exposure[soc]
        cls_wt = soc10_classifiable_wt[soc]
        auto_sh = soc10_auto_wt[soc] / cls_wt if cls_wt > 0 else 0
        augm_sh = soc10_augm_wt[soc] / cls_wt if cls_wt > 0 else 0
        all_tasks = onet_tasks_per_soc.get(soc, set())
        matched_tasks = sum(1 for t in all_tasks if t in task_pct_keys)
        soc10_scores[soc] = {
            'overall_exposure': exp,
            'automation_share': auto_sh,
            'augmentation_share': augm_sh,
            'n_tasks_matched': matched_tasks,
            'n_tasks_total': len(all_tasks),
        }

    # Step 2: SOC 2010 -> ISCO-08 (then filtered to valid STYRK-08 codes)
    print("\nLoading crosswalks...")
    soc10_to_isco, partial_flags = load_soc2010_to_isco08()
    styrk_codes = load_styrk08_codes()

    # Track which SOCs contribute to each ISCO, with quality info
    isco_contributions: dict[str, list[dict]] = defaultdict(list)
    unmapped_10 = 0
    for soc10, scores in soc10_scores.items():
        if soc10 in soc10_to_isco:
            fan_out = len(soc10_to_isco[soc10])
            for isco in soc10_to_isco[soc10]:
                is_partial = partial_flags.get((soc10, isco), False)
                contrib = dict(scores)
                contrib['soc'] = soc10
                contrib['partial'] = is_partial
                contrib['fan_out'] = fan_out if is_partial else 1
                isco_contributions[isco].append(contrib)
        else:
            unmapped_10 += 1
    print(f"  SOC 2010 -> ISCO-08: {len(isco_contributions)} codes, {unmapped_10} unmapped")

    # Step 3: Filter to valid STYRK-08 and compute final scores + quality flags
    results = []
    for isco in sorted(isco_contributions):
        if isco not in styrk_codes:
            continue
        contribs = isco_contributions[isco]
        n = len(contribs)
        results.append({
            'styrk08': isco,
            'overall_exposure': sum(c['overall_exposure'] for c in contribs) / n,
            'automation_share': sum(c['automation_share'] for c in contribs) / n,
            'augmentation_share': sum(c['augmentation_share'] for c in contribs) / n,
            'n_soc_matched': n,
            'n_tasks_matched': sum(c['n_tasks_matched'] for c in contribs),
            'n_tasks_total': sum(c['n_tasks_total'] for c in contribs),
            'task_coverage': (sum(c['n_tasks_matched'] for c in contribs) /
                              max(1, sum(c['n_tasks_total'] for c in contribs))),
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
        contribs = []
        for soc in soc_sources:
            scores = soc10_scores.get(soc)
            if not scores:
                continue
            contrib = dict(scores)
            contrib['soc'] = soc
            contribs.append(contrib)
        if not contribs:
            print(f"  Manual SOC map skipped: {styrk_target} has no source scores")
            continue
        n = len(contribs)
        results.append({
            'styrk08': styrk_target,
            'overall_exposure': sum(c['overall_exposure'] for c in contribs) / n,
            'automation_share': sum(c['automation_share'] for c in contribs) / n,
            'augmentation_share': sum(c['augmentation_share'] for c in contribs) / n,
            'n_soc_matched': n,
            'n_tasks_matched': sum(c['n_tasks_matched'] for c in contribs),
            'n_tasks_total': sum(c['n_tasks_total'] for c in contribs),
            'task_coverage': (sum(c['n_tasks_matched'] for c in contribs) /
                              max(1, sum(c['n_tasks_total'] for c in contribs))),
            'has_partial_match': 0,
            'max_partial_fanout': 0,
            'manual_map': 'SOC:' + ';'.join(c['soc'] for c in contribs),
        })
        print(f"  Manual SOC map: {styrk_target} <- "
              f"{';'.join(c['soc'] for c in contribs)}")

    # Apply manual mappings for unmapped Norwegian STYRK codes
    mapped_codes = {r['styrk08'] for r in results}
    for styrk_target, styrk_source in MANUAL_STYRK_MAP.items():
        if styrk_target in mapped_codes:
            continue
        if styrk_target not in styrk_codes:
            continue
        # Find the source code's scores
        source_row = next((r for r in results if r['styrk08'] == styrk_source), None)
        if source_row:
            manual = dict(source_row)
            manual['styrk08'] = styrk_target
            manual['manual_map'] = styrk_source
            results.append(manual)
            print(f"  Manual map: {styrk_target} <- {styrk_source}")

    results.sort(key=lambda x: x['styrk08'])

    print(f"\n  Final: {len(results)} STYRK-08 codes with Handa scores")
    print(f"  Coverage: {len(results)}/{len(styrk_codes)} "
          f"({100 * len(results) / len(styrk_codes):.1f}%)")

    # Quality summary
    n_partial = sum(1 for r in results if r['has_partial_match'])
    n_low_cov = sum(1 for r in results if r['task_coverage'] < 0.1)
    print(f"  With partial SOC->ISCO match: {n_partial}")
    print(f"  With <10% task coverage: {n_low_cov}")

    # Assign equal-frequency quintiles (each occupation counts once) for each
    # measure. This is identical to the dashboard's rule in
    # analysis/06_figures/plot_canaries_style_usage.py, so the paper and the
    # companion dashboard bin occupations the same way: pd.qcut on the
    # first-occurrence rank gives five equal-sized groups (~70 codes each), and
    # pctl is the matching rank percentile (0-100). The earlier
    # strict-less / pctl<=80 rule produced unequal groups and split borderline
    # codes (e.g. STYRK 7115, automation_share 0.39474, exactly on the Q4/Q5
    # cut) onto the opposite side from the dashboard.
    for measure in ['overall_exposure', 'automation_share', 'augmentation_share']:
        vals = pd.Series([r[measure] for r in results], dtype=float)
        ranks = vals.rank(method='first')
        quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
        pctl = (ranks - 1) / (len(vals) - 1) * 100.0
        for i, r in enumerate(results):
            r[f'pctl_{measure}'] = round(float(pctl.iloc[i]), 2)
            r[f'q_{measure}'] = int(quint.iloc[i])

    # Show distributions
    from collections import Counter
    for measure in ['overall_exposure', 'automation_share', 'augmentation_share']:
        q_dist = Counter(r[f'q_{measure}'] for r in results)
        vals = [r[measure] for r in results]
        print(f"\n  {measure}:")
        print(f"    range: {min(vals):.6f} - {max(vals):.6f}")
        print(f"    quintiles: {dict(sorted(q_dist.items()))}")

    # Save
    fieldnames = [
        'styrk08',
        'overall_exposure', 'pctl_overall_exposure', 'q_overall_exposure',
        'automation_share', 'pctl_automation_share', 'q_automation_share',
        'augmentation_share', 'pctl_augmentation_share', 'q_augmentation_share',
        'n_soc_matched', 'n_tasks_matched', 'n_tasks_total', 'task_coverage',
        'has_partial_match', 'max_partial_fanout', 'manual_map',
    ]
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            out = {k: r[k] for k in fieldnames}
            for m in ['overall_exposure', 'automation_share', 'augmentation_share']:
                out[m] = round(r[m], 8)
            out['task_coverage'] = round(r['task_coverage'], 4)
            writer.writerows([out])

    print(f"\nSaved to {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
