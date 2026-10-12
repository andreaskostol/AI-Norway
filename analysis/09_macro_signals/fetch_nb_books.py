"""
Teller boker i Nasjonalbibliotekets katalog etter utgivelsesaar: alle og paa bokmaal eller nynorsk.

Kilde: Nasjonalbibliotekets API (api.nb.no/catalog/v1/items), filter mediatype:boker og year:<aar>.
Katalogen bygger paa pliktavlevering, og de siste aarene er ufullstendige fordi katalogiseringen tar tid.
Raa svar (totalElements per sok) lagres i data/macro_signals/raw/nb_books/.

Kjor: python analysis/09_macro_signals/fetch_nb_books.py
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "nb_books"
RAW.mkdir(parents=True, exist_ok=True)
API = "https://api.nb.no/catalog/v1/items"
GROUPS = {"all": [], "nob": ["languages:nob"], "nno": ["languages:nno"]}

rows, raw = [], {}
for year in range(2010, date.today().year):
    for g, extra in GROUPS.items():
        params = [("q", "*"), ("filter", "mediatype:bøker"), ("filter", f"year:{year}"), ("size", 1)] + \
                 [("filter", f) for f in extra]
        js = requests.get(API, params=params, timeout=60).json()
        n = js["page"]["totalElements"]
        raw[f"{g}_{year}"] = n
        rows.append({"metric": "books", "group": g, "period": str(year), "value": n})
(RAW / "totals.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")
df = pd.DataFrame(rows)
df.to_csv(OUT / "nb_books.csv", index=False)
meta = {"source": "Nasjonalbiblioteket, katalog-API", "url": API, "fetched": date.today().isoformat(),
        "filter": "q=*, mediatype:bøker, year:<aar>, eventuelt languages:nob eller languages:nno",
        "note": "Utgivelsesaar i katalogen. De siste aarene er ufullstendige fordi katalogisering tar tid."}
(OUT / "_meta_nb_books.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df.pivot(index="period", columns="group", values="value").tail(10))
