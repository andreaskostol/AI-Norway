"""
Teller kliniske studier med minst ett studiested i Norge per maaned i ClinicalTrials.gov:
etter startdato (StartDate) og etter forste innsendingsdato (StudyFirstSubmitDate).

Kilde: ClinicalTrials.gov API v2, /api/v2/studies med filter.advanced og countTotal=true.
Raa svar (totalCount per sok) logges i data/macro_signals/raw/clinicaltrials/log.jsonl.

Kjor: python analysis/09_macro_signals/fetch_clinicaltrials.py
"""
import calendar
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "clinicaltrials"
RAW.mkdir(parents=True, exist_ok=True)
LOG = RAW / "log.jsonl"
API = "https://clinicaltrials.gov/api/v2/studies"
FIELDS = {"start": "StartDate", "first_submitted": "StudyFirstSubmitDate"}
START, END = (2014, 1), (2026, 9)

done = {json.loads(l)["filter"]: json.loads(l) for l in LOG.read_text().splitlines()} if LOG.exists() else {}
rows = []
y, m = START
while (y, m) <= END:
    last = calendar.monthrange(y, m)[1]
    for metric, field in FIELDS.items():
        flt = f"AREA[LocationCountry]Norway AND AREA[{field}]RANGE[{y}-{m:02d}-01,{y}-{m:02d}-{last:02d}]"
        if flt not in done:
            time.sleep(1.3)
            r = requests.get(API, params={"filter.advanced": flt, "countTotal": "true", "pageSize": 1,
                                          "fields": "NCTId"}, timeout=60)
            r.raise_for_status()
            done[flt] = {"filter": flt, "totalCount": r.json()["totalCount"], "fetched": date.today().isoformat()}
            with LOG.open("a") as f:
                f.write(json.dumps(done[flt]) + "\n")
        rows.append({"metric": metric, "period": f"{y}-{m:02d}", "value": done[flt]["totalCount"]})
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)

df = pd.DataFrame(rows)
df.to_csv(OUT / "clinicaltrials_norway.csv", index=False)
meta = {"source": "ClinicalTrials.gov API v2", "url": API, "fetched": date.today().isoformat(),
        "filter": "AREA[LocationCountry]Norway og RANGE paa StartDate eller StudyFirstSubmitDate per maaned",
        "note": "Startdato kan vaere planlagt (anticipated) for de siste maanedene. Studier registrert bare i EU CTIS er ikke med."}
(OUT / "_meta_clinicaltrials_norway.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df.pivot(index="period", columns="metric", values="value").tail(8))
