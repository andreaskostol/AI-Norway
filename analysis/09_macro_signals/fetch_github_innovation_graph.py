"""
Henter GitHub Innovation Graph (github.com/github/innovationgraph, CC0): git pushes, repositories,
developers og organizations per oekonomi og kvartal fra 2020K1.

Git pushes er en strom per kvartal. De tre andre er bestander ved kvartalsslutt, saa nye enheter per
kvartal maa regnes som endring i bestand (run_all.py gjor det). Raa CSV-er lagres i
data/macro_signals/raw/github_innovation_graph/. Output beholder Norge, USA, Sverige, Danmark, Finland og EU.

Kjor: python analysis/09_macro_signals/fetch_github_innovation_graph.py
"""
import json
from datetime import date
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "github_innovation_graph"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://raw.githubusercontent.com/github/innovationgraph/main/data/{}.csv"
METRICS = ["git_pushes", "repositories", "developers", "organizations"]
KEEP = ["NO", "US", "SE", "DK", "FI", "EU"]

frames = []
for m in METRICS:
    r = requests.get(URL.format(m), timeout=120)
    r.raise_for_status()
    (RAW / f"{m}.csv").write_bytes(r.content)
    d = pd.read_csv(RAW / f"{m}.csv", keep_default_na=False)  # NA er Namibia
    d = d[d.iso2_code.isin(KEEP)]
    frames.append(pd.DataFrame({"metric": m, "iso2_code": d.iso2_code, "period": d.year.astype(str) + "Q" + d.quarter.astype(str),
                                "value": d[m]}))
df = pd.concat(frames).sort_values(["metric", "iso2_code", "period"])
df.to_csv(OUT / "github_innovation_graph.csv", index=False)
commit = requests.get("https://api.github.com/repos/github/innovationgraph/commits?path=data&per_page=1", timeout=60).json()
meta = {"source": "GitHub Innovation Graph", "url": "https://github.com/github/innovationgraph", "license": "CC0-1.0",
        "fetched": date.today().isoformat(), "data_commit": commit[0]["sha"], "data_commit_date": commit[0]["commit"]["committer"]["date"],
        "filter": {"iso2_code": KEEP, "metrics": METRICS},
        "note": "Aktivitet tilordnes land etter IP-adresse. Bare offentlige repoer. Boter og svaert aktive kontoer er "
                "utelatt. repositories, developers og organizations er bestander ved kvartalsslutt."}
(OUT / "_meta_github_innovation_graph.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(df[df.iso2_code == "NO"].pivot(index="period", columns="metric", values="value").tail(6))
