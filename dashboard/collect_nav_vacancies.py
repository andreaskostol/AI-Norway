#!/usr/bin/env python3
"""
Snapshot of open job ads on arbeidsplassen.nav.no, counted per STYRK-08.

Feeds the "sammenlign arbeidsmarkedet" view on the occupation panel
(kiindeksen.no/yrker.html). Meant to run on a schedule (the Mac Mini agent
runs it; any machine with the Dropbox folder can). Each run writes one raw
snapshot and rebuilds the aggregated series from all snapshots on disk, so
running it twice on the same day is harmless.

Source: NAV's open search endpoint, no token needed
    https://arbeidsplassen.nav.no/stillinger/api/search?county=OSLO&from=0&size=100
The endpoint pages at most 10 000 hits per query, so the run loops over
counties (from the endpoint's own facet) and de-duplicates ads by uuid.

An ad can list several STYRK-08 occupations. It is counted once in each,
so per-occupation counts do not sum to the number of ads (n_ads_unique in
the totals file is the de-duplicated count).

Outputs, all under data/nav_vacancies/ (see README.md there for the contract):
    snapshots/nav_ads_YYYY-MM-DD.csv     one row per ad (raw, ~12 000 rows)
    nav_vacancies_by_styrk.csv           snapshot_date, styrk08, n_ads, n_positions, n_ads_new7d
    nav_vacancies_totals.csv             snapshot_date, n_ads_unique, n_ads_mapped, n_unmapped_names
    unmapped_names.csv                   STYRK names the code lookup could not resolve

Usage:
    python dashboard/collect_nav_vacancies.py            # today's snapshot + rebuild
    python dashboard/collect_nav_vacancies.py --rebuild  # only rebuild from snapshots
"""

import argparse
import csv
import datetime as dt
import difflib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
OUT_DIR = os.path.join(REPO, "data", "nav_vacancies")
SNAP_DIR = os.path.join(OUT_DIR, "snapshots")
CODES = os.path.join(REPO, "data", "ai_exposure", "styrk08_codes.csv")
SEARCH = "https://arbeidsplassen.nav.no/stillinger/api/search"
UA = {"User-Agent": "Mozilla/5.0 (research; kiindeksen.no; arbeidsmarkedet-panel)"}
PAGE = 100
# Seconds between requests. NAV rate-limits by address: a burst of ~120
# requests in a few minutes (one full run at 0.3 s) earned a 429 block that
# lasted well over ten minutes, for any user agent. Keep the pace gentle;
# a full run is ~130 requests, so 3 s means about seven minutes.
SLEEP = 3.0


def get_json(params, tries=6):
    """GET with back-off. NAV rate-limits (HTTP 429); wait and retry, honouring
    Retry-After when it is sent."""
    url = SEARCH + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if i == tries - 1:
                raise
            wait = 30.0 * (i + 1)
            if e.code == 429:
                try:
                    wait = max(wait, float(e.headers.get("Retry-After", 0)))
                except ValueError:
                    pass
                print(f"  429 from NAV, waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5.0 * (i + 1))


def norm(s):
    s = (s or "").lower().strip().rstrip(";").replace("–", "-")
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    s = re.sub(r"(?<=[a-zæøå])-\s*(?=[a-zæøå])", "", s)   # petro-leums -> petroleums
    s = re.sub(r"\s*([/,-])\s*", r"\1", s)
    return re.sub(r"\s+", " ", s)


def load_code_lookup():
    """STYRK-08 name -> 4-digit code, from SSB's code list (latin-1)."""
    lookup = {}
    with open(CODES, encoding="latin-1") as f:
        for r in csv.DictReader(f):
            if len(r["code"]) == 4:
                lookup.setdefault(norm(r["name"]), r["code"])
    return lookup


class NameMapper:
    def __init__(self):
        self.lookup = load_code_lookup()
        self.keys = list(self.lookup)
        self.cache = {}
        self.unmapped = defaultdict(int)

    def code(self, name):
        k = norm(name)
        if k in self.cache:
            return self.cache[k]
        code = self.lookup.get(k)
        if not code:
            close = difflib.get_close_matches(k, self.keys, n=1, cutoff=0.92)
            code = self.lookup[close[0]] if close else ""
        if not code:
            self.unmapped[name] += 1
        self.cache[k] = code
        return code


def fetch_all():
    """Every open ad, de-duplicated by uuid, via one query per county."""
    first = get_json({"size": 0})
    total = first["hits"]["total"]["value"]
    counties = [b["key"] for b in
                first["aggregations"]["counties"]["nestedLocations"]["values"]["buckets"]]
    print(f"NAV open ads: {total}. Counties: {len(counties)}.")
    ads = {}
    for county in counties:
        frm, n_county = 0, None
        while True:
            d = get_json({"county": county, "from": frm, "size": PAGE})
            hits = d["hits"]["hits"]
            if n_county is None:
                n_county = d["hits"]["total"]["value"]
            for h in hits:
                s = h["_source"]
                if s["uuid"] in ads:
                    continue
                props = s.get("properties") or {}
                styrk_names = [c["name"] for c in (s.get("categoryList") or [])
                               if c.get("categoryType") == "STYRK08" and c.get("name")]
                locs = s.get("locationList") or []
                ads[s["uuid"]] = {
                    "uuid": s["uuid"],
                    "published": (s.get("published") or "")[:10],
                    "expires": (s.get("expires") or "")[:10],
                    "county": (locs[0].get("county") or "") if locs else county,
                    "sector": props.get("sector", ""),
                    "positioncount": props.get("positioncount", ""),
                    "styrk_names": ";".join(styrk_names),
                    "title": s.get("title", ""),
                }
            frm += len(hits)
            if not hits or frm >= n_county or frm >= 10000:
                break
            time.sleep(SLEEP)
        print(f"  {county:<18} {n_county:>6}  cumulative unique {len(ads)}")
        time.sleep(SLEEP)
    return ads


def write_snapshot(ads, date):
    os.makedirs(SNAP_DIR, exist_ok=True)
    mapper = NameMapper()
    path = os.path.join(SNAP_DIR, f"nav_ads_{date}.csv")
    fields = ["uuid", "published", "expires", "county", "sector", "positioncount",
              "styrk08", "styrk_names", "title"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for a in ads.values():
            codes = []
            for name in a["styrk_names"].split(";"):
                if not name:
                    continue
                c = mapper.code(name)
                if c and c not in codes:
                    codes.append(c)
            row = dict(a)
            row["styrk08"] = ";".join(codes)
            w.writerow(row)
    with open(os.path.join(OUT_DIR, "unmapped_names.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["styrk_name", "n_ads"])
        for name, n in sorted(mapper.unmapped.items(), key=lambda x: -x[1]):
            w.writerow([name, n])
    print(f"Snapshot {path}: {len(ads)} ads, {len(mapper.unmapped)} unmapped names")


def rebuild():
    """Aggregate every snapshot on disk into the two series files."""
    rows, totals = [], []
    for fn in sorted(os.listdir(SNAP_DIR)) if os.path.isdir(SNAP_DIR) else []:
        m = re.match(r"nav_ads_(\d{4}-\d{2}-\d{2})\.csv$", fn)
        if not m:
            continue
        date = m.group(1)
        cutoff = (dt.date.fromisoformat(date) - dt.timedelta(days=7)).isoformat()
        n_ads = defaultdict(int)
        n_pos = defaultdict(int)
        n_new = defaultdict(int)
        n_unique = n_mapped = 0
        with open(os.path.join(SNAP_DIR, fn), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                n_unique += 1
                codes = [c for c in r["styrk08"].split(";") if c]
                if codes:
                    n_mapped += 1
                try:
                    pos = int(float(r["positioncount"] or 1))
                except ValueError:
                    pos = 1
                for c in codes:
                    n_ads[c] += 1
                    n_pos[c] += max(pos, 1)
                    if r["published"] >= cutoff:
                        n_new[c] += 1
        for c in sorted(n_ads):
            rows.append({"snapshot_date": date, "styrk08": c, "n_ads": n_ads[c],
                         "n_positions": n_pos[c], "n_ads_new7d": n_new[c]})
        totals.append({"snapshot_date": date, "n_ads_unique": n_unique,
                       "n_ads_mapped": n_mapped, "n_styrk_codes": len(n_ads)})
    with open(os.path.join(OUT_DIR, "nav_vacancies_by_styrk.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["snapshot_date", "styrk08", "n_ads",
                                          "n_positions", "n_ads_new7d"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(OUT_DIR, "nav_vacancies_totals.csv"), "w", newline="",
              encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["snapshot_date", "n_ads_unique", "n_ads_mapped",
                                          "n_styrk_codes"], lineterminator="\n")
        w.writeheader()
        w.writerows(totals)
    print(f"Rebuilt series: {len(totals)} snapshots, {len(rows)} occupation rows")


def main():
    global SLEEP
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="only rebuild from snapshots")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--sleep", type=float, default=SLEEP,
                    help="seconds between requests (default %(default)s)")
    args = ap.parse_args()
    SLEEP = args.sleep
    os.makedirs(OUT_DIR, exist_ok=True)
    if not args.rebuild:
        ads = fetch_all()
        write_snapshot(ads, args.date)
    rebuild()


if __name__ == "__main__":
    sys.exit(main())
