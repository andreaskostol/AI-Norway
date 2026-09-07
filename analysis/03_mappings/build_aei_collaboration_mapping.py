"""
Automation vs. augmentation per STYRK-08 occupation from the newer Anthropic
Economic Index releases (Nov 2025, Feb 2026, and Aug 2025 if extracted).

The original Handa et al. (2025) mapping (build_handa_mapping.py) uses the
March 2025 release, which covered Claude.ai conversations from Dec 2024 to
Jan 2025. Anthropic has since published the same task x interaction-type
table three more times, at the O*NET task level and for both Claude.ai and
the first-party API. This script walks those tables through the same
chain as the Handa mapping (O*NET task -> SOC 2010 -> ISCO-08 -> STYRK-08),
so the occupation panel on kiindeksen.no can show how each occupation's
automation share has moved, and what the API (agentic, enterprise) side
looks like.

Interaction types (Anthropic's five-way classifier), bucketed the way
Anthropic buckets them in every Economic Index report:
  directive, feedback loop       -> automation
  task iteration, validation,
  learning                       -> augmentation
  not_classified, none           -> dropped from the denominator
NB: build_handa_mapping.py (and hence styrk08_handa_mapping.csv, the
dashboard's usage groups and the paper text) counts directive ONLY as
automation. Both conventions are kept here: automation_share follows
Anthropic, directive_share is the directive-only variant.

The original Handa vintage (release_2025_03_27, Claude.ai conversations
Dec 2024 to Jan 2025) is included as date 2024-12-01 so the site can show
all four points in time. It is rebuilt from the task-level shares with
usage-weighted pseudo-counts, which reproduces the Handa mapping's
weighting exactly; its conversation counts are unknown and left blank.

Inputs (written by extract_aei_release_slices.py):
  data/ai_exposure/handa/aei_releases/onet_task_collaboration_{platform}_{date}.csv
  data/ai_exposure/handa/aei_releases/onet_task_{platform}_{date}.csv

Outputs:
  data/ai_exposure/styrk08_aei_collaboration.csv   one row per STYRK x platform x date
  data/ai_exposure/styrk08_aei_tasks.csv           top tasks per STYRK, latest date per platform
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_handa_mapping as handa  # noqa: E402  (reuse the crosswalk chain)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'
REL_DIR = DATA_DIR / 'handa' / 'aei_releases'
OUT_OCC = DATA_DIR / 'styrk08_aei_collaboration.csv'
OUT_TASKS = DATA_DIR / 'styrk08_aei_tasks.csv'

TYPES = ['directive', 'feedback loop', 'task iteration', 'validation', 'learning']
AUTOMATE = TYPES[:2]
AUGMENT = TYPES[2:]
TOP_TASKS = 15          # tasks kept per occupation in the task table
MIN_TASK_N = 10         # a task needs this many classified conversations to be listed
HANDA_DATE = '2024-12-01'   # the original Handa et al. (2025) vintage


def read_handa():
    """The March 2025 release as pseudo-counts: usage pct x task share."""
    counts: dict = defaultdict(dict)
    usage = {}
    pct = handa.load_task_pct()
    ava = handa.load_ava()
    for task, p in pct.items():
        a = ava.get(task)
        if not a:
            continue
        usage[task] = p
        scale = p * 1000.0
        counts[task] = {
            'directive': scale * a['directive'],
            'feedback loop': scale * a['feedback_loop'],
            'task iteration': scale * a['task_iteration'],
            'validation': scale * a['validation'],
            'learning': scale * a['learning'],
        }
    return counts, usage


def read_release(platform: str, date: str):
    """Return {task: {type: count}} and {task: pct} for one release slice."""
    if date == HANDA_DATE:
        return read_handa()
    counts: dict = defaultdict(dict)
    with open(REL_DIR / f'onet_task_collaboration_{platform}_{date}.csv',
              encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['count']:
                counts[row['task_name']][row['collaboration']] = float(row['count'])
    usage = {}
    with open(REL_DIR / f'onet_task_{platform}_{date}.csv', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['pct']:
                usage[row['task_name']] = float(row['pct'])
    return counts, usage


def releases():
    seen = [('claude_ai', HANDA_DATE)]
    for p in sorted(REL_DIR.glob('onet_task_collaboration_*.csv')):
        stem = p.stem.replace('onet_task_collaboration_', '')
        platform, date = stem.rsplit('_', 1)
        seen.append((platform, date))
    return seen


def main():
    task_to_soc = handa.load_onet_task_to_soc()
    tasks_per_soc = handa.load_onet_tasks_per_soc()
    soc_to_isco, partial = handa.load_soc2010_to_isco08()
    styrk_codes = handa.load_styrk08_codes()

    occ_rows = []
    task_rows = []
    latest_by_platform = {}
    for platform, date in releases():
        latest_by_platform[platform] = max(latest_by_platform.get(platform, ''), date)

    for platform, date in releases():
        counts, usage = read_release(platform, date)

        # Step 1: task -> SOC 2010. Counts are split evenly across the SOC
        # codes that share a task statement, exactly as the Handa mapping
        # splits task_pct.
        soc_type = defaultdict(lambda: defaultdict(float))
        soc_usage = defaultdict(float)
        soc_tasks = defaultdict(list)
        matched = 0
        for task, types in counts.items():
            socs = task_to_soc.get(task.lower().strip())
            if not socs:
                continue
            matched += 1
            classified = sum(types.get(t, 0.0) for t in TYPES)
            n = len(socs)
            for soc in socs:
                for t in TYPES:
                    soc_type[soc][t] += types.get(t, 0.0) / n
                soc_usage[soc] += usage.get(task, 0.0) / n
                if classified >= MIN_TASK_N:
                    soc_tasks[soc].append({
                        'task_name': task,
                        'pct': usage.get(task, 0.0) / n,
                        'n_classified': classified,
                        'directive': types.get('directive', 0.0) / classified,
                        'feedback_loop': types.get('feedback loop', 0.0) / classified,
                        'task_iteration': types.get('task iteration', 0.0) / classified,
                        'validation': types.get('validation', 0.0) / classified,
                        'learning': types.get('learning', 0.0) / classified,
                    })

        # Step 2: SOC 2010 -> ISCO-08 (filtered to STYRK-08 codes).
        isco_contrib = defaultdict(list)
        for soc, types in soc_type.items():
            for isco in soc_to_isco.get(soc, []):
                isco_contrib[isco].append((soc, types, soc_usage[soc]))
        for target, socs in handa.MANUAL_STYRK_SOC_MAP.items():
            isco_contrib[target] = [(s, soc_type[s], soc_usage[s])
                                    for s in socs if s in soc_type]
        for target, source in handa.MANUAL_STYRK_MAP.items():
            if target not in isco_contrib and source in isco_contrib:
                isco_contrib[target] = isco_contrib[source]

        # Step 3: STYRK-08 scores. Shares are computed per SOC and then
        # averaged equally across contributing SOCs (the Handa rule), so a
        # small SOC that maps to the same STYRK code counts as much as a big
        # one. n_classified is the fan-out-adjusted conversation count behind
        # the share, for flagging thin cells on the site.
        for isco in sorted(isco_contrib):
            if isco not in styrk_codes:
                continue
            contribs = isco_contrib[isco]
            shares = defaultdict(float)
            n_cls = 0.0
            usage_sum = 0.0
            k = 0
            for soc, types, u in contribs:
                cls = sum(types[t] for t in TYPES)
                if cls <= 0:
                    continue
                k += 1
                for t in TYPES:
                    shares[t] += types[t] / cls
                n_cls += cls
                usage_sum += u
            if k == 0:
                continue
            row = {
                'styrk08': isco, 'platform': platform, 'date_start': date,
                'usage_pct': round(usage_sum, 6),
                'automation_share': round(sum(shares[t] for t in AUTOMATE) / k, 6),
                'augmentation_share': round(sum(shares[t] for t in AUGMENT) / k, 6),
                'n_classified': '' if date == HANDA_DATE else round(n_cls, 1),
                'n_soc_matched': k,
                'n_tasks_matched': sum(1 for s, _, _ in contribs
                                       for t in tasks_per_soc.get(s, ())
                                       if t in counts),
            }
            for t in TYPES:
                row[t.replace(' ', '_') + '_share'] = round(shares[t] / k, 6)
            occ_rows.append(row)

            if date == latest_by_platform[platform]:
                pool = [dict(tr, soc=soc) for soc, _, _ in contribs
                        for tr in soc_tasks.get(soc, [])]
                pool.sort(key=lambda r: -r['pct'])
                for tr in pool[:TOP_TASKS]:
                    task_rows.append({
                        'styrk08': isco, 'platform': platform, 'date_start': date,
                        'soc': tr['soc'], 'task_name': tr['task_name'],
                        'pct': round(tr['pct'], 6),
                        'n_classified': round(tr['n_classified'], 1),
                        'directive_share': round(tr['directive'], 4),
                        'feedback_loop_share': round(tr['feedback_loop'], 4),
                        'task_iteration_share': round(tr['task_iteration'], 4),
                        'validation_share': round(tr['validation'], 4),
                        'learning_share': round(tr['learning'], 4),
                    })
        n_occ = sum(1 for r in occ_rows if r['platform'] == platform and r['date_start'] == date)
        print(f'{platform} {date}: {matched} tasks matched to SOC, {n_occ} STYRK-08 codes')

    occ_fields = ['styrk08', 'platform', 'date_start', 'usage_pct',
                  'automation_share', 'augmentation_share',
                  'directive_share', 'feedback_loop_share', 'task_iteration_share',
                  'validation_share', 'learning_share',
                  'n_classified', 'n_soc_matched', 'n_tasks_matched']
    with open(OUT_OCC, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=occ_fields, lineterminator='\n')
        w.writeheader()
        w.writerows(occ_rows)
    task_fields = ['styrk08', 'platform', 'date_start', 'soc', 'task_name', 'pct',
                   'n_classified', 'directive_share', 'feedback_loop_share',
                   'task_iteration_share', 'validation_share', 'learning_share']
    with open(OUT_TASKS, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=task_fields, lineterminator='\n')
        w.writeheader()
        w.writerows(task_rows)
    print(f'Saved {len(occ_rows)} occupation rows -> {OUT_OCC.name}, '
          f'{len(task_rows)} task rows -> {OUT_TASKS.name}')


if __name__ == '__main__':
    main()
