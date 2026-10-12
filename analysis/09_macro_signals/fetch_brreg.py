"""
Teller enheter i Enhetsregisteret etter registreringsmaaned: alle, AS, ENK og naeringskode 62 og 63.

Kilde: Bronnoysundregistrene, full nedlasting av Enhetsregisteret som CSV (gzip, ca. 150 MB).
Filen inneholder bare enheter som finnes i dag. Slettede enheter mangler, saa eldre kohorter er
undertalt. Sammenlign med SSB 08076 (fetch_ssb_foretak.py), som teller alle nye foretak.

Et slankt uttrekk (orgnr, orgform, naeringskode, datoer) lagres i data/macro_signals/raw/brreg/.
Den fulle filen lastes ned til en midlertidig mappe og slettes etterpaa.

Kjor: python analysis/09_macro_signals/fetch_brreg.py
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
RAW = OUT / "raw" / "brreg"
RAW.mkdir(parents=True, exist_ok=True)
URL = "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv"
COLS = {"organisasjonsnummer": "orgnr", "organisasjonsform.kode": "orgform", "naeringskode1.kode": "nace",
        "registreringsdatoenhetsregisteret": "reg_date", "stiftelsesdato": "founded",
        "registreringsdatoForetaksregisteret": "reg_date_fr"}

tmp = Path(tempfile.mkdtemp())
with requests.get(URL, stream=True, timeout=600) as r:
    r.raise_for_status()
    headers = dict(r.headers)
    with open(tmp / "enheter.csv.gz", "wb") as f:
        shutil.copyfileobj(r.raw, f)
df = pd.read_csv(tmp / "enheter.csv.gz", usecols=list(COLS), dtype=str).rename(columns=COLS)
shutil.rmtree(tmp)
df.to_csv(RAW / "enheter_slim.csv.gz", index=False, compression="gzip")

df["period"] = df["reg_date"].str[:7]
df["nace2"] = df["nace"].str[:2]
df = df[df["period"] >= "2008-01"]
groups = {"all": df, "AS": df[df.orgform == "AS"], "ENK": df[df.orgform == "ENK"],
          "nace62": df[df.nace2 == "62"], "nace63": df[df.nace2 == "63"],
          "nace62_AS": df[(df.nace2 == "62") & (df.orgform == "AS")]}
rows = [{"metric": k, "period": p, "value": int(n)} for k, g in groups.items()
        for p, n in g.groupby("period").size().items()]
agg = pd.DataFrame(rows)
agg = agg[agg.period < date.today().strftime("%Y-%m")]  # dropper inneværende måned
agg.to_csv(OUT / "brreg_registrations.csv", index=False)

meta = {"source": "Bronnoysundregistrene, Enhetsregisteret, full nedlasting", "url": URL,
        "fetched": date.today().isoformat(), "file": headers.get("content-disposition"),
        "last_modified": headers.get("last-modified"), "rows_in_file": int(len(df)),
        "filter": "registreringsdatoenhetsregisteret fra 2008-01. nace2 = forste to siffer i naeringskode1",
        "note": "Bare enheter som er registrert i dag. Slettede enheter mangler. Naeringskoder er slik de star i dag."}
(OUT / "_meta_brreg_registrations.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print(agg.pivot(index="period", columns="metric", values="value").tail(8))
