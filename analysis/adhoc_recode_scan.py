"""
Skann for mulige omkodingshendelser i yrkeskodene.

Kriterier (jf. 4311->3313 mai 2025):
  1. Stort en-maaneds-sprang RELATIVT til kodens eget sesongmoenster
     (samme kalendermaaned andre aar).
  2. Varig nivaaskift: snittet 3 mnd etter vs 3 mnd foer flytter seg
     i samme retning (omkoding reverserer ikke; glitcher gjoer).
  3. Par: en annen kode hopper motsatt vei samme maaned med
     sammenlignbar stoerrelse, og summen av de to er glatt.
"""
import os
import numpy as np
import pandas as pd

BASE = os.path.dirname(__file__)
DATA = os.path.join(BASE, "..", "microdata-output",
                    "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")

d = pd.read_csv(DATA, dtype={"yrke4": str, "alder_gr": str, "sekt": int})
d = d[(d["variable"] == "count") & (d["sekt"] == 2)
      & (d["alder_gr"].isin(["1", "2", "3", "4"]))]

tot = d.groupby(["yrke4", "date"], as_index=False)["value"].sum()
tot = tot.sort_values(["yrke4", "date"]).reset_index(drop=True)
tot["lch"] = np.log(tot["value"]).groupby(tot["yrke4"]).diff()
tot["calmon"] = tot["date"].str[5:7]

# Sesongjustert endring: trekk fra median log-endring for samme
# kalendermaaned innen koden (leave-one-out unoedvendig, median robust)
med = tot.groupby(["yrke4", "calmon"])["lch"].transform("median")
tot["adj"] = tot["lch"] - med
sd = tot.groupby("yrke4")["adj"].transform(
    lambda s: 1.4826 * np.nanmedian(np.abs(s - np.nanmedian(s))) + 0.004)
tot["z"] = tot["adj"] / sd
tot["prev"] = tot.groupby("yrke4")["value"].shift(1)
tot["diff"] = tot["value"] - tot["prev"]

# Varighet: snitt 3 mnd etter vs 3 mnd foer spranget
g = tot.groupby("yrke4")["value"]
tot["pre3"] = (g.shift(1) + g.shift(2) + g.shift(3)) / 3
tot["post3"] = (tot["value"] + g.shift(-1) + g.shift(-2)) / 3
tot["shift3"] = np.log(tot["post3"] / tot["pre3"])

cand = tot[(tot["z"].abs() >= 6) & (tot["diff"].abs() >= 150)
           & (tot["adj"].abs() >= 0.05)
           & (np.sign(tot["shift3"]) == np.sign(tot["diff"]))
           & (tot["shift3"].abs() >= 0.6 * tot["adj"].abs())].copy()

print("=== Varige, sesongkorrigerte sprang (sum 21-60, privat) ===")
print(f"{'yrke':>5} {'maaned':>8} {'fra':>7} {'til':>7} {'diff':>6} "
      f"{'adj%':>6} {'z':>6} {'3mnd%':>6}")
for _, r in cand.sort_values(["date", "yrke4"]).iterrows():
    print(f"{r['yrke4']:>5} {r['date'][:7]:>8} {int(r['prev']):>7} "
          f"{int(r['value']):>7} {int(r['diff']):>+6} "
          f"{100*r['adj']:>+6.1f} {r['z']:>+6.1f} {100*r['shift3']:>+6.1f}")

# Par med glatt sum
print("\n=== Omkodingspar: motsatte sprang, glatt sum ===")
piv = tot.pivot(index="date", columns="yrke4", values="value")
for mo, grp in cand.groupby(tot["date"]):
    ups = grp[grp["diff"] > 0]
    downs = grp[grp["diff"] < 0]
    for _, u in ups.iterrows():
        for _, dn in downs.iterrows():
            ratio = -u["diff"] / dn["diff"]
            if not (0.5 <= ratio <= 2.0):
                continue
            pair = piv[u["yrke4"]] + piv[dn["yrke4"]]
            lp = np.log(pair).diff()
            jump = lp.loc[mo]
            typ = 1.4826 * np.nanmedian(np.abs(lp - np.nanmedian(lp)))
            smooth = abs(jump) < 2 * typ
            print(f"{mo[:7]}: {dn['yrke4']} {int(dn['diff']):+} <-> "
                  f"{u['yrke4']} {int(u['diff']):+}  ratio {ratio:.2f}, "
                  f"sum-sprang {100*jump:+.1f}% "
                  f"({'GLATT' if smooth else 'ikke glatt'})")

# Til slutt: vis tidsserien rundt hendelsen for kandidatene
print("\n=== Serier rundt kandidat-hendelsene (+/- 4 mnd) ===")
shown = set()
for _, r in cand.sort_values(["date", "yrke4"]).iterrows():
    key = (r["yrke4"], r["date"][:7])
    if key in shown:
        continue
    shown.add(key)
    s = piv[r["yrke4"]]
    i = list(s.index).index(r["date"])
    lo, hi = max(0, i - 4), min(len(s), i + 5)
    vals = " ".join(f"{s.index[k][2:7]}:{int(s.iloc[k])}"
                    for k in range(lo, hi))
    print(f"{r['yrke4']}: {vals}")
