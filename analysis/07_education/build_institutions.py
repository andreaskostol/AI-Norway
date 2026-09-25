#!/usr/bin/env python3
"""
Institution view: graduates per programme (DBH) x the job profile and AI
exposure of the programme's education code.

Repo version of Edutech/education-analysis/scripts/03_institutions.py,
generalised from six institutions to every institution in
data/education_analysis/dbh/institutions.csv, with two extra aggregates for
the education panel: institution x field x level, and national field x level
top occupations.

Inputs
  data/education_analysis/dbh/               from analysis/07_education/fetch_dbh.py
  data/education_analysis/education_exposure_by_nus.csv     per NUS code (Edutech 02)
  data/education_analysis/education_exposure_by_group.csv   level, field, level_x_field, nus4
  data/education_analysis/inputs/styrk08_exposure_v2.csv    dashboard exposure per STYRK-08 (0-1)
  data/education_analysis/inputs/styrk08_codes.csv          utdanning.no's STYRK-08 names
  data/ai_exposure/styrk08_all_exposure_measures.csv        Mouchel, Handa
  <EDUTECH>/data/utdanning_no/links_nus2styrk08*.csv         full occupation distribution per NUS
                                                            code (17 MB each, not in the repo;
                                                            EDUTECH_DIR env var or the Dropbox path)

Outputs (data/education_analysis/)
  programs_all.csv, institutions_summary.csv, institutions_by_level.csv,
  institutions_by_field.csv, institutions_top_occupations.csv,
  institutions_by_field_level.csv, institutions_trend.csv,
  national_field_level_top_occupations.csv, quintile_cuts.json

Rules (unchanged from the Edutech pipeline)
  * A programme inherits the national job profile of its NUS code: residents
    20-70 with that code as highest completed education (utdanning.no register
    link, Nov 2024). If the code's employed-and-scored population is below
    MIN_CELL, the 4-digit NUS group is used instead (profile_source).
  * PhDs have no NUS code in DBH and get the national profile of all NUS
    level-8 codes.
  * Levels follow DBH's Nivåkode: LN group = bachelor-nivå, HN/MP group =
    master-nivå, FU = ph.d.
  * Institution totals in the summary are DBH's exact totals; programme rows
    give the mix. Programme rows sum lower than the totals because DBH
    suppresses small cells.
"""

import collections
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
E = os.path.join(REPO, "data", "education_analysis")
D = os.path.join(E, "dbh")
INP = os.path.join(E, "inputs")
EDUTECH = os.environ.get("EDUTECH_DIR", os.path.join(
    os.path.expanduser("~"), "Dropbox (Privat)", "AI-research", "Edutech", "education-analysis"))
U = os.path.join(EDUTECH, "data", "utdanning_no")
MIN_CELL = 100
LOWER = {"AR", "B3", "B4", "HK", "YU", "LN"}
HIGHER = {"M2", "ME", "MX", "HN", "M5", "PR"}
FIELD_NAMES = {"0": "Allmenne fag", "1": "Humanistiske og estetiske fag",
               "2": "Lærerutdanninger og pedagogikk", "3": "Samfunnsfag og juridiske fag",
               "4": "Økonomiske og administrative fag", "5": "Naturvitenskap, håndverk og teknikk",
               "6": "Helse-, sosial- og idrettsfag", "7": "Primærnæringsfag",
               "8": "Samferdsel, sikkerhet og service", "9": "Uoppgitt fagfelt"}
STATUS = {"9994", "9995", "9996", "9997", "9999", "0000"}


def level_of(niva, nus):
    if niva in LOWER:
        return "Bachelor-nivå"
    if niva in HIGHER:
        return "Master-nivå"
    if niva == "FU":
        return "Ph.d."
    return {"6": "Bachelor-nivå", "7": "Master-nivå", "8": "Ph.d."}.get(nus[:1], "Annet")


def fnum(x):
    try:
        return float(x) if x not in (None, "", "NA", "nan") else None
    except ValueError:
        return None


def rows_of(path, **kw):
    with open(path, encoding=kw.get("encoding", "utf-8-sig"), newline="") as f:
        return list(csv.DictReader(f))


# ---------- DBH
inst_list = rows_of(os.path.join(D, "institutions.csv"))
SHORT = {r["institusjonskode"]: (r["kortnavn"] or r["institusjonskode"]) for r in inst_list}
INST_TYPE = {r["institusjonskode"]: r["institusjonstype"] for r in inst_list}
grads = []
for r in rows_of(os.path.join(D, "graduates_by_program.csv")):
    grads.append({"inst": r["institusjonskode"], "inst_name": r["institusjonsnavn"], "year": int(r["aar"]),
                  "prog": r["studieprogramkode"], "prog_name": r["studieprogramnavn"],
                  "nus": r["nus_kode"].strip(), "niva": r["nivaakode"], "niva_name": r["nivaanavn"],
                  "studium": r.get("studiumnavn", ""), "n": fnum(r["kandidater_totalt"]) or 0.0})
for r in rows_of(os.path.join(D, "graduates_phd_by_program.csv")):
    grads.append({"inst": r["institusjonskode"], "inst_name": r["institusjonsnavn"], "year": int(r["aar"]),
                  "prog": r["studieprogramkode"], "prog_name": r["studieprogramnavn"], "nus": "",
                  "niva": "FU", "niva_name": "Forskerutdanning", "studium": "Ph.d.",
                  "n": fnum(r["kandidater_totalt"]) or 0.0})
exact = collections.defaultdict(dict)
for r in json.load(open(os.path.join(D, "raw", "104_kandidater_totaler.json"), encoding="utf-8")):
    if "Institusjonskode" in r:
        exact[r["Institusjonskode"]][int(r["Årstall"])] = int(r["Antall totalt"])
students_exact = collections.defaultdict(collections.Counter)
for r in json.load(open(os.path.join(D, "raw", "123_registrerte_totaler.json"), encoding="utf-8")):
    if "Institusjonskode" in r:
        students_exact[r["Institusjonskode"]][int(r["Årstall"])] += int(r["Antall totalt"])
students = []
for r in rows_of(os.path.join(D, "students_by_program.csv")):
    if r["nivaakode"].upper() == "FU":
        continue
    students.append({"inst": r["institusjonskode"], "year": int(r["aar"]), "prog": r["studieprogramkode"],
                     "n": fnum(r["studenter_totalt"]) or 0.0})
LATEST = max(g["year"] for g in grads)
print("latest year:", LATEST, "| institutions:", len(SHORT))

# ---------- exposure per occupation, quintile cuts
nusrows = {r["nus_code"]: r for r in rows_of(os.path.join(E, "education_exposure_by_nus.csv"))}
styrk = {r["styrk08"]: r for r in rows_of(os.path.join(INP, "styrk08_codes.csv"))}
expo = {r["styrk08_code"]: fnum(r["exposure_norm"])
        for r in rows_of(os.path.join(INP, "styrk08_exposure_v2.csv"))}
meas = {r["styrk08"]: {k: fnum(r[k]) for k in ("handa_augmentation", "handa_automation", "mouchel_grounded")}
        for r in rows_of(os.path.join(REPO, "data", "ai_exposure", "styrk08_all_exposure_measures.csv"))}
_mou = {k: v["mouchel_grounded"] for k, v in meas.items() if v["mouchel_grounded"] is not None}
MOU_MAX = max(_mou.values())
expo2 = {k: v / MOU_MAX for k, v in _mou.items()}


def _qcuts(vals):
    vals = sorted(vals)
    return [vals[int(len(vals) * k)] for k in (0.2, 0.4, 0.6, 0.8)]


QCUTS = {"v1": _qcuts(v for v in expo.values() if v is not None), "v2": _qcuts(expo2.values())}


def quint(v, ver):
    return None if v is None else 1 + sum(v >= c for c in QCUTS[ver])


TOP5_CUT = {"v1": QCUTS["v1"][3], "v2": QCUTS["v2"][3]}

# ---------- full occupation distribution per NUS code (register link)
dist = collections.defaultdict(collections.Counter)
dist13 = collections.defaultdict(collections.Counter)
seen = set()
for fn in ("links_nus2styrk08_by_nus.csv", "links_nus2styrk08.csv"):
    p = os.path.join(U, fn)
    if not os.path.exists(p):
        continue
    rows = [r for r in csv.DictReader(open(p, encoding="utf-8"))
            if r["retning"] == "nus2styrk08" and ";" not in r["nus"]]
    here = set(r["nus"] for r in rows)
    for r in rows:
        if r["nus"] in seen:
            continue
        dist[r["nus"]][r["styrk08"]] += int(float(r["antall_personer"] or 0))
        dist13[r["nus"]][r["styrk08"]] += int(float(r["antall_13"] or 0))
    seen |= here
if not dist:
    raise SystemExit(f"No register link files under {U}. Set EDUTECH_DIR.")


def profile_from_counter(c, c13=None):
    tot = sum(c.values())
    if not tot:
        return None
    emp = {k: v for k, v in c.items() if k not in STATUS}
    n_emp = sum(emp.values())
    scored = {k: v for k, v in emp.items() if expo.get(k) is not None}
    n_sc = sum(scored.values())
    if not n_sc:
        return None
    scored2 = {k: v for k, v in emp.items() if expo2.get(k) is not None}
    n_sc2 = sum(scored2.values())
    out = {"n_pop": tot, "n_emp_scored": n_sc,
           "exposure": sum(expo[k] * v for k, v in scored.items()) / n_sc,
           "top5_v1": sum(v for k, v in scored.items() if expo[k] >= TOP5_CUT["v1"]) / n_sc,
           "qdist_v1": [sum(v for k, v in scored.items() if quint(expo[k], "v1") == q) / n_sc for q in range(1, 6)],
           "qdist_v2": [sum(v for k, v in scored2.items() if quint(expo2[k], "v2") == q) / n_sc2 for q in range(1, 6)] if n_sc2 else None,
           "exposure2": sum(expo2[k] * v for k, v in scored2.items()) / n_sc2 if n_sc2 else None,
           "top5_v2": sum(v for k, v in scored2.items() if expo2[k] >= TOP5_CUT["v2"]) / n_sc2 if n_sc2 else None,
           "employed": n_emp / tot, "studying": c.get("9997", 0) / tot,
           "occ": {k: v / n_emp for k, v in emp.items()} if n_emp else {}}
    for m in ("handa_augmentation", "handa_automation"):
        pairs = [(meas[k][m], v) for k, v in emp.items() if k in meas and meas[k][m] is not None]
        w = sum(v for _, v in pairs)
        out[m] = sum(a * v for a, v in pairs) / w if w else None
    if c13:
        emp13 = {k: v for k, v in c13.items() if k not in STATUS}
        n13 = sum(v for k, v in emp13.items() if expo.get(k) is not None)
        out["recent_exposure"] = sum(expo[k] * v for k, v in emp13.items() if expo.get(k) is not None) / n13 if n13 else None
        n13_all = sum(emp13.values())
        out["occ_recent"] = {k: v / n13_all for k, v in emp13.items()} if n13_all else {}
    else:
        out["recent_exposure"] = None
        out["occ_recent"] = {}
    return out


EMPTY = {"source": "none", "n_pop": None, "n_emp_scored": None, "exposure": None, "employed": None,
         "studying": None, "occ": {}, "handa_augmentation": None, "handa_automation": None,
         "recent_exposure": None, "occ_recent": {}, "top5_v1": None, "exposure2": None,
         "top5_v2": None, "qdist_v1": None, "qdist_v2": None}
dist4 = collections.defaultdict(collections.Counter)
dist4_13 = collections.defaultdict(collections.Counter)
dist8, dist8_13 = collections.Counter(), collections.Counter()
for code, c in dist.items():
    for k, v in c.items():
        dist4[code[:4]][k] += v
    for k, v in dist13[code].items():
        dist4_13[code[:4]][k] += v
    if code.startswith("8"):
        for k, v in c.items():
            dist8[k] += v
        for k, v in dist13[code].items():
            dist8_13[k] += v
PHD_PROFILE = profile_from_counter(dist8, dist8_13)
cache = {}


def profile_for(nus, niva):
    key = (nus, niva)
    if key in cache:
        return cache[key]
    if niva == "FU" or not nus:
        res = dict(PHD_PROFILE, source="phd_national")
    else:
        p6 = profile_from_counter(dist.get(nus, collections.Counter()), dist13.get(nus))
        if p6 and p6["n_emp_scored"] >= MIN_CELL:
            res = dict(p6, source="nus6")
        else:
            p4 = profile_from_counter(dist4.get(nus[:4], collections.Counter()), dist4_13.get(nus[:4]))
            if p4 and p4["n_emp_scored"] >= MIN_CELL:
                res = dict(p4, source="nus4 (small cell)" if p6 else "nus4 (no cell)")
            elif p6:
                res = dict(p6, source="nus6 (small cell)")
            else:
                res = dict(EMPTY)
    cache[key] = res
    return res


# ---------- programme rows, latest year
stud_latest = collections.defaultdict(float)
for s in students:
    if s["year"] == LATEST:
        stud_latest[(s["inst"], s["prog"])] += s["n"]
prow = []
for g in grads:
    if g["year"] != LATEST or g["n"] <= 0 or g["inst"] not in SHORT:
        continue
    pf = profile_for(g["nus"], g["niva"])
    tops = sorted(pf["occ"].items(), key=lambda x: -x[1])[:5]
    row = {"inst": g["inst"], "inst_short": SHORT[g["inst"]], "inst_name": g["inst_name"], "year": g["year"],
           "prog": g["prog"], "prog_name": g["prog_name"], "nus": g["nus"],
           "nus_name": nusrows.get(g["nus"], {}).get("nus_name", "") if g["nus"] else "Ph.d.",
           "niva": g["niva"], "niva_name": g["niva_name"], "level": level_of(g["niva"], g["nus"]),
           "field": FIELD_NAMES.get(g["nus"][1:2], "") if g["nus"] else "Ph.d.", "studium": g["studium"],
           "graduates": g["n"], "students_autumn": stud_latest.get((g["inst"], g["prog"])),
           "profile_source": pf["source"], "register_population": pf["n_pop"],
           "exposure_w": pf["exposure"], "share_employed": pf["employed"], "share_i_utdanning": pf["studying"],
           "handa_augmentation_w": pf["handa_augmentation"], "handa_automation_w": pf["handa_automation"],
           "exposure_w_recent": pf["recent_exposure"], "share_top5_v1": pf["top5_v1"],
           "exposure2_w": pf["exposure2"], "share_top5_v2": pf["top5_v2"],
           "top_occupations": "; ".join(f"{styrk.get(k, {}).get('navn', k)} ({v:.0%})" for k, v in tops),
           "_occ": pf["occ"], "_occ_recent": pf["occ_recent"]}
    for q in range(1, 6):
        row[f"share_q{q}_v1"] = pf["qdist_v1"][q - 1] if pf["qdist_v1"] else None
        row[f"share_q{q}_v2"] = pf["qdist_v2"][q - 1] if pf["qdist_v2"] else None
    prow.append(row)
prow.sort(key=lambda r: (r["inst"], -r["graduates"]))


def write(path, rows, drop=("_occ", "_occ_recent")):
    if not rows:
        print("nothing to write:", path)
        return
    keys = [k for k in rows[0].keys() if k not in drop]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else (f"{r[k]:.6f}" if isinstance(r[k], float) else r[k]))
                        for k in keys})


write(os.path.join(E, "programs_all.csv"), prow)


def wavg(rows, key, wkey="graduates"):
    pairs = [(r[key], r[wkey]) for r in rows if r.get(key) is not None]
    w = sum(x for _, x in pairs)
    return (sum(v * x for v, x in pairs) / w if w else None), w


def aggregate(rows):
    """Graduate-weighted exposure, quintile shares and top occupations for a set of programme rows."""
    n = sum(r["graduates"] for r in rows)
    out = {"graduates_rows": n, "programmes": len(rows)}
    for key in ("exposure_w", "exposure2_w", "share_top5_v1", "share_top5_v2", "share_employed",
                "share_i_utdanning", "handa_augmentation_w", "handa_automation_w", "exposure_w_recent"):
        out[key] = wavg(rows, key)[0]
    for q in range(1, 6):
        out[f"share_q{q}_v1"] = wavg(rows, f"share_q{q}_v1")[0]
        out[f"share_q{q}_v2"] = wavg(rows, f"share_q{q}_v2")[0]
    out["coverage_profile"] = wavg(rows, "exposure_w")[1] / n if n else None
    dest, dest_r = collections.Counter(), collections.Counter()
    wd = wr = 0.0
    for r in rows:
        if r["_occ"]:
            wd += r["graduates"]
            for k, v in r["_occ"].items():
                dest[k] += v * r["graduates"]
        if r["_occ_recent"]:
            wr += r["graduates"]
            for k, v in r["_occ_recent"].items():
                dest_r[k] += v * r["graduates"]
    out["_dest"] = (dest, wd)
    out["_dest_recent"] = (dest_r, wr)
    return out


def top_rows(dest, ww, n=15):
    rows = []
    for rank, (k, v) in enumerate(sorted(dest.items(), key=lambda x: -x[1])[:n], 1):
        rows.append({"rank": rank, "styrk08": k, "styrk08_name": styrk.get(k, {}).get("navn", k),
                     "share": v / ww if ww else None, "exposure_norm": expo.get(k),
                     "exposure2_norm": expo2.get(k), "quintile_v1": quint(expo.get(k), "v1"),
                     "quintile_v2": quint(expo2.get(k), "v2")})
    return rows


# ---------- institution aggregates
summary, by_level, by_field, by_field_level, top_occ = [], [], [], [], []
for inst in sorted(set(r["inst"] for r in prow), key=lambda i: -exact[i].get(LATEST, 0)):
    rows = [r for r in prow if r["inst"] == inst]
    n_rows = sum(r["graduates"] for r in rows)
    agg = aggregate(rows)
    lv, fd = collections.Counter(), collections.Counter()
    for r in rows:
        lv[r["level"]] += r["graduates"]
        fd[r["field"] or "Ukjent"] += r["graduates"]
    s = {"inst": inst, "inst_short": SHORT[inst], "inst_name": rows[0]["inst_name"],
         "inst_type": INST_TYPE.get(inst, ""), "year": LATEST,
         "graduates_exact": exact[inst].get(LATEST), "phd": lv.get("Ph.d.", 0),
         "students_autumn_exact": students_exact[inst].get(LATEST)}
    s.update({k: v for k, v in agg.items() if not k.startswith("_")})
    s["share_bachelor"] = lv.get("Bachelor-nivå", 0) / n_rows
    s["share_master"] = lv.get("Master-nivå", 0) / n_rows
    s["share_phd"] = lv.get("Ph.d.", 0) / n_rows
    summary.append(s)
    for k, v in lv.items():
        by_level.append({"inst": inst, "inst_short": SHORT[inst], "level": k, "graduates": v, "share": v / n_rows})
    for k, v in fd.items():
        by_field.append({"inst": inst, "inst_short": SHORT[inst], "field": k, "graduates": v, "share": v / n_rows})
    for cohort, key in (("all", "_dest"), ("recent", "_dest_recent")):
        for t in top_rows(*agg[key]):
            top_occ.append({"inst": inst, "inst_short": SHORT[inst], "cohort": cohort, **t})
    # institution x field x level
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["field"] or "Ukjent", r["level"])].append(r)
    for (field, level), grp in sorted(groups.items()):
        a = aggregate(grp)
        top = top_rows(*a["_dest"], n=5)
        by_field_level.append({"inst": inst, "inst_short": SHORT[inst], "field": field, "level": level,
                               "graduates": a["graduates_rows"], "programmes": a["programmes"],
                               "share_of_institution": a["graduates_rows"] / n_rows,
                               "exposure_w": a["exposure_w"], "exposure2_w": a["exposure2_w"],
                               "share_top5_v1": a["share_top5_v1"], "share_top5_v2": a["share_top5_v2"],
                               **{f"share_q{q}_v1": a[f"share_q{q}_v1"] for q in range(1, 6)},
                               **{f"share_q{q}_v2": a[f"share_q{q}_v2"] for q in range(1, 6)},
                               "top_occupations": "; ".join(f"{t['styrk08_name']} ({t['share']:.0%})" for t in top),
                               "top_codes": ";".join(t["styrk08"] for t in top)})

write(os.path.join(E, "institutions_summary.csv"), summary)
write(os.path.join(E, "institutions_by_level.csv"), by_level)
write(os.path.join(E, "institutions_by_field.csv"), by_field)
write(os.path.join(E, "institutions_top_occupations.csv"), top_occ)
write(os.path.join(E, "institutions_by_field_level.csv"), by_field_level)
trend = [{"inst": i, "inst_short": SHORT[i], "year": y, "graduates_exact": v,
          "students_autumn_exact": students_exact[i].get(y)}
         for i in SHORT for y, v in sorted(exact[i].items())]
write(os.path.join(E, "institutions_trend.csv"), trend)

# ---------- national field x level: top occupations from the NUS-level register distributions
nat = []
groups = collections.defaultdict(collections.Counter)
pop = collections.Counter()
for nus, c in dist.items():
    r = nusrows.get(nus)
    if not r:
        continue
    key = (r["field_name"], r["level_name"])
    emp = {k: v for k, v in c.items() if k not in STATUS}
    for k, v in emp.items():
        groups[key][k] += v
    pop[key] += sum(emp.values())
for (field, level), dest in sorted(groups.items()):
    for t in top_rows(dest, pop[(field, level)], n=10):
        nat.append({"field": field, "level": level, "n_employed": pop[(field, level)], **t})
write(os.path.join(E, "national_field_level_top_occupations.csv"), nat)

json.dump({"qcuts": QCUTS, "top5_cut": TOP5_CUT, "mou_max": MOU_MAX, "min_cell": MIN_CELL,
           "latest_year": LATEST},
          open(os.path.join(E, "quintile_cuts.json"), "w", encoding="utf-8"))
for s in summary[:8]:
    print(f'{s["inst_short"]:8} n={s["graduates_exact"]:>6} v1={s["exposure_w"]:.3f} q5={s["share_q5_v1"]:.2f}')
print("institutions:", len(summary), "| programmes:", len(prow), "| field x level rows:", len(by_field_level))
src = collections.Counter(r["profile_source"] for r in prow)
print("profile sources:", dict(src))
