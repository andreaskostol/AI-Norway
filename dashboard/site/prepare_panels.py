"""
Build the data files for the two pages that sit beside the KI-indeks on
kiindeksen.no (Yrker and Utdanning):

  public/data/yrker.json      occupation panel: automation vs augmentation per
                              STYRK-08 occupation across Anthropic Economic
                              Index vintages, each occupation's top tasks and
                              its closest occupations by O*NET work content
  public/data/utdanning.json  education page: per NUS faggruppe (level +
                              two-digit group) the ten most common tasks
                              with exposure and Claude use, and the most
                              common jobs (analysis/07_education/build_majors.py).
                              The institution view (build_institutions.py)
                              is kept as build_institutions_json() for a
                              later, separate analysis; not on the page.
  public/data/vacancies.json  open NAV job ads per occupation, only when
                              data/nav_vacancies/ has a series (see its README)

These panels update on their own cadence (when Anthropic, DBH or NAV
publish), so they are kept apart from prepare_data.py, which runs monthly.

Run:
    python dashboard/site/prepare_panels.py
"""

import csv
import difflib
import json
import os
from collections import defaultdict

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SITE_DIR))
EXPO_DIR = os.path.join(REPO_DIR, "data", "ai_exposure")
EDU_DIR = os.path.join(REPO_DIR, "data", "education_analysis")
OUT_DIR = os.path.join(SITE_DIR, "public", "data")

# Vintage labels. The date is the start of Anthropic's sample window.
VINTAGES = [
    ("claude_ai", "2024-12-01", "des. 2024–jan. 2025", "Dec 2024–Jan 2025",
     "Handa m.fl. (2025), release mars 2025", "Handa et al. (2025), March 2025 release"),
    ("claude_ai", "2025-08-04", "aug. 2025", "Aug 2025", "release september 2025", "September 2025 release"),
    ("claude_ai", "2025-11-13", "nov. 2025", "Nov 2025", "release januar 2026", "January 2026 release"),
    ("claude_ai", "2026-02-05", "feb. 2026", "Feb 2026", "release mars 2026", "March 2026 release"),
    ("api", "2025-08-04", "aug. 2025", "Aug 2025", "release september 2025", "September 2025 release"),
    ("api", "2025-11-13", "nov. 2025", "Nov 2025", "release januar 2026", "January 2026 release"),
    ("api", "2026-02-05", "feb. 2026", "Feb 2026", "release mars 2026", "March 2026 release"),
]


def read_csv(path, encoding="utf-8"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def tkey(s):
    return " ".join((s or "").lower().split())


# ---- O*NET 30.1 task importance: IM (1-5) and RT (share of incumbents the
# task is relevant for), and the task's rank by IM x RT among the occupation's
# rated tasks. Same files and weight as analysis/07_education/build_majors.py.
ONET_DIR = os.path.join(EXPO_DIR, "onet_relational")


def load_onet_task_info():
    rat = defaultdict(dict)
    for r in read_tsv(os.path.join(ONET_DIR, "Task Ratings IM RT.txt")):
        if r["Scale ID"] in ("IM", "RT"):
            rat[(r["O*NET-SOC Code"], r["Task ID"])][r["Scale ID"]] = float(r["Data Value"])
    per_occ = defaultdict(list)
    for r in read_tsv(os.path.join(ONET_DIR, "Task Statements.txt")):
        q = rat.get((r["O*NET-SOC Code"], r["Task ID"]))
        if q and "IM" in q:
            per_occ[r["O*NET-SOC Code"]].append((tkey(r["Task"]), q["IM"], q.get("RT", 100.0)))
    info, by_text, by_occ = {}, defaultdict(list), defaultdict(list)
    for onet, lst in per_occ.items():
        lst.sort(key=lambda x: -(x[1] * x[2]))
        for i, (txt, im, rt) in enumerate(lst, 1):
            info[(onet, txt)] = {"im": round(im, 2), "rt": round(rt, 1), "rk": i, "nt": len(lst)}
            by_text[txt].append((onet, info[(onet, txt)]))
            by_occ[onet].append(txt)
    return info, by_text, by_occ


def onet_task_info(info, by_text, by_occ, soc, text):
    """The AEI task carries a SOC 2010 code (11-1011); O*NET codes are
    11-1011.00 plus specialties. Base code first, then a specialty, then a
    reworded statement in the same occupation (difflib ratio >= 0.9, O*NET
    edits wording between versions), then the same text under any
    occupation (importance averaged, no rank)."""
    txt, base = tkey(text), soc.split(".")[0]
    if (base + ".00", txt) in info:
        return info[(base + ".00", txt)], "exact"
    for onet, d in by_text.get(txt, []):
        if onet.startswith(base + "."):
            return d, "exact"
    best, best_key = 0.0, None
    for onet in by_occ:
        if not onet.startswith(base + "."):
            continue
        for cand in by_occ[onet]:
            r = difflib.SequenceMatcher(None, txt, cand).ratio()
            if r > best:
                best, best_key = r, (onet, cand)
    if best >= 0.9:
        return info[best_key], "fuzzy"
    alts = by_text.get(txt, [])
    if alts:
        return {"im": round(sum(d["im"] for _, d in alts) / len(alts), 2),
                "rt": round(sum(d["rt"] for _, d in alts) / len(alts), 1), "rk": None, "nt": None}, "text"
    return None, "none"


def num(x, nd=4):
    if x in ("", None):
        return None
    return round(float(x), nd)


def intq(x):
    return int(float(x)) if x not in ("", None) else None


# ---------------------------------------------------------------- yrker

def build_yrker():
    """One record per STYRK-08 occupation with every vintage that covers it."""
    measures = read_csv(os.path.join(EXPO_DIR, "styrk08_all_exposure_measures.csv"))
    names_en = {r["styrk08"]: r["name_en"]
                for r in read_csv(os.path.join(EXPO_DIR, "styrk08_names_en.csv"))}
    n_base = {}
    occ_path = os.path.join(OUT_DIR, "occupations.json")
    if os.path.exists(occ_path):
        with open(occ_path, encoding="utf-8") as f:
            for o in json.load(f)["occupations"]:
                n_base[o["code"]] = o["n_base"]

    coll = read_csv(os.path.join(EXPO_DIR, "styrk08_aei_collaboration.csv"))
    tasks = read_csv(os.path.join(EXPO_DIR, "styrk08_aei_tasks.csv"))
    neighbours = defaultdict(list)
    nb_path = os.path.join(EXPO_DIR, "styrk08_task_neighbours.csv")
    if os.path.exists(nb_path):
        for r in read_csv(nb_path):
            if int(r["rank"]) <= 3:
                neighbours[r["styrk08"]].append({
                    "code": r["neighbour"], "sim": num(r["similarity"], 3),
                    "shared": [s for s in r.get("shared_elements", "").split("; ") if s]})

    by_code = defaultdict(dict)
    for r in coll:
        by_code[r["styrk08"]][r["platform"] + "|" + r["date_start"]] = {
            "u": num(r["usage_pct"], 5), "auto": num(r["automation_share"]),
            "aug": num(r["augmentation_share"]), "d": num(r["directive_share"]),
            "fb": num(r["feedback_loop_share"]), "ti": num(r["task_iteration_share"]),
            "va": num(r["validation_share"]), "le": num(r["learning_share"]),
            "n": num(r["n_classified"], 0), "nt": int(r["n_tasks_matched"]),
        }
    # Norwegian task texts when translated (analysis/07_education/translate_tasks.py).
    trans = {}
    tp = os.path.join(EXPO_DIR, "onet_task_translations_no.csv")
    if os.path.exists(tp):
        trans = {" ".join(r["task"].lower().split()): r["task_no"] for r in read_csv(tp) if r.get("task_no")}
    onet_info, onet_by_text, onet_by_occ = load_onet_task_info()
    how = defaultdict(int)
    task_by_code = defaultdict(lambda: defaultdict(list))
    for r in tasks:
        oi, kind = onet_task_info(onet_info, onet_by_text, onet_by_occ, r["soc"], r["task_name"])
        how[kind] += 1
        task_by_code[r["styrk08"]][r["platform"]].append({
            "t": r["task_name"], "t_no": trans.get(" ".join(r["task_name"].lower().split()), ""),
            "soc": r["soc"], "pct": num(r["pct"], 5),
            "n": num(r["n_classified"], 0), "d": num(r["directive_share"]),
            "fb": num(r["feedback_loop_share"]), "ti": num(r["task_iteration_share"]),
            "va": num(r["validation_share"]), "le": num(r["learning_share"]),
            # O*NET importance to the occupation: im 1-5, rt % of incumbents,
            # rk rank of nt tasks by IM x RT (rk/nt None when matched by text only).
            "im": oi["im"] if oi else None, "rt": oi["rt"] if oi else None,
            "rk": oi["rk"] if oi else None, "nt": oi["nt"] if oi else None,
        })
    print("  O*NET importance matched:", dict(how))

    # Task-level five-type shares for every sample, so the page can show a
    # task's change since an earlier sample: the raw release slices (chat and
    # API) plus the Handa vintage. Arrays: [d, fb, ti, va, le, n, usage pct].
    TYPE_COLS = ["directive", "feedback loop", "task iteration", "validation", "learning"]
    REL = os.path.join(EXPO_DIR, "handa", "aei_releases")

    def tkey(s):
        return " ".join(s.lower().split())

    tv = defaultdict(dict)
    for p, d, *_ in VINTAGES:
        path = os.path.join(REL, f"onet_task_collaboration_{p}_{d}.csv")
        upath = os.path.join(REL, f"onet_task_{p}_{d}.csv")
        if not os.path.exists(path):
            continue
        cnt = defaultdict(lambda: defaultdict(float))
        for r in read_csv(path):
            cnt[tkey(r["task_name"])][r["collaboration"]] += float(r["count"] or 0)
        use = {tkey(r["task_name"]): float(r["pct"] or 0) for r in read_csv(upath)} if os.path.exists(upath) else {}
        for t, c in cnt.items():
            n = sum(c[k] for k in TYPE_COLS)
            if n > 0:
                tv[t][p + "|" + d] = [round(c[k] / n, 4) for k in TYPE_COLS] + [int(n), round(use.get(t, 0), 4)]
    hp = os.path.join(EXPO_DIR, "handa", "automation_vs_augmentation_by_task.csv")
    up = os.path.join(EXPO_DIR, "handa", "task_pct_v2.csv")
    if os.path.exists(hp):
        use = {tkey(r["task_name"]): float(r["pct"] or 0) for r in read_csv(up)} if os.path.exists(up) else {}
        for r in read_csv(hp):
            sh = [float(r[k] or 0) for k in ("directive", "feedback_loop", "task_iteration", "validation", "learning")]
            s = sum(sh)
            if s > 0:
                tv[tkey(r["task_name"])]["claude_ai|2024-12-01"] = [round(x / s, 4) for x in sh] + [None, round(use.get(tkey(r["task_name"]), 0), 4)]
    for code_tasks in task_by_code.values():
        for plat_tasks in code_tasks.values():
            for t in plat_tasks:
                t["v"] = tv.get(tkey(t["t"]), {})

    occupations = []
    for m in measures:
        code = m["styrk08"]
        if code not in by_code:
            continue
        occupations.append({
            "code": code, "name": m["styrk08_name"], "name_en": names_en.get(code, ""),
            "n": n_base.get(code), "q": intq(m["eloundou_q"]),
            "q_mouchel": intq(m["mouchel_grounded_q"]),
            "beta": num(m["eloundou_beta"], 3), "mouchel": num(m["mouchel_grounded"], 3),
            "nb": neighbours.get(code, []), "v": by_code[code],
            "tasks": task_by_code.get(code, {}),
        })
    occupations.sort(key=lambda o: o["code"])
    # Neighbours without Claude data are not in `occupations`, but the page
    # still needs their name, size and exposure, otherwise "the three closest"
    # shows two entries for 45 occupations.
    have = {o["code"] for o in occupations}
    referenced = {nb["code"] for o in occupations for nb in o["nb"]}
    extra = {}
    for m in measures:
        code = m["styrk08"]
        if code in have or code not in referenced:
            continue
        extra[code] = {"name": m["styrk08_name"], "name_en": names_en.get(code, ""),
                       "n": n_base.get(code), "q": intq(m["eloundou_q"]),
                       "beta": num(m["eloundou_beta"], 3)}
    vintages = [{"platform": p, "date": d, "key": p + "|" + d, "label": lab,
                 "label_en": lab_en, "source": src, "source_en": src_en}
                for p, d, lab, lab_en, src, src_en in VINTAGES]
    return {"vintages": vintages, "occupations": occupations,
            "n_occupations": len(occupations), "extra": extra}


# ------------------------------------------------------------- utdanning

LEVEL_ORDER = ["Bachelor-nivå", "Master-nivå", "Ph.d.", "Påbygging/fagskole",
               "Videregående avsluttende", "Videregående grunnutdanning"]


def build_utdanning():
    """The study-choice view: data/education_analysis/majors.json, passed
    through as-is (built by analysis/07_education/build_majors.py)."""
    with open(os.path.join(EDU_DIR, "majors.json"), encoding="utf-8") as f:
        return json.load(f)


def build_institutions_json():
    """Institution view (35 institutions from DBH). Taken off the page on
    2026-09-07; kept for a separate analysis later."""
    summary = read_csv(os.path.join(EDU_DIR, "institutions_summary.csv"))
    by_field = read_csv(os.path.join(EDU_DIR, "institutions_by_field.csv"))
    by_level = read_csv(os.path.join(EDU_DIR, "institutions_by_level.csv"))
    top_occ = read_csv(os.path.join(EDU_DIR, "institutions_top_occupations.csv"))
    field_level = read_csv(os.path.join(EDU_DIR, "institutions_by_field_level.csv"))
    trend = read_csv(os.path.join(EDU_DIR, "institutions_trend.csv"))
    groups = read_csv(os.path.join(EDU_DIR, "education_exposure_by_group.csv"))
    nat_top = read_csv(os.path.join(EDU_DIR, "national_field_level_top_occupations.csv"))
    with open(os.path.join(EDU_DIR, "quintile_cuts.json"), encoding="utf-8") as f:
        cuts = json.load(f)

    fields = defaultdict(list)
    for r in by_field:
        fields[r["inst"]].append({"field": r["field"], "n": num(r["graduates"], 0),
                                  "share": num(r["share"])})
    levels = defaultdict(list)
    for r in by_level:
        levels[r["inst"]].append({"level": r["level"], "n": num(r["graduates"], 0),
                                  "share": num(r["share"])})
    tops = defaultdict(lambda: defaultdict(list))
    for r in top_occ:
        tops[r["inst"]][r["cohort"]].append({
            "rank": int(r["rank"]), "code": r["styrk08"], "name": r["styrk08_name"],
            "share": num(r["share"]), "q_v1": intq(r["quintile_v1"]), "q_v2": intq(r["quintile_v2"])})
    fl = defaultdict(list)
    for r in field_level:
        fl[r["inst"]].append({
            "field": r["field"], "level": r["level"], "n": num(r["graduates"], 0),
            "programmes": int(r["programmes"]), "share": num(r["share_of_institution"]),
            "exposure_v1": num(r["exposure_w"]), "exposure_v2": num(r["exposure2_w"]),
            "q5_v1": num(r["share_top5_v1"]), "q5_v2": num(r["share_top5_v2"]),
            "q_v1": [num(r["share_q%d_v1" % i]) for i in range(1, 6)],
            "q_v2": [num(r["share_q%d_v2" % i]) for i in range(1, 6)],
            "top": r["top_occupations"]})
    tr = defaultdict(list)
    for r in trend:
        tr[r["inst"]].append({"year": int(r["year"]), "graduates": num(r["graduates_exact"], 0),
                              "students": num(r["students_autumn_exact"], 0)})

    institutions = []
    for r in summary:
        inst = r["inst"]
        institutions.append({
            "code": inst, "short": r["inst_short"], "name": r["inst_name"], "type": r["inst_type"],
            "year": int(r["year"]), "graduates": num(r["graduates_exact"], 0), "phd": num(r["phd"], 0),
            "programmes": int(r["programmes"]), "students": num(r["students_autumn_exact"], 0),
            "graduates_rows": num(r["graduates_rows"], 0), "coverage": num(r["coverage_profile"]),
            "exposure_v1": num(r["exposure_w"]), "exposure_v2": num(r["exposure2_w"]),
            "exposure_v1_recent": num(r["exposure_w_recent"]),
            "q_v1": [num(r["share_q%d_v1" % i]) for i in range(1, 6)],
            "q_v2": [num(r["share_q%d_v2" % i]) for i in range(1, 6)],
            "share_employed": num(r["share_employed"]), "share_in_education": num(r["share_i_utdanning"]),
            "handa_aug": num(r["handa_augmentation_w"]), "handa_auto": num(r["handa_automation_w"]),
            "share_bachelor": num(r["share_bachelor"]), "share_master": num(r["share_master"]),
            "share_phd": num(r["share_phd"]),
            "fields": sorted(fields[inst], key=lambda x: -x["share"]),
            "levels": sorted(levels[inst], key=lambda x: LEVEL_ORDER.index(x["level"])
                             if x["level"] in LEVEL_ORDER else 99),
            "top_occ": {c: sorted(v, key=lambda x: x["rank"]) for c, v in tops[inst].items()},
            "field_level": sorted(fl[inst], key=lambda x: -x["n"]),
            "trend": sorted(tr[inst], key=lambda x: x["year"]),
        })
    institutions.sort(key=lambda x: -(x["graduates"] or 0))

    def group_rows(kind):
        out = []
        for r in groups:
            if r["group_type"] != kind:
                continue
            rec = {"group": r["group"], "n_codes": int(r["n_codes"]),
                   "n_total": num(r["n_total"], 0), "n_employed": num(r["n_employed"], 0),
                   "share_employed": num(r["share_employed"]),
                   "exposure_v1": num(r["exposure_w"]), "exposure_v2": num(r["exposure2_w"]),
                   "q5_v1": num(r["share_top5_v1"]), "q5_v2": num(r["share_top5_v2"]),
                   "handa_aug": num(r["handa_augmentation_w"]), "handa_auto": num(r["handa_automation_w"])}
            if kind == "level_x_field":
                lvl, fld = r["group"].split(" | ", 1)
                rec["level"], rec["field"] = lvl, fld
            out.append(rec)
        return out

    nat_tops = defaultdict(list)
    for r in nat_top:
        nat_tops[(r["field"], r["level"])].append({
            "rank": int(r["rank"]), "code": r["styrk08"], "name": r["styrk08_name"],
            "share": num(r["share"]), "q_v1": intq(r["quintile_v1"]), "q_v2": intq(r["quintile_v2"])})
    field_level_nat = group_rows("level_x_field")
    for rec in field_level_nat:
        rec["top"] = sorted(nat_tops.get((rec["field"], rec["level"]), []), key=lambda x: x["rank"])

    return {"year": institutions[0]["year"] if institutions else None,
            "n_institutions": len(institutions), "min_graduates": 50,
            "institutions": institutions,
            "national": {"fields": group_rows("field"), "levels": group_rows("level"),
                         "field_level": field_level_nat},
            "level_order": LEVEL_ORDER,
            "quintile_cuts": cuts, "register_vintage": "2024-11-01"}


# ------------------------------------------------------------- vacancies

def build_vacancies():
    """Open NAV job ads per STYRK-08 and snapshot date (data/nav_vacancies/).
    Returns None when no series exists yet; the panel then hides the figure."""
    path = os.path.join(REPO_DIR, "data", "nav_vacancies", "nav_vacancies_by_styrk.csv")
    if not os.path.exists(path):
        return None
    rows = read_csv(path)
    dates = sorted({r["snapshot_date"] for r in rows})
    idx = {d: i for i, d in enumerate(dates)}
    by_code = {}
    for r in rows:
        rec = by_code.setdefault(r["styrk08"], {"ads": [None] * len(dates), "pos": [None] * len(dates),
                                                "new7": [None] * len(dates)})
        i = idx[r["snapshot_date"]]
        rec["ads"][i] = int(r["n_ads"])
        rec["pos"][i] = int(r["n_positions"])
        rec["new7"][i] = int(r["n_ads_new7d"])
    totals = []
    tot_path = os.path.join(REPO_DIR, "data", "nav_vacancies", "nav_vacancies_totals.csv")
    if os.path.exists(tot_path):
        totals = [{"date": r["snapshot_date"], "ads": int(r["n_ads_unique"]),
                   "mapped": int(r["n_ads_mapped"])} for r in read_csv(tot_path)]
    return {"dates": dates, "by_code": by_code, "totals": totals, "source": "arbeidsplassen.nav.no"}


# ------------------------------------------------------------------ main

def write(name, data):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("%-16s %7.0f kB" % (name, os.path.getsize(path) / 1024))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    y = build_yrker()
    write("yrker.json", y)
    print("  occupations:", y["n_occupations"])
    u = build_utdanning()
    write("utdanning.json", u)
    print("  groups:", len(u["groups"]), "| levels:", [l["code"] for l in u["levels"]],
          "| AEI:", u["aei_latest"])
    v = build_vacancies()
    if v:
        write("vacancies.json", v)
        print("  vacancy snapshots:", v["dates"], "codes:", len(v["by_code"]))
    else:
        print("vacancies.json      skipped (no data/nav_vacancies/nav_vacancies_by_styrk.csv yet)")
    # No CSV downloads for Yrker and Utdanning (taken off 2026-09-07): the
    # pages read only the JSON above. The data live in data/ai_exposure/ and
    # data/education_analysis/ for analysis.


if __name__ == "__main__":
    main()
