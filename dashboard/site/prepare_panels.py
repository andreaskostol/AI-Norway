"""
Build the data files for the three panels that sit beside the KI-indeks on
kiindeksen.no ("Arbeidsmarkedet"):

  public/data/yrker.json      occupation panel: automation vs augmentation per
                              STYRK-08 occupation across Anthropic Economic
                              Index vintages, plus each occupation's top tasks
  public/data/utdanning.json  education panel: institutions, fields, levels
                              and top occupations (Edutech pipeline output
                              copied to data/education_analysis/)
  public/data/bruk.json       cross-provider usage: Norway vs comparison
                              countries in the Anthropic country files

These panels update on their own cadence (when Anthropic or DBH publish),
so they are kept apart from prepare_data.py, which runs every month.

Inputs are all in the repo; see the loader docstrings. Run:
    python dashboard/site/prepare_panels.py
"""

import csv
import json
import os
from collections import defaultdict

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SITE_DIR))
EXPO_DIR = os.path.join(REPO_DIR, "data", "ai_exposure")
EDU_DIR = os.path.join(REPO_DIR, "data", "education_analysis")
USE_DIR = os.path.join(REPO_DIR, "data", "ai_usage_cross_platform")
REL_DIR = os.path.join(EXPO_DIR, "handa", "aei_releases")
OUT_DIR = os.path.join(SITE_DIR, "public", "data")

# Comparison countries shown on the usage panel (ISO alpha-3), Norway first.
COUNTRIES = ["NOR", "SWE", "DNK", "FIN", "ISL", "NLD", "DEU", "GBR", "CHE", "USA"]
COUNTRY_NAMES_NO = {
    "NOR": "Norge", "SWE": "Sverige", "DNK": "Danmark", "FIN": "Finland",
    "ISL": "Island", "NLD": "Nederland", "DEU": "Tyskland",
    "GBR": "Storbritannia", "CHE": "Sveits", "USA": "USA",
}

# Vintage labels. The date is the start of Anthropic's sample window.
VINTAGES = [
    ("claude_ai", "2024-12-01", "des. 2024–jan. 2025", "Dec 2024–Jan 2025",
     "Handa m.fl. (2025), release mars 2025"),
    ("claude_ai", "2025-08-04", "aug. 2025", "Aug 2025", "release september 2025"),
    ("claude_ai", "2025-11-13", "nov. 2025", "Nov 2025", "release januar 2026"),
    ("claude_ai", "2026-02-05", "feb. 2026", "Feb 2026", "release mars 2026"),
    ("api", "2025-08-04", "aug. 2025", "Aug 2025", "release september 2025"),
    ("api", "2025-11-13", "nov. 2025", "Nov 2025", "release januar 2026"),
    ("api", "2026-02-05", "feb. 2026", "Feb 2026", "release mars 2026"),
]


def read_csv(path, **kw):
    with open(path, encoding=kw.pop("encoding", "utf-8"), newline="") as f:
        return list(csv.DictReader(f))


def num(x, nd=4):
    if x in ("", None):
        return None
    return round(float(x), nd)


# ---------------------------------------------------------------- yrker

def build_yrker():
    """One record per STYRK-08 occupation with every vintage that covers it."""
    measures = read_csv(os.path.join(EXPO_DIR, "styrk08_all_exposure_measures.csv"))
    names_en = {r["styrk08"]: r["name_en"]
                for r in read_csv(os.path.join(EXPO_DIR, "styrk08_names_en.csv"))}
    # Employment (Nov 2022 headcount, private sector 21-60) from the
    # occupation selector's file, when it has been built.
    n_base = {}
    occ_path = os.path.join(OUT_DIR, "occupations.json")
    if os.path.exists(occ_path):
        with open(occ_path, encoding="utf-8") as f:
            for o in json.load(f)["occupations"]:
                n_base[o["code"]] = o["n_base"]

    coll = read_csv(os.path.join(EXPO_DIR, "styrk08_aei_collaboration.csv"))
    tasks = read_csv(os.path.join(EXPO_DIR, "styrk08_aei_tasks.csv"))
    # Closest occupations by O*NET work content (build_occupation_task_similarity.py).
    neighbours = defaultdict(list)
    nb_path = os.path.join(EXPO_DIR, "styrk08_task_neighbours.csv")
    if os.path.exists(nb_path):
        for r in read_csv(nb_path):
            if int(r["rank"]) <= 3:
                neighbours[r["styrk08"]].append({"code": r["neighbour"],
                                                 "sim": num(r["similarity"], 3)})

    by_code = defaultdict(dict)
    for r in coll:
        key = r["platform"] + "|" + r["date_start"]
        by_code[r["styrk08"]][key] = {
            "u": num(r["usage_pct"], 5),
            "auto": num(r["automation_share"]),
            "aug": num(r["augmentation_share"]),
            "d": num(r["directive_share"]),
            "fb": num(r["feedback_loop_share"]),
            "ti": num(r["task_iteration_share"]),
            "va": num(r["validation_share"]),
            "le": num(r["learning_share"]),
            "n": num(r["n_classified"], 0),
            "nt": int(r["n_tasks_matched"]),
        }
    task_by_code = defaultdict(lambda: defaultdict(list))
    for r in tasks:
        task_by_code[r["styrk08"]][r["platform"]].append({
            "t": r["task_name"], "soc": r["soc"], "pct": num(r["pct"], 5),
            "n": num(r["n_classified"], 0),
            "d": num(r["directive_share"]), "fb": num(r["feedback_loop_share"]),
            "ti": num(r["task_iteration_share"]), "va": num(r["validation_share"]),
            "le": num(r["learning_share"]),
        })

    occupations = []
    for m in measures:
        code = m["styrk08"]
        if code not in by_code:
            continue
        occupations.append({
            "code": code,
            "name": m["styrk08_name"],
            "name_en": names_en.get(code, ""),
            "n": n_base.get(code),
            "q": int(float(m["eloundou_q"])) if m["eloundou_q"] else None,
            "q_mouchel": int(float(m["mouchel_grounded_q"])) if m["mouchel_grounded_q"] else None,
            "beta": num(m["eloundou_beta"], 3),
            "mouchel": num(m["mouchel_grounded"], 3),
            "nb": neighbours.get(code, []),
            "v": by_code[code],
            "tasks": task_by_code.get(code, {}),
        })
    occupations.sort(key=lambda o: o["code"])

    src_en = {"release mars 2025": "March 2025 release",
              "release september 2025": "September 2025 release",
              "release januar 2026": "January 2026 release",
              "release mars 2026": "March 2026 release"}
    vintages = [{"platform": p, "date": d, "key": p + "|" + d,
                 "label": lab, "label_en": lab_en, "source": src,
                 "source_en": src.replace("Handa m.fl. (2025), ", "Handa et al. (2025), ")
                 .replace("release mars 2025", src_en["release mars 2025"])
                 .replace("release september 2025", src_en["release september 2025"])
                 .replace("release januar 2026", src_en["release januar 2026"])
                 .replace("release mars 2026", src_en["release mars 2026"])}
                for p, d, lab, lab_en, src in VINTAGES]
    return {"vintages": vintages, "occupations": occupations,
            "n_occupations": len(occupations)}


# ------------------------------------------------------------- utdanning

def build_utdanning():
    summary = read_csv(os.path.join(EDU_DIR, "institutions_summary.csv"))
    by_field = read_csv(os.path.join(EDU_DIR, "institutions_by_field.csv"))
    by_level = read_csv(os.path.join(EDU_DIR, "institutions_by_level.csv"))
    top_occ = read_csv(os.path.join(EDU_DIR, "institutions_top_occupations.csv"))
    groups = read_csv(os.path.join(EDU_DIR, "education_exposure_by_group.csv"))
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
            "share": num(r["share"]),
            "q_v1": int(float(r["quintile_v1"])) if r["quintile_v1"] else None,
            "q_v2": int(float(r["quintile_v2"])) if r["quintile_v2"] else None,
        })

    institutions = []
    for r in summary:
        inst = r["inst"]
        institutions.append({
            "code": inst, "short": r["inst_short"], "name": r["inst_name"],
            "year": int(r["year"]),
            "graduates": num(r["graduates_exact"], 0), "phd": num(r["phd"], 0),
            "programmes": int(r["programmes"]),
            "students": num(r["students_autumn_exact"], 0),
            "exposure_v1": num(r["exposure_w"]), "exposure_v2": num(r["exposure2_w"]),
            "exposure_v1_recent": num(r["exposure_w_recent"]),
            "exposure_v2_recent": num(r["exposure2_w_recent"]),
            "q_v1": [num(r["share_q%d_v1" % i]) for i in range(1, 6)],
            "q_v2": [num(r["share_q%d_v2" % i]) for i in range(1, 6)],
            "share_employed": num(r["share_employed"]),
            "share_in_education": num(r["share_i_utdanning"]),
            "handa_aug": num(r["handa_augmentation_w"]),
            "handa_auto": num(r["handa_automation_w"]),
            "share_bachelor": num(r["share_bachelor"]),
            "share_master": num(r["share_master"]),
            "share_phd": num(r["share_phd"]),
            "share_econ_admin": num(r["share_econ_admin"]),
            "fields": sorted(fields[inst], key=lambda x: -x["share"]),
            "levels": levels[inst],
            "top_occ": {c: sorted(v, key=lambda x: x["rank"]) for c, v in tops[inst].items()},
        })
    institutions.sort(key=lambda x: -x["exposure_v1"])

    def group_rows(kind):
        out = []
        for r in groups:
            if r["group_type"] != kind:
                continue
            out.append({
                "group": r["group"], "n_codes": int(r["n_codes"]),
                "n_total": num(r["n_total"], 0), "n_employed": num(r["n_employed"], 0),
                "share_employed": num(r["share_employed"]),
                "exposure_v1": num(r["exposure_w"]), "exposure_v2": num(r["exposure2_w"]),
                "share_q5_v1": num(r["share_top5_v1"]), "share_q5_v2": num(r["share_top5_v2"]),
                "handa_aug": num(r["handa_augmentation_w"]),
                "handa_auto": num(r["handa_automation_w"]),
            })
        return out

    return {"year": institutions[0]["year"] if institutions else None,
            "institutions": institutions,
            "national": {"fields": group_rows("field"), "levels": group_rows("level")},
            "quintile_cuts": cuts,
            "register_vintage": "2024-11-01"}


# ------------------------------------------------------------------ bruk

def build_bruk():
    iso = {r["iso_alpha_2"]: r["iso_alpha_3"]
           for r in read_csv(os.path.join(USE_DIR, "iso_country_codes.csv"))}
    pop = {r["iso_alpha_3"]: float(r["working_age_pop"])
           for r in read_csv(os.path.join(USE_DIR, "working_age_pop_2024_country.csv"))}
    world_pop = sum(pop.values())

    series = []
    # Weekly samples from the raw releases (Aug 2025, Nov 2025, Feb 2026).
    for date in ["2025-08-04", "2025-11-13", "2026-02-05"]:
        usage = {}
        for r in read_csv(os.path.join(REL_DIR, "usage_by_country_claude_ai_%s.csv" % date)):
            a3 = iso.get(r["geo_id"])
            if a3 in COUNTRIES and r["usage_pct"]:
                usage[a3] = float(r["usage_pct"])
        collab = defaultdict(dict)
        for r in read_csv(os.path.join(REL_DIR,
                                       "collaboration_by_country_claude_ai_%s.csv" % date)):
            a3 = iso.get(r["geo_id"])
            if a3 in COUNTRIES and r["pct"]:
                collab[a3][r["collaboration"]] = float(r["pct"])
        by_country = {}
        for a3 in COUNTRIES:
            if a3 not in usage:
                continue
            c = collab.get(a3, {})
            classified = sum(c.get(k, 0.0) for k in
                             ["directive", "feedback loop", "task iteration",
                              "validation", "learning"])
            # Only the raw usage share is kept for the weekly samples.
            # Anthropic's per-capita index (AUI) is published only in the
            # monthly country files and uses a population base we cannot
            # reproduce exactly (our recomputation lands 25-30 % lower), so
            # the panel shows the AUI only where Anthropic has published it.
            rec = {"usage_pct": round(usage[a3], 4)}
            if classified > 0:
                rec.update({
                    "automation": round((c.get("directive", 0) + c.get("feedback loop", 0))
                                        / classified * 100, 1),
                    "augmentation": round((c.get("task iteration", 0) + c.get("validation", 0)
                                           + c.get("learning", 0)) / classified * 100, 1),
                    "directive": round(c.get("directive", 0) / classified * 100, 1),
                    "feedback_loop": round(c.get("feedback loop", 0) / classified * 100, 1),
                    "task_iteration": round(c.get("task iteration", 0) / classified * 100, 1),
                    "validation": round(c.get("validation", 0) / classified * 100, 1),
                    "learning": round(c.get("learning", 0) / classified * 100, 1),
                })
            by_country[a3] = rec
        series.append({"date": date, "window": "uke", "platform": "claude_ai",
                       "by_country": by_country})

    # Monthly country files from the June 2026 release (Apr and May 2026).
    monthly = defaultdict(dict)
    for r in read_csv(os.path.join(USE_DIR, "anthropic_aei_country_usage_2026-04_2026-05.csv")):
        a3 = r["country_code"]
        if a3 not in COUNTRIES:
            continue
        monthly[r["month"]][a3] = {
            "usage_pct": num(r["usage_pct"]), "aui": num(r["usage_per_capita_index"], 2),
            "work": num(r["use_case_work_pct"], 1), "personal": num(r["use_case_personal_pct"], 1),
            "coursework": num(r["use_case_coursework_pct"], 1),
            "automation": num(r["collaboration_bucket_automation_pct"], 1),
            "augmentation": num(r["collaboration_bucket_augmentation_pct"], 1),
            "autonomy": num(r["ai_autonomy_mean"], 2),
        }
    for month in sorted(monthly):
        series.append({"date": month, "window": "måned", "platform": "claude_ai",
                       "by_country": monthly[month]})

    countries = [{"a3": a3, "name": COUNTRY_NAMES_NO[a3], "pop": pop.get(a3)}
                 for a3 in COUNTRIES]
    return {"countries": countries, "series": series,
            "world_working_age_pop": round(world_pop)}


# ------------------------------------------------------------- vacancies

def build_vacancies():
    """Open NAV job ads per STYRK-08 and snapshot date (data/nav_vacancies/).

    Written by dashboard/collect_nav_vacancies.py, or delivered in the same
    format by the collecting agent. Returns None when no series exists yet,
    and the panel then hides the vacancy figure.
    """
    path = os.path.join(REPO_DIR, "data", "nav_vacancies", "nav_vacancies_by_styrk.csv")
    if not os.path.exists(path):
        return None
    rows = read_csv(path)
    dates = sorted({r["snapshot_date"] for r in rows})
    idx = {d: i for i, d in enumerate(dates)}
    by_code = {}
    for r in rows:
        rec = by_code.setdefault(r["styrk08"], {"ads": [None] * len(dates),
                                                "pos": [None] * len(dates),
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
    return {"dates": dates, "by_code": by_code, "totals": totals,
            "source": "arbeidsplassen.nav.no"}


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
    print("  institutions:", [i["short"] for i in u["institutions"]])
    b = build_bruk()
    write("bruk.json", b)
    print("  usage series:", [s["date"] for s in b["series"]])
    v = build_vacancies()
    if v:
        write("vacancies.json", v)
        print("  vacancy snapshots:", v["dates"], "codes:", len(v["by_code"]))
    else:
        print("vacancies.json      skipped (no data/nav_vacancies/nav_vacancies_by_styrk.csv yet)")
    # Downloadable copies of the occupation table for the panel's data section.
    dl = os.path.join(OUT_DIR, "panels")
    os.makedirs(dl, exist_ok=True)
    for src in ["styrk08_aei_collaboration.csv", "styrk08_aei_tasks.csv"]:
        with open(os.path.join(EXPO_DIR, src), encoding="utf-8") as fi, \
                open(os.path.join(dl, src), "w", encoding="utf-8") as fo:
            fo.write(fi.read())
    with open(os.path.join(EDU_DIR, "institutions_summary.csv"), encoding="utf-8") as fi, \
            open(os.path.join(dl, "institutions_summary.csv"), "w", encoding="utf-8") as fo:
        fo.write(fi.read())
    with open(os.path.join(USE_DIR, "anthropic_aei_country_usage_2026-04_2026-05.csv"),
              encoding="utf-8") as fi, \
            open(os.path.join(dl, "anthropic_aei_country_usage_2026-04_2026-05.csv"), "w",
                 encoding="utf-8") as fo:
        fo.write(fi.read())


if __name__ == "__main__":
    main()
