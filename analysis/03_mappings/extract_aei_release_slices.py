"""
Pull the small task-level slices out of the Anthropic Economic Index raw
release files.

The raw files on Hugging Face (Anthropic/EconomicIndex, 40-100 MB each) are
too big to keep in the repo. This script keeps only the rows the occupation
panel and the cross-provider notes need, and writes them as small CSVs to
data/ai_exposure/handa/aei_releases/:

  onet_task_collaboration_{platform}_{date}.csv
      task_name, collaboration, count, pct       (global, one row per task x type)
  onet_task_{platform}_{date}.csv
      task_name, count, pct                      (global task usage share)
  collaboration_by_country_{platform}_{date}.csv
      geo_id, collaboration, count, pct          (country level, Claude.ai only)
  usage_by_country_{platform}_{date}.csv
      geo_id, usage_count, usage_pct             (country share of conversations)

Usage:
  python extract_aei_release_slices.py RAW_FILE [RAW_FILE ...]

Raw files: release_2026_01_15/data/intermediate/aei_raw_*_2025-11-13_to_2025-11-20.csv
           release_2026_03_24/data/aei_raw_*_2026-02-05_to_2026-02-12.csv
Download with curl -L from
https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/<path>.
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = BASE_DIR / 'data' / 'ai_exposure' / 'handa' / 'aei_releases'

csv.field_size_limit(10 ** 9)


def platform_key(label: str) -> str:
    # "Claude AI (Free, Pro, and Max)" -> claude_ai ; "1P API" -> api
    return 'api' if label.strip().upper().startswith('1P API') else 'claude_ai'


def extract(path: Path) -> None:
    # One pass over the raw file. The three slices are keyed by (task, type)
    # so count and pct rows for the same cell land on the same output row.
    task_collab: dict = defaultdict(dict)
    task_usage: dict = defaultdict(dict)
    country_collab: dict = defaultdict(dict)
    country_usage: dict = defaultdict(dict)
    platform = None
    date_start = None
    with open(path, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if platform is None:
                platform = platform_key(row['platform_and_product'])
                date_start = row['date_start']
            facet = row['facet']
            var = row['variable']
            kind = 'count' if var.endswith('_count') else (
                'pct' if var.endswith('_pct') else None)
            if kind is None:
                continue
            if facet == 'onet_task::collaboration' and row['geo_id'] == 'GLOBAL':
                task, ctype = row['cluster_name'].rsplit('::', 1)
                task_collab[(task, ctype)][kind] = row['value']
            elif facet == 'onet_task' and row['geo_id'] == 'GLOBAL':
                task_usage[row['cluster_name']][kind] = row['value']
            elif facet == 'collaboration' and row['geography'] == 'country':
                country_collab[(row['geo_id'], row['cluster_name'])][kind] = row['value']
            elif facet == 'country' and row['geography'] == 'country':
                # usage_count / usage_pct: the country's share of all
                # Claude.ai conversations in the sample week.
                country_usage[row['geo_id']][kind] = row['value']

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tag = f'{platform}_{date_start}'

    with open(OUT_DIR / f'onet_task_collaboration_{tag}.csv', 'w',
              newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['task_name', 'collaboration', 'count', 'pct'])
        for (task, ctype), v in sorted(task_collab.items()):
            w.writerow([task, ctype, v.get('count', ''), v.get('pct', '')])

    with open(OUT_DIR / f'onet_task_{tag}.csv', 'w',
              newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['task_name', 'count', 'pct'])
        for task, v in sorted(task_usage.items()):
            w.writerow([task, v.get('count', ''), v.get('pct', '')])

    if country_collab:
        with open(OUT_DIR / f'collaboration_by_country_{tag}.csv', 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(['geo_id', 'collaboration', 'count', 'pct'])
            for (geo, ctype), v in sorted(country_collab.items()):
                w.writerow([geo, ctype, v.get('count', ''), v.get('pct', '')])

    if country_usage:
        with open(OUT_DIR / f'usage_by_country_{tag}.csv', 'w',
                  newline='', encoding='utf-8') as f:
            w = csv.writer(f, lineterminator='\n')
            w.writerow(['geo_id', 'usage_count', 'usage_pct'])
            for geo, v in sorted(country_usage.items()):
                w.writerow([geo, v.get('count', ''), v.get('pct', '')])

    print(f'{path.name}: platform={platform} date={date_start} '
          f'tasks_with_collab={len({t for t, _ in task_collab})} '
          f'tasks_with_usage={len(task_usage)} '
          f'countries={len({g for g, _ in country_collab})}')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        extract(Path(p))
