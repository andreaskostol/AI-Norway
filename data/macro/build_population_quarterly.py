"""
Last ned SSB tabell 07459 (befolkning 1. januar etter 1-aarig alder) og
interpoler til ARBLONN-stikkdager (16. feb / mai / aug / nov), som er
midten av kvartalene Q1-Q4.

Output: ssb_population_by_age_quarterly.csv (overskriver eksisterende)
Format: date, age, population  med date = 'YYYY-Qn'
"""

import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

OUTDIR = Path(__file__).parent
URL = "https://data.ssb.no/api/v0/no/table/07459/"

YEARS = list(range(2019, 2027))  # trenger nabopunkter for interpolasjon
AGES = [f"{a:03d}" for a in range(0, 105)] + ["105+"]  # 07459 har 000-104, 105+

# Stikkdag (dag-i-aar) for hver kvartalsmidte
QUARTER_DAYS = {
    "Q1": date(2000, 2, 16).timetuple().tm_yday,   # 47
    "Q2": date(2000, 5, 16).timetuple().tm_yday,   # 137
    "Q3": date(2000, 8, 16).timetuple().tm_yday,   # 229
    "Q4": date(2000, 11, 16).timetuple().tm_yday,  # 321
}
DAYS_IN_YEAR = 365


def fetch():
    body = {
        "query": [
            {"code": "Region", "selection": {"filter": "item", "values": ["0"]}},
            {"code": "Kjonn", "selection": {"filter": "all", "values": ["*"]}},
            {"code": "Alder", "selection": {"filter": "item", "values": AGES}},
            {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in YEARS]}},
        ],
        "response": {"format": "json-stat2"},
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def parse(payload):
    """Returner dict[(year, age)] = total befolkning (begge kjoenn)."""
    dims = payload["dimension"]
    age_index = dims["Alder"]["category"]["index"]
    year_index = dims["Tid"]["category"]["index"]
    sex_index = dims["Kjonn"]["category"]["index"]
    n_age = len(age_index)
    n_year = len(year_index)
    n_sex = len(sex_index)
    values = payload["value"]

    # Order in json-stat2: Region(1) x Kjonn x Alder x ContentsCode(1) x Tid
    out = {}
    for sex_code, si in sex_index.items():
        for age_code, ai in age_index.items():
            for year_code, yi in year_index.items():
                idx = si * n_age * n_year + ai * n_year + yi
                v = values[idx]
                if v is None:
                    continue
                age_int = 105 if age_code == "105+" else int(age_code)
                key = (int(year_code), age_int)
                out[key] = out.get(key, 0) + v
    return out


def interpolate(annual: dict) -> list[dict]:
    """For hvert (kvartal, alder), lineaer interpolasjon mellom 1. januar-stikkdager.

    1. januar i year_t er fraction 0; 1. januar i year_{t+1} er fraction 1.
    Stikkdagen for Qn ligger ved (day_of_year - 1) / 365 inn i aaret.
    """
    rows = []
    years = sorted({y for (y, _) in annual.keys()})
    ages = sorted({a for (_, a) in annual.keys()})

    # For aar med naboaar: lineaer interpolasjon mellom 1.jan-stikkdager.
    # For siste aar (uten naboaar etter seg): extrapoler basert paa
    # fjoraarets vekst, slik at vi faar med Q1-Q4 ogsaa for siste aar.
    last_year = years[-1]

    for y in years:
        for a in ages:
            v0 = annual.get((y, a))
            if v0 is None:
                continue
            v1 = annual.get((y + 1, a))
            if v1 is None:
                # Siste aar: extrapoler med foregaaende aars endring (eller 0)
                v_prev = annual.get((y - 1, a))
                growth = (v0 - v_prev) if v_prev is not None else 0
                v1 = v0 + growth
            for q, doy in QUARTER_DAYS.items():
                frac = (doy - 1) / DAYS_IN_YEAR
                v = v0 + (v1 - v0) * frac
                rows.append({
                    "date": f"{y}-{q}",
                    "age": a,
                    "population": round(v),
                })
    return rows


def main():
    print("Henter SSB 07459 ...")
    payload = fetch()
    annual = parse(payload)
    print(f"  {len(annual)} (aar, alder)-celler")

    rows = interpolate(annual)
    rows.sort(key=lambda r: (r["date"], r["age"]))

    out = OUTDIR / "ssb_population_by_age_quarterly.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "age", "population"])
        w.writeheader()
        w.writerows(rows)

    print(f"Skrev {len(rows)} rader til {out.name}")
    ages = sorted({r["age"] for r in rows})
    dates = sorted({r["date"] for r in rows})
    print(f"  Aldre: {ages[0]}-{ages[-1]}  ({len(ages)} unike)")
    print(f"  Kvartaler: {dates[0]} til {dates[-1]}")


if __name__ == "__main__":
    main()
