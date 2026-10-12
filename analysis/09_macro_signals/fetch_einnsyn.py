"""
Henter maanedstall fra eInnsyn: dokumenter opprettet i eInnsyn og innsynskrav sendt via eInnsyn.

Kilde: eInnsyn API, https://api.einnsyn.no/statistics (aggregateInterval=month). Raa JSON lagres i
data/macro_signals/raw/einnsyn/. createdCount er opprettet-dato i eInnsyn, ikke journaldato. Den
har et nivåskift i september 2024 (83 mill. den måneden, deretter rundt én million per måned mot
under 25 000 før). Årsaken er ikke sjekket. Serien brukes ikke i trendtesten. Innsynskrav finnes
fra februar 2018.

Kjor: python analysis/09_macro_signals/fetch_einnsyn.py
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "einnsyn"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.einnsyn.no/statistics"
last = (date.today().replace(day=1) - date.resolution).isoformat()  # siste hele maaned

r = requests.get(API, params={"aggregateFrom": "2016-01-01", "aggregateTo": last, "aggregateInterval": "month"}, timeout=120)
r.raise_for_status()
(RAW / "statistics_month.json").write_text(r.text, encoding="utf-8")
rows = [{"metric": k, "period": t["time"][:7], "value": t[c]} for t in r.json()["timeSeries"]
        for k, c in (("created", "createdCount"), ("innsynskrav", "createdInnsynskravCount"),
                     ("created_fulltext", "createdWithFulltextCount"))]
df = pd.DataFrame(rows)
df = df[df.period < date.today().strftime("%Y-%m")]  # API-et gir en rad for inneværende måned (tidssone)
df.to_csv(OUT / "einnsyn_statistics.csv", index=False)
meta = {"source": "eInnsyn (Digdir)", "url": API, "fetched": date.today().isoformat(),
        "filter": f"aggregateFrom=2016-01-01, aggregateTo={last}, aggregateInterval=month",
        "note": "created er opprettet-dato i eInnsyn, med nivåskift i september 2024, årsak ikke sjekket. innsynskrav er krav sendt via eInnsyn, tall fra 2018-02."}
(OUT / "_meta_einnsyn_statistics.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df.pivot(index="period", columns="metric", values="value").tail(6))
