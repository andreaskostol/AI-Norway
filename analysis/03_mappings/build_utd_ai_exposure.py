"""
Bygger AI-eksponering per utd_gr fra Kostols utdanningsdata.

Leser: data/ai_exposure/kostol_education_exposure.csv (7246 NUS-koder)
Mapper: NUS 1.siffer (nivaa) + 2.siffer (fagfelt) -> utd_gr (vaar koding)
Aggregerer: mean_exposure per utd_gr, vektet med n_styrk_with_exposure

Output: data/ai_exposure/utd_gr_ai_exposure.csv

utd_gr-koding:
  0   = lav (NUS < 3, dvs foerste siffer 0-2, + uoppgitt 9)
  10-19 = VGS (NUS 3-4), fagfelt = 2.siffer (0-9)
  20-29 = bachelor (NUS 5-6), fagfelt = 2.siffer
  30-39 = master+ (NUS 7-8), fagfelt = 2.siffer
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KOSTOL = ROOT / "data" / "ai_exposure" / "kostol_education_exposure.csv"
OUT = ROOT / "data" / "ai_exposure" / "utd_gr_ai_exposure.csv"

NUS_FAGFELT_LABELS = {
    0: "Almenne fag",
    1: "Humanistiske og estetiske fag",
    2: "Laererutd. og pedagogikk",
    3: "Samfunnsfag og juridiske fag",
    4: "Oekonomiske og adm. fag",
    5: "Naturvit., haandverk, teknikk",
    6: "Helse-, sosial- og idrettsfag",
    7: "Primaernaeringsfag",
    8: "Samferdsels- og sikkerhetsfag",
    9: "Andre/uoppgitte fag",
}

UTD_LEV_LABELS = {
    0: "Lav (<VGS)",
    1: "VGS",
    2: "Bachelor",
    3: "Master+",
}


def nus_to_utd_gr(nus_code: str):
    if len(nus_code) < 2:
        return 0
    nivaa = int(nus_code[0])
    fagfelt = int(nus_code[1])
    if nivaa <= 2 or nivaa == 9:
        return 0
    if nivaa <= 4:
        lev = 1
    elif nivaa <= 6:
        lev = 2
    else:
        lev = 3
    return lev * 10 + fagfelt


def main():
    # Accumulate weighted sum per utd_gr
    sum_exp = {}
    sum_wt = {}
    count = {}

    with open(KOSTOL, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            nus = r["nus_code"]
            exp = r["mean_exposure"]
            n = r["n_styrk_with_exposure"]
            if not exp or not n:
                continue
            try:
                exp_val = float(exp)
                n_val = int(n)
            except ValueError:
                continue
            if n_val == 0:
                continue
            # Kun nivaa 5 (enkeltutdanninger) for aa unngaa dobbeltelling
            if r["level"] != "5":
                continue
            g = nus_to_utd_gr(nus)
            sum_exp[g] = sum_exp.get(g, 0.0) + exp_val * n_val
            sum_wt[g] = sum_wt.get(g, 0) + n_val
            count[g] = count.get(g, 0) + 1

    rows = []
    for g in sorted(sum_exp.keys()):
        lev = g // 10
        fag = g % 10
        if g == 0:
            label = UTD_LEV_LABELS[0]
        else:
            label = f"{UTD_LEV_LABELS[lev]}, {NUS_FAGFELT_LABELS[fag]}"
        avg = sum_exp[g] / sum_wt[g]
        rows.append({
            "utd_gr": g,
            "utd_label": label,
            "ai_exposure": round(avg, 4),
            "n_nus_codes": count[g],
            "n_styrk_total": sum_wt[g],
        })

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["utd_gr", "utd_label", "ai_exposure",
                                          "n_nus_codes", "n_styrk_total"])
        w.writeheader()
        w.writerows(rows)

    print(f"Saved {len(rows)} utd_gr groups to {OUT}")
    print()
    for r in rows:
        print(f"  {r['utd_gr']:>2}  {r['ai_exposure']:.3f}  {r['utd_label']}")


if __name__ == "__main__":
    main()
