"""
Henter maanedstall for norsk Wikipedia (bokmaal/riksmaal og nynorsk): redigeringer, nye sider og
aktive redaktorer, bare innholdssider og bare menneskelige brukere (editor-type user).

Kilde: Wikimedia Analytics REST API (wikimedia.org/api/rest_v1/metrics). Raa JSON lagres i
data/macro_signals/raw/wikimedia/.

Kjor: python analysis/09_macro_signals/fetch_wikimedia.py
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "wikimedia"
RAW.mkdir(parents=True, exist_ok=True)
BASE = "https://wikimedia.org/api/rest_v1/metrics"
HEAD = {"User-Agent": "AI-Norway research project (Frisch Centre, Oslo) macro_signals/1.0"}
FIRST, LAST = "20100101", date.today().replace(day=1).strftime("%Y%m%d")  # siste hele maaned
ENDPOINTS = {
    "edits": ("edits/aggregate/{p}/user/content/monthly/{a}/{b}", "edits"),
    "new_pages": ("edited-pages/new/{p}/user/content/monthly/{a}/{b}", "new_pages"),
    "active_editors": ("editors/aggregate/{p}/user/content/all-activity-levels/monthly/{a}/{b}", "editors"),
}

rows = []
for project in ("no.wikipedia.org", "nn.wikipedia.org"):
    for metric, (path, key) in ENDPOINTS.items():
        r = requests.get(f"{BASE}/{path.format(p=project, a=FIRST, b=LAST)}", headers=HEAD, timeout=60)
        r.raise_for_status()
        (RAW / f"{project.split('.')[0]}_{metric}.json").write_text(r.text, encoding="utf-8")
        rows += [{"project": project, "metric": metric, "period": x["timestamp"][:7], "value": x[key]}
                 for x in r.json()["items"][0]["results"]]

df = pd.DataFrame(rows)
df.to_csv(OUT / "wikimedia_norway.csv", index=False)
meta = {"source": "Wikimedia Analytics REST API", "url": BASE, "fetched": date.today().isoformat(),
        "filter": "editor-type=user (ikke boter), page-type=content, monthly", "projects": ["no.wikipedia.org", "nn.wikipedia.org"]}
(OUT / "_meta_wikimedia_norway.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df[df.project == "no.wikipedia.org"].pivot(index="period", columns="metric", values="value").tail(6))
