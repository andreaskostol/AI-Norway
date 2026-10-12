"""
Teller høringssvar per høring på regjeringen.no for høringer publisert fra 2016.

Kilde: regjeringen.no. Listen over høringer (https://www.regjeringen.no/no/dokument/hoyringar/id1763/?page=N,
sortert etter dato) gir lenke, dato, departement, høringsfrist og status. Svarvisningen for hver høring
(<lenke>?showSvar=true) oppgir antall treff, for eksempel «Søket ditt gav 18 treff» eller «Viser 1-100 av
108 treff». Tellingen omfatter også svar «uten merknader» og enkelte dokumenter som departementet har
lagt i svarlisten. robots.txt sperrer filterparametre (term, ownerid, from, to osv.), ikke page eller showSvar.
Ett kall per 1,5 sekund. Svar lagres i data/macro_signals/raw/horinger/svar.jsonl og hentes ikke på nytt
for høringer med frist som er passert.

Kjor: python analysis/09_macro_signals/fetch_horinger.py
"""
import html
import json
import re
import time
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_signals"
RAW = OUT / "raw" / "horinger"
RAW.mkdir(parents=True, exist_ok=True)
BASE = "https://www.regjeringen.no"
LIST = BASE + "/no/dokument/hoyringar/id1763/"
FIRST = date(2016, 1, 1)
S = requests.Session()
S.headers["User-Agent"] = "Mozilla/5.0 (forskningsprosjekt AI-Norway, Frischsenteret; telling av horingssvar)"  # bare ASCII, ellers 403


def get(url, params=None):
    for i in range(5):
        time.sleep(1.5)
        try:
            r = S.get(url, params=params, timeout=60)
        except requests.RequestException as e:  # tidsavbrudd og brutte forbindelser: vent og proev igjen
            print("  nettverksfeil, venter:", type(e).__name__, flush=True)
            time.sleep(30 * (i + 1))
            continue
        if r.status_code == 200:
            return r.text
        time.sleep(30 * (i + 1))
    raise RuntimeError(f"ga opp: {url}")


def text(t):
    t = re.sub(r"<(script|style).*?</\1>", "", t, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))


def dmy(s):
    m = re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", (s or "").strip())  # noen frister er ufullstendige, f.eks. «12.»
    return date(int(m[3]), int(m[2]), int(m[1])) if m else None


# 1. Listen over høringer, nyeste først, til datoene er eldre enn FIRST
rows, page = [], 1
while True:
    t = get(LIST, {"page": page})
    items = re.findall(r'<li class="listItem">(.*?)</li>', t, flags=re.S)
    for it in items:
        url = re.search(r'href="(/no/dokumenter/[^"]+)"', it).group(1)
        f = lambda cls: (re.search(rf'class="{cls}">([^<]*)<', it) or [None, ""])[1].strip()
        frist = re.search(r"(?:H&#xF8;|Hø)ringsfrist:\s*([\d.]+)", it)
        status = re.search(r'event-details-open">([^<]*)<', it)
        rows.append({"url": url, "id": re.search(r"/id(\d+)/", url).group(1), "title": text(re.search(r"<a[^>]*>(.*?)</a>", it, flags=re.S).group(1)).strip(),
                     "date": dmy(f("date")), "type": html.unescape(f("type")), "department": html.unescape(f("department")),
                     "deadline": dmy(frist.group(1)) if frist else None,
                     "status": html.unescape(status.group(1)).replace("Status:", "").strip() if status else ""})
    if not items or min(r["date"] or date.max for r in rows[-len(items):]) < FIRST:
        break
    page += 1
    if page % 20 == 0:
        print("listeside", page, rows[-1]["date"], flush=True)
lst = pd.DataFrame(rows).drop_duplicates("id")
lst = lst[lst.date.notna() & (lst.date >= FIRST)]
lst.to_csv(RAW / "listing.csv", index=False)
print("høringer fra", FIRST, len(lst), flush=True)

# 2. Antall svar per høring
f = RAW / "svar.jsonl"
done = {json.loads(l)["id"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()} if f.exists() else {}
for i, r in enumerate(lst.itertuples()):
    if r.id in done and r.deadline and r.deadline < date.fromisoformat(done[r.id]["fetched"]):
        continue
    tx = text(get(BASE + r.url, {"showSvar": "true"}))
    m = re.search(r"(?:Søket ditt gav|av) (\d+) treff", tx)
    rec = {"id": r.id, "n_svar": int(m.group(1)) if m else None, "fetched": date.today().isoformat()}
    with f.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
    done[r.id] = rec
    if i % 100 == 0:
        print(i, r.date, rec, flush=True)

lst["n_svar"] = lst.id.map(lambda k: done.get(k, {}).get("n_svar"))
lst.drop(columns=["title"]).to_csv(OUT / "horinger.csv", index=False)
meta = {"source": "regjeringen.no, høringer", "url": LIST, "fetched": date.today().isoformat(),
        "filter": f"Høringer publisert fra {FIRST}. n_svar = antall treff i svarvisningen (?showSvar=true)",
        "note": "Tellingen omfatter svar uten merknader og enkelte dokumenter fra departementet. Høringer uten "
                "svarvisning har n_svar tom."}
(OUT / "_meta_horinger.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False), encoding="utf-8")
print("skrev", len(lst), "høringer,", lst.n_svar.notna().sum(), "med antall svar")
