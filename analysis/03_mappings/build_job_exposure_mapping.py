"""
Build the Anthropic 2026 job_exposure mapping to STYRK-08.

Chain: SOC -> ISCO-08 -> STYRK-08, with targeted manual SOC-source
corrections for Norwegian STYRK adaptations.
"""

import csv
from collections import defaultdict
from pathlib import Path

import openpyxl
import pandas as pd
import xlrd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ai_exposure'
HANDA_DIR = DATA_DIR / 'handa'

JOB_EXPOSURE_FILE = HANDA_DIR / 'job_exposure.csv'
SOC_2010_2018_FILE = DATA_DIR / 'soc_2010_to_2018_crosswalk.xlsx'
SOC_ISCO_FILE = DATA_DIR / 'isco_soc_crosswalk.xls'
STYRK08_FILE = DATA_DIR / 'styrk08_codes.csv'
OUTPUT_FILE = DATA_DIR / 'styrk08_job_exposure_mapping.csv'

MANUAL_STYRK_SOC_MAP = {
    '2267': ['29-1122'],  # Ergoterapeuter -> Occupational Therapists
    '2269': ['29-1011'],  # Kiropraktorer mv. -> Chiropractors
}


def load_job_exposure() -> dict[str, float]:
    scores = {}
    with open(JOB_EXPOSURE_FILE, encoding='utf-8') as f:
        for row in csv.DictReader(f):
            soc = row['occ_code'].strip()
            if soc:
                scores[soc] = float(row['observed_exposure'])
    return scores


def load_soc_2018_to_2010() -> dict[str, list[str]]:
    wb = openpyxl.load_workbook(str(SOC_2010_2018_FILE))
    ws = wb.active
    mapping: dict[str, list[str]] = defaultdict(list)
    for row in ws.iter_rows(min_row=10, values_only=True):
        soc2010 = str(row[0]).strip() if row[0] else ''
        soc2018 = str(row[2]).strip() if row[2] else ''
        if soc2010 and soc2018 and '-' in soc2010:
            mapping[soc2018].append(soc2010)
    return dict(mapping)


def load_soc2010_to_isco08() -> dict[str, list[str]]:
    wb = xlrd.open_workbook(str(SOC_ISCO_FILE))
    ws = wb.sheet_by_name('2010 SOC to ISCO-08')
    mapping: dict[str, list[str]] = defaultdict(list)
    for i in range(7, ws.nrows):
        soc = str(ws.cell_value(i, 0)).strip()
        isco = str(ws.cell_value(i, 3)).strip()
        if soc and isco and '-' in soc:
            if '.' in isco:
                isco = isco.split('.')[0]
            mapping[soc].append(isco.zfill(4))
    return dict(mapping)


def load_styrk08_codes() -> set[str]:
    codes = set()
    with open(STYRK08_FILE, encoding='latin-1') as f:
        for row in csv.DictReader(f):
            code = row.get('styrk08', row.get('code', ''))
            if len(code) == 4:
                codes.add(code)
    return codes


def main() -> None:
    scores = load_job_exposure()
    soc18_to_10 = load_soc_2018_to_2010()
    soc_to_isco = load_soc2010_to_isco08()
    styrk_codes = load_styrk08_codes()

    soc2010_scores: dict[str, list[float]] = defaultdict(list)
    unmapped_source = 0
    for soc, score in scores.items():
        source_socs = soc18_to_10.get(soc)
        if source_socs:
            for soc10 in source_socs:
                soc2010_scores[soc10].append(score)
        else:
            unmapped_source += 1
            soc2010_scores[soc].append(score)

    isco_contribs: dict[str, list[float]] = defaultdict(list)
    unmapped_10 = 0
    for soc, vals in soc2010_scores.items():
        score = sum(vals) / len(vals)
        if soc not in soc_to_isco:
            unmapped_10 += 1
            continue
        for isco in soc_to_isco[soc]:
            if isco in styrk_codes:
                isco_contribs[isco].append(score)

    results = []
    for isco, vals in sorted(isco_contribs.items()):
        if not vals:
            continue
        results.append({
            'styrk08': isco,
            'observed_exposure': sum(vals) / len(vals),
        })

    manual_targets = set(MANUAL_STYRK_SOC_MAP)
    results = [r for r in results if r['styrk08'] not in manual_targets]
    for styrk_target, soc_sources in MANUAL_STYRK_SOC_MAP.items():
        if styrk_target not in styrk_codes:
            continue
        vals = []
        for soc in soc_sources:
            source_vals = soc2010_scores.get(soc)
            if source_vals:
                vals.append(sum(source_vals) / len(source_vals))
        if not vals:
            print(f"Manual SOC map skipped: {styrk_target} has no source scores")
            continue
        results.append({
            'styrk08': styrk_target,
            'observed_exposure': sum(vals) / len(vals),
        })
        print(f"Manual SOC map: {styrk_target} <- {';'.join(soc_sources)}")

    results.sort(key=lambda r: r['styrk08'])

    vals = pd.Series([r['observed_exposure'] for r in results], dtype=float)
    ranks = vals.rank(method='first')
    quint = pd.qcut(ranks, 5, labels=[1, 2, 3, 4, 5]).astype(int)
    for i, r in enumerate(results):
        r['quintile'] = int(quint.iloc[i])
        r['observed_exposure'] = round(r['observed_exposure'], 6)

    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=['styrk08', 'observed_exposure', 'quintile'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Wrote {OUTPUT_FILE}")
    print(f"  Source SOC scores: {len(scores)}")
    print(f"  Source SOC scores without SOC 2018->2010 mapping: {unmapped_source}")
    print(f"  SOC 2010 scores without SOC->ISCO mapping: {unmapped_10}")
    print(f"  STYRK codes mapped: {len(results)}")


if __name__ == '__main__':
    main()
