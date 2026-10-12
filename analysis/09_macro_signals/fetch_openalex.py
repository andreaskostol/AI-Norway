"""
Teller publikasjoner med minst én norsk institusjon per publiseringsmaaned i OpenAlex,
fordelt paa type (article, preprint osv.) og fagfelt (primary_topic.field).

Kilde: OpenAlex API (api.openalex.org/works). Uten nokkel gir API-et 1000 kreditter per dag.
Hver maaned koster to kall: group_by=type og group_by=primary_topic.field.id. I tillegg telles
verk datert 1. januar (totalt, etter type og etter fagfelt), fordi verk med bare aarstall ofte faar den datoen.
Raa svar lagres i data/macro_signals/raw/openalex/, og kall som finnes der gjores ikke paa nytt.

Kjor: python analysis/09_macro_signals/fetch_openalex.py
"""
import json
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "openalex"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.openalex.org/works"
BASE = "institutions.country_code:no"
START, END = (2015, 1), (2026, 9)


def call(name, params):
    f = RAW / f"{name}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    time.sleep(0.2)
    r = requests.get(API, params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    js["meta"].pop("x_query", None)
    f.write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
    return js


rows = []
y, m = START
while (y, m) <= END:
    last = (date(y + (m == 12), m % 12 + 1, 1) - date.resolution).day
    flt = f"{BASE},from_publication_date:{y}-{m:02d}-01,to_publication_date:{y}-{m:02d}-{last:02d}"
    period = f"{y}-{m:02d}"
    t = call(f"type_{period}", {"filter": flt, "group_by": "type", "per_page": 200})
    rows.append({"metric": "works", "group": "all", "period": period, "value": t["meta"]["count"]})
    rows += [{"metric": "works_type", "group": g["key_display_name"], "period": period, "value": g["count"]}
             for g in t["group_by"]]
    fl = call(f"field_{period}", {"filter": flt, "group_by": "primary_topic.field.id", "per_page": 200})
    rows += [{"metric": "works_field", "group": g["key_display_name"], "period": period, "value": g["count"]}
             for g in fl["group_by"]]
    if m == 1:
        j1 = call(f"jan1_{y}", {"filter": f"{BASE},publication_date:{y}-01-01", "per_page": 1})
        rows.append({"metric": "works_jan1", "group": "all", "period": period, "value": j1["meta"]["count"]})
        for g_by, metric in (("type", "works_type_jan1"), ("primary_topic.field.id", "works_field_jan1")):
            js = call(f"jan1_{metric}_{y}", {"filter": f"{BASE},publication_date:{y}-01-01", "group_by": g_by,
                                             "per_page": 200})
            rows += [{"metric": metric, "group": g["key_display_name"], "period": period, "value": g["count"]}
                     for g in js["group_by"]]
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)

df = pd.DataFrame(rows)
df.to_csv(OUT / "openalex_norway.csv", index=False)
meta = {"source": "OpenAlex", "url": API, "fetched": date.today().isoformat(),
        "filter": f"{BASE}, publiseringsdato i maaneden. group_by type og primary_topic.field.id",
        "note": "Verk med bare aarstall faar ofte 1. januar som dato (se works_jan1). Siste maaneder er "
                "ufullstendige fordi OpenAlex indekserer med forsinkelse."}
(OUT / "_meta_openalex_norway.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df[df.metric == "works"].tail(12).to_string(index=False))
