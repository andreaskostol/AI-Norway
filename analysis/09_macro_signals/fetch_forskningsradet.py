"""
Teller søknader til Forskningsrådet per år etter søknadsdato: alle, etter søknadstype og etter sektor,
og antall som fikk bevilgning.

Kilde: Forskningsrådets åpne data, datasettet «Søknader - versjon 2» (alle søknader siden 2004, både
avslag og bevilgning), https://github.com/Forskningsradet/open-data/tree/main/datasets/soknader2.
Trukne, lukkede og avviste søknader er ikke med. README-en i repoet sier at søknader i det nye
saksbehandlingssystemet Tibi ikke er med, så 2026 er ufullstendig.

Et slankt uttrekk lagres i data/macro_signals/raw/forskningsradet/. Den fulle fila (ca. 54 MB) lastes
ned til en midlertidig mappe og slettes etterpå.

Kjor: python analysis/09_macro_signals/fetch_forskningsradet.py
"""
import json
import shutil
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "forskningsradet"
RAW.mkdir(parents=True, exist_ok=True)
BASE = "https://raw.githubusercontent.com/Forskningsradet/open-data/main/datasets/soknader2/"
KEEP = ["prosjektnummer", "soknadsfrist", "soknadsdato", "utlysnings_id", "soknadstype", "soknadstypevariant",
        "prosjektfase", "sektor", "fagomraade", "sokt_belop", "tildelt_belop"]

tmp = Path(tempfile.mkdtemp())
with requests.get(BASE + "dataset.csv", stream=True, timeout=600) as r:
    r.raise_for_status()
    r.raw.decode_content = True  # GitHub sender fila gzip-komprimert
    with open(tmp / "dataset.csv", "wb") as f:
        shutil.copyfileobj(r.raw, f)
d = pd.read_csv(tmp / "dataset.csv", usecols=KEEP, low_memory=False)
shutil.rmtree(tmp)
for name in ("README.md", "fields.csv", "meta.xml"):
    (RAW / (name if name != "README.md" else "README_kilde.md")).write_bytes(requests.get(BASE + name, timeout=60).content)
d.to_csv(RAW / "soknader_slim.csv.gz", index=False, compression="gzip")

d["period"] = d["soknadsdato"].astype(str).str[:4]
d = d[d.period.str.fullmatch(r"\d{4}")]
d["granted"] = d.prosjektfase.isin(["Bevilgning", "Avsluttet"])
rows = []
for metric, sub in (("applications", d), ("granted", d[d.granted])):
    rows += [{"metric": metric, "dim": "all", "group": "all", "period": p, "value": n}
             for p, n in sub.groupby("period").size().items()]
    for dim in ("soknadstype", "sektor"):
        rows += [{"metric": metric, "dim": dim, "group": g, "period": p, "value": n}
                 for (g, p), n in sub.groupby([dim, "period"]).size().items()]
df = pd.DataFrame(rows)
df.to_csv(OUT / "forskningsradet_soknader.csv", index=False)
meta = {"source": "Forskningsrådet, åpne data, Søknader - versjon 2", "url": BASE + "dataset.csv",
        "fetched": date.today().isoformat(),
        "updated": next(l.split(":", 1)[1].strip() for l in (RAW / "README_kilde.md").read_text(encoding="utf-8").splitlines()
                        if "Sist oppdatert" in l),
        "filter": "År etter søknadsdato. granted = prosjektfase Bevilgning eller Avsluttet",
        "note": "Trukne, lukkede og avviste søknader er ikke med. Søknader i saksbehandlingssystemet Tibi er ikke "
                "med, så 2026 er ufullstendig. Søknadstyper ble lagt om i 2019/2020."}
(OUT / "_meta_forskningsradet_soknader.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df[(df.dim == "all")].pivot(index="period", columns="metric", values="value").tail(8))
