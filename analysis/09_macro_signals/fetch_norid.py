"""
Henter nyregistrerte .no-domener per maaned fra Norid (norid.no, Nokkeltall).

Kilde: grafen "Development in the number of new registrations of domain names" paa
https://www.norid.no/en/om-domenenavn/statistics/key-figures/. Siden henter data fra
/wp-json/nrd/v1/dataset/table_antall-nyregistreringer-per-maned med parameteren year.
Raa JSON per aar lagres i data/macro_signals/raw/norid/.

Kjor: python analysis/09_macro_signals/fetch_norid.py
"""
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "norid"
RAW.mkdir(parents=True, exist_ok=True)
PAGE = "https://www.norid.no/en/om-domenenavn/statistics/key-figures/"
DATASET = "table_antall-nyregistreringer-per-maned"
API = "https://www.norid.no/wp-json/nrd/v1/dataset/" + DATASET

html = requests.get(PAGE, timeout=60).text
nonce = re.search(r'dataset="' + DATASET + r'"\s+wp-nonce="([0-9a-f]+)"', html).group(1)

rows = []
for year in range(2000, date.today().year + 1):
    js = requests.get(API, params={"lang": "en", "_wpnonce": nonce, "year": year}, timeout=60).json()
    (RAW / f"nyregistreringer_{year}.json").write_text(json.dumps(js, ensure_ascii=False), encoding="utf-8")
    for m, v in enumerate(js["datasets"][0]["data"], start=1):
        if v not in (None, "") and (year, m) < (date.today().year, date.today().month):  # dropper inneværende måned
            rows.append({"metric": "new_domains", "period": f"{year}-{m:02d}", "value": int(v)})
    yearly = js["years"][str(year)]["value"]
    s = sum(r["value"] for r in rows if r["period"].startswith(str(year)))
    print(year, "sum maaneder", s, "aarstall", yearly)

df = pd.DataFrame(rows)
df.to_csv(OUT / "norid_new_domains.csv", index=False)
meta = {"source": "Norid AS, Nokkeltall", "url": PAGE, "api": API, "fetched": date.today().isoformat(),
        "updated_at": js["updated_at"], "label": js["datasets"][0]["label"],
        "filter": "Alle nyregistrerte domenenavn per maaned, hele landet",
        "note": "Norid nevner tre regelendringer: feb. 2001, feb. 2004 (nasjonale tegn), juni 2014 (privatpersoner direkte under .no)."}
(OUT / "_meta_norid_new_domains.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print("skrev", len(df), "rader, siste", df.period.max())
