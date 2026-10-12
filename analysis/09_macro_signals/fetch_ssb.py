"""
Henter SSB-tabeller til trendtesten:
  08076  Nye foretak per kvartal (SN2007, 2008K1 og utover): hele landet, alle naeringer og NACE 58, 62, 63
  10990  Patentsoknader per aar
  10991  Designsoknader per aar
  10992  Varemerkesoknader per aar

Kilde: SSB PxWebAPI v0, json-stat2. Samme oppsett som analysis/08_ai_boom/fetch_ssb.py.
Skriver data/macro_signals/ssb_<tabell>_<innhold>.csv og _meta_ssb_<tabell>.json.

Kjor: python analysis/09_macro_signals/fetch_ssb.py
"""
import itertools
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
API = "https://data.ssb.no/api/v0/no/table/{}"
JOBS = [
    ("08076", "nye_foretak", {"Region": ["0"], "NACE2007": ["01-99", "58", "62", "63"]}),
    ("10990", "patentsoknader", {}),
    ("10991", "designsoknader", {}),
    ("10992", "varemerkesoknader", {}),
]


def to_long(js):
    dims, sizes, cats = js["id"], js["size"], {}
    for d in dims:
        c = js["dimension"][d]["category"]
        codes = sorted(c["index"], key=c["index"].get) if isinstance(c["index"], dict) else list(c["index"])
        cats[d] = [(k, c.get("label", {}).get(k, k)) for k in codes]
    rows = []
    for i, combo in enumerate(itertools.product(*[range(s) for s in sizes])):
        row = {}
        for d, k in zip(dims, combo):
            row[f"{d}_code"], row[f"{d}_label"] = cats[d][k]
        row["value"] = js["value"][i]
        rows.append(row)
    return pd.DataFrame(rows)


for tid, name, flt in JOBS:
    meta = requests.get(API.format(tid), timeout=60).json()
    query = [{"code": v["code"], "selection": {"filter": "item", "values": flt[v["code"]]} if v["code"] in flt
              else {"filter": "all", "values": ["*"]}} for v in meta["variables"]]
    r = requests.post(API.format(tid), json={"query": query, "response": {"format": "json-stat2"}}, timeout=300)
    r.raise_for_status()
    js = r.json()
    df = to_long(js)
    df["period"] = df["Tid_code"].str.replace("K", "Q")
    df.to_csv(OUT / f"ssb_{tid}_{name}.csv", index=False, encoding="utf-8")
    cat_notes = {d: js["dimension"][d]["category"].get("note") for d in js["id"] if js["dimension"][d]["category"].get("note")}
    info = {"table": tid, "title": meta["title"], "url": API.format(tid), "fetched": date.today().isoformat(),
            "updated": js.get("updated"), "filter": flt, "note": js.get("note"), "kategori_noter": cat_notes}
    (OUT / f"_meta_ssb_{tid}.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    print(meta["title"], "| oppdatert", js.get("updated"), "| rader", len(df), "| siste", df.period.max())
