"""
Bygger justeringsfaktorer for komposisjonsskift innen grove aldersgrupper.

Input:
  microdata-output/03_syss_alder_2020_2026_parsed.csv  (sysselsatte per 1-aarig alder, kvartalsvis)
  data/macro/ssb_population_by_age_quarterly.csv       (bosatte per 1-aarig alder, kvartalsvis)

Logikk:
  1. For hver (kvartal, alder): rate = sysselsatte / bosatte.
  2. For hver grov aldersgruppe g og kvartal t:
       raa(g,t)  = sum_a(syss_a) / sum_a(pop_a)               [kvartalets egen aldersmiks]
       std(g,t)  = sum_a(rate_a,t * w_a),  w_a = pop_a,2019Q1 / sum(pop_a,2019Q1)
                                                              [fast 2019Q1-aldersmiks]
       f(g,t)    = std(g,t) / raa(g,t)
  3. Skriver ut tabell (kvartal, gruppe, raa_rate, std_rate, factor) som
     kan multipliseres paa yrkesrater i etterfoelgende analyser.

Aldersgrupper foelger CLAUDE.md (1=<=21, ..., 9=70+).

Output:
  microdata-output/03_age_adjustment_2020_2026.csv
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYSS = ROOT / "microdata-output" / "03_syss_alder_2020_2026_parsed.csv"
POP = ROOT / "data" / "macro" / "ssb_population_by_age_quarterly.csv"
OUT = ROOT / "microdata-output" / "03_age_adjustment_2020_2026.csv"

REF_QUARTER = "2021-Q1"


def alder_gr(a: int) -> int:
    if a <= 21:
        return 1
    if a <= 25:
        return 2
    if a <= 30:
        return 3
    if a <= 34:
        return 4
    if a <= 40:
        return 5
    if a <= 49:
        return 6
    if a <= 59:
        return 7
    if a <= 69:
        return 8
    return 9


def date_to_quarter(date: str) -> str:
    # 2020-01-16 -> 2020-Q1, -04 -> Q2, -07 -> Q3, -10 -> Q4
    y, m, _ = date.split("-")
    q = (int(m) - 1) // 3 + 1
    return f"{y}-Q{q}"


def load_syss():
    """Returner dict[(quarter, alder_int)] = sysselsatte (kun sysselsatt==1)."""
    out = {}
    with open(SYSS, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["sysselsatt"] != "1":
                continue
            try:
                a = int(r["alder"])
            except ValueError:
                continue
            if a < 0:
                continue
            q = date_to_quarter(r["date"])
            out[(q, a)] = int(r["n"])
    return out


def load_pop():
    """Returner dict[(quarter, alder_int)] = bosatte."""
    out = {}
    with open(POP, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                a = int(r["age"])
            except ValueError:
                continue
            out[(r["date"], a)] = int(r["population"])
    return out


def main():
    syss = load_syss()
    pop = load_pop()

    # Aldersuniverset i syss-fila
    syss_quarters = sorted({q for (q, _) in syss.keys()})
    syss_ages = sorted({a for (_, a) in syss.keys()})

    # Aldere som finnes i begge kilder, kappet til pop sin maks alder
    pop_max_age = max(a for (_, a) in pop.keys())
    ages = [a for a in syss_ages if a <= pop_max_age]

    # Referansevekter fra REF_QUARTER, per grovgruppe
    ref_pop_by_age = {a: pop.get((REF_QUARTER, a), 0) for a in ages}
    ref_pop_by_group = {}
    for a in ages:
        g = alder_gr(a)
        ref_pop_by_group[g] = ref_pop_by_group.get(g, 0) + ref_pop_by_age[a]

    rows = []
    for q in syss_quarters:
        # Aggreger raa-tellinger og std-rater per grovgruppe
        raa_syss = {}
        raa_pop = {}
        std_num = {}  # sum_a w_a * rate_a
        for a in ages:
            s = syss.get((q, a), 0)
            p = pop.get((q, a), 0)
            if p == 0:
                continue
            g = alder_gr(a)
            raa_syss[g] = raa_syss.get(g, 0) + s
            raa_pop[g] = raa_pop.get(g, 0) + p
            w = ref_pop_by_age[a] / ref_pop_by_group[g] if ref_pop_by_group[g] else 0
            rate_a = s / p
            std_num[g] = std_num.get(g, 0) + w * rate_a

        for g in sorted(raa_pop.keys()):
            raa = raa_syss[g] / raa_pop[g]
            std = std_num[g]
            factor = std / raa if raa > 0 else float("nan")
            rows.append({
                "quarter": q,
                "alder_gr": g,
                "raa_rate": round(raa, 6),
                "std_rate": round(std, 6),
                "factor": round(factor, 6),
            })

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["quarter", "alder_gr", "raa_rate", "std_rate", "factor"])
        w.writeheader()
        w.writerows(rows)

    print(f"Saved {len(rows)} rows to {OUT}")
    print(f"  Quarters: {syss_quarters[0]} to {syss_quarters[-1]}")
    print(f"  Reference quarter for weights: {REF_QUARTER}")
    # Spotcheck
    sample = [r for r in rows if r["quarter"] in (syss_quarters[0], syss_quarters[-1])]
    print("\nFirst/last quarter factors:")
    for r in sample:
        print(f"  {r['quarter']} g={r['alder_gr']}  raa={r['raa_rate']:.4f}  std={r['std_rate']:.4f}  f={r['factor']:.4f}")


if __name__ == "__main__":
    main()
