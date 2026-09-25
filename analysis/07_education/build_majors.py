#!/usr/bin/env python3
"""
Study-choice view for the Utdanning page on kiindeksen.no.

For each NUS2000 faggruppe (level digit + two-digit group, e.g. 641 =
bachelor-nivå, økonomisk-administrative fag): which jobs people with that
education hold, which tasks those jobs consist of, how exposed each task is
to language models, and how Claude is actually used on it.

Chain
  utdanning.no register link, NUS6 x STYRK-08 (residents 20-70, highest
  completed education, Nov 2024), summed to NUS3            -> the jobs
  STYRK-08 -> ISCO-08 -> SOC 2010 -> O*NET-SOC 2019 (the BLS crosswalks used
  by build_eloundou_mapping.py and build_occupation_task_similarity.py)
  O*NET 30.1 Task Statements + Task Ratings: a task's weight inside an
  occupation is importance (IM, 1-5) x relevance (RT, share of incumbents
  who do it)                                                 -> the tasks
  Eloundou et al. (2024) full_labelset.tsv, gpt4_exposure per task:
  E1 = 1 (a language model alone halves the time), E2 = 0.5 (with extra
  software), E0 = 0                                          -> task exposure
  Anthropic Economic Index, task x interaction type, latest sample per
  platform: directive + feedback loop = automation           -> how Claude is used

Task weight for a group = sum over the group's occupations of
  share of the employed in that occupation
  x 1 / number of O*NET occupations the STYRK code maps to
  x the task's share of IM x RT/100 within that O*NET occupation,
so every occupation's tasks sum to its employment share and long O*NET task
lists do not outweigh short ones. The ten tasks with the largest weight are
listed, at most MAX_PER_OCC per occupation so the list spans the common jobs
rather than the one job with the longest task list. The group's task-based
exposure is the weight-weighted mean of the task betas over all its tasks.

Inputs
  <EDUTECH>/data/utdanning_no/links_nus2styrk08*.csv    (17 MB, not in repo; EDUTECH_DIR)
  data/education_analysis/inputs/nus2000_klass.csv     NUS2000 names (SSB KLASS 36)
  data/education_analysis/inputs/styrk08_codes.csv     STYRK-08 names (utdanning.no)
  data/education_analysis/inputs/styrk08_exposure_v2.csv   Eloundou exposure_norm, 0-1
  data/education_analysis/quintile_cuts.json           quintile cuts per measure
  data/ai_exposure/styrk08_all_exposure_measures.csv   Mouchel (v2)
  data/ai_exposure/styrk08_names_en.csv
  data/ai_exposure/styrk08_aei_collaboration.csv       occupation-level automation, latest chat
  data/ai_exposure/onet_relational/Task Statements.txt, Task Ratings IM RT.txt   (O*NET 30.1)
  data/ai_exposure/handa/onet_task_statements.csv      older task texts (for AEI text matching)
  data/ai_exposure/eloundou/full_labelset.tsv
  data/ai_exposure/handa/aei_releases/onet_task[_collaboration]_{platform}_{date}.csv

Outputs (data/education_analysis/)
  majors.json, majors_summary.csv, majors_top_tasks.csv, majors_top_occupations.csv

Run: python analysis/07_education/build_majors.py
"""

import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
E = os.path.join(REPO, "data", "education_analysis")
INP = os.path.join(E, "inputs")
X = os.path.join(REPO, "data", "ai_exposure")
ONET = os.path.join(X, "onet_relational")
REL = os.path.join(X, "handa", "aei_releases")
EDUTECH = os.environ.get("EDUTECH_DIR", os.path.join(
    os.path.expanduser("~"), "Dropbox (Privat)", "AI-research", "Edutech", "education-analysis"))
U = os.path.join(EDUTECH, "data", "utdanning_no")

sys.path.insert(0, os.path.join(REPO, "analysis", "03_mappings"))
from build_eloundou_mapping import (  # noqa: E402
    MANUAL_STYRK_MAP, MANUAL_STYRK_SOC_MAP,
    load_soc_2018_to_2010, load_soc2010_to_isco08, load_styrk08_codes,
)

MIN_EMP_SCORED = 100     # a group needs this many employed with an exposure score
TOP_TASKS = 10
MAX_PER_OCC = 3          # tasks from the same occupation in the top list
TOP_OCC = 10
STATUS = {"9994", "9995", "9996", "9997", "9999", "0000"}
LEVELS = [("6", "Bachelor-nivå", "Bachelor level"), ("7", "Master-nivå", "Master level"),
          ("8", "Ph.d.", "PhD"), ("5", "Påbygging/fagskole", "Vocational college"),
          ("4", "Videregående avsluttende", "Upper secondary, final"),
          ("3", "Videregående grunnutdanning", "Upper secondary, basic")]
FIELD_NAMES = {"0": "Allmenne fag", "1": "Humanistiske og estetiske fag",
               "2": "Lærerutdanninger og pedagogikk", "3": "Samfunnsfag og juridiske fag",
               "4": "Økonomiske og administrative fag", "5": "Naturvitenskap, håndverk og teknikk",
               "6": "Helse-, sosial- og idrettsfag", "7": "Primærnæringsfag",
               "8": "Samferdsel, sikkerhet og service", "9": "Uoppgitt fagfelt"}
TYPES = ["directive", "feedback loop", "task iteration", "validation", "learning"]
TYPE_KEY = {"directive": "d", "feedback loop": "fb", "task iteration": "ti", "validation": "va", "learning": "le"}
BETA = {"E0": 0.0, "E1": 1.0, "E2": 0.5}


def read_csv(path, encoding="utf-8"):
    with open(path, encoding=encoding, newline="") as f:
        return list(csv.DictReader(f))


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def norm_task(s):
    return " ".join((s or "").lower().split())


# ---------------------------------------------------------------- names
klass = read_csv(os.path.join(INP, "nus2000_klass.csv"))
GROUP_NAME = {r["code"]: r["name"] for r in klass if r["level"] == "3"}
OCC_NAME = {r["styrk08"]: r["navn"] for r in read_csv(os.path.join(INP, "styrk08_codes.csv"))}
OCC_NAME_EN = {r["styrk08"]: r["name_en"] for r in read_csv(os.path.join(X, "styrk08_names_en.csv"))}

# ---------------------------------------------------------------- exposure per occupation
expo, expo2 = {}, {}
for r in read_csv(os.path.join(INP, "styrk08_exposure_v2.csv")):
    if r["exposure_norm"] not in ("", None):
        expo[r["styrk08_code"]] = float(r["exposure_norm"])
meas = read_csv(os.path.join(X, "styrk08_all_exposure_measures.csv"))
mou = {r["styrk08"]: float(r["mouchel_grounded"]) for r in meas if r["mouchel_grounded"] not in ("", None)}
MOU_MAX = max(mou.values())
expo2 = {k: v / MOU_MAX for k, v in mou.items()}
with open(os.path.join(E, "quintile_cuts.json"), encoding="utf-8") as f:
    QC = json.load(f)
QCUTS = QC["qcuts"]
TOP5_CUT = {"v1": QCUTS["v1"][3], "v2": QCUTS["v2"][3]}


def quint(v, ver):
    return None if v is None else 1 + sum(v >= c for c in QCUTS[ver])


# occupation-level automation, latest chat sample (Anthropic's bucketing)
occ_auto = {}
aei_occ = read_csv(os.path.join(X, "styrk08_aei_collaboration.csv"))
chat_dates = sorted({r["date_start"] for r in aei_occ if r["platform"] == "claude_ai"})
LATEST = {"claude_ai": chat_dates[-1],
          "api": sorted({r["date_start"] for r in aei_occ if r["platform"] == "api"})[-1]}
for r in aei_occ:
    if r["platform"] == "claude_ai" and r["date_start"] == LATEST["claude_ai"] and r["automation_share"]:
        occ_auto[r["styrk08"]] = float(r["automation_share"])

# ---------------------------------------------------------------- STYRK -> O*NET-SOC 2019
soc18_to_10 = load_soc_2018_to_2010()
soc10_to_18 = collections.defaultdict(set)
for s18, lst in soc18_to_10.items():
    for s10 in lst:
        soc10_to_18[s10].add(s18)
soc10_to_isco, _ = load_soc2010_to_isco08()
styrk_codes = load_styrk08_codes()
soc10_per_styrk = collections.defaultdict(set)
for s10, iscos in soc10_to_isco.items():
    for isco in iscos:
        if isco in styrk_codes:
            soc10_per_styrk[isco].add(s10)
for target, socs in MANUAL_STYRK_SOC_MAP.items():
    soc10_per_styrk[target] = set(socs)
for target, source in MANUAL_STYRK_MAP.items():
    if target not in soc10_per_styrk and source in soc10_per_styrk:
        soc10_per_styrk[target] = set(soc10_per_styrk[source])

# ---------------------------------------------------------------- O*NET tasks
statements = read_tsv(os.path.join(ONET, "Task Statements.txt"))
task_text, tasks_per_onet = {}, collections.defaultdict(list)
for r in statements:
    tid = r["Task ID"]
    task_text[tid] = r["Task"]
    tasks_per_onet[r["O*NET-SOC Code"]].append(tid)
ratings = collections.defaultdict(dict)
for r in read_tsv(os.path.join(ONET, "Task Ratings IM RT.txt")):
    if r["Scale ID"] in ("IM", "RT"):
        ratings[(r["O*NET-SOC Code"], r["Task ID"])][r["Scale ID"]] = float(r["Data Value"])


def task_weight(onet, tid):
    q = ratings.get((onet, tid))
    if not q or "IM" not in q:
        return 0.0
    return q["IM"] * (q.get("RT", 100.0) / 100.0)


# The task's share of the occupation's work: IM x RT over the occupation's sum.
onet_task_sum = {onet: sum(task_weight(onet, t) for t in tids) for onet, tids in tasks_per_onet.items()}


def task_share(onet, tid):
    s = onet_task_sum.get(onet, 0.0)
    return task_weight(onet, tid) / s if s else 0.0


# O*NET-SOC 2019 has specialties under a SOC code (15-1211.01 Health
# Informatics Specialists under 15-1211 Computer Systems Analysts). The
# base code (.00) describes the occupation; specialties are used only when
# there is no base code, otherwise their tasks would outweigh the general ones.
onet_by_s18 = collections.defaultdict(list)
for onet in tasks_per_onet:
    onet_by_s18[onet.split(".")[0]].append(onet)
onet_per_styrk = {}
for styrk, s10s in soc10_per_styrk.items():
    onets = set()
    for s10 in s10s:
        for s18 in soc10_to_18.get(s10, ()):
            cands = onet_by_s18.get(s18, [])
            if s18 + ".00" in cands:
                onets.add(s18 + ".00")
            else:
                onets.update(cands)
    if onets:
        onet_per_styrk[styrk] = sorted(onets)

# Eloundou labels per task id. `label` is the GPT-4 label; `score` is the
# mean beta over the three label sets in the file (human, GPT-4, GPT-4 with
# the alternative rubric), 0-1, and `tq` places that score in the same five
# groups as the occupations (exposure_norm = beta / 0.975, occupation cuts).
label, score, tq = {}, {}, {}
BETA_MAX = 0.975
for r in read_tsv(os.path.join(X, "eloundou", "full_labelset.tsv")):
    tid = r["Task ID"].split(".")[0]
    if r["gpt4_exposure"] in BETA:
        label[tid] = r["gpt4_exposure"]
    vals = [BETA[r[c]] for c in ("human_labels", "gpt4_exposure", "gpt4_exposure_alt_rubric") if r.get(c) in BETA]
    if vals:
        score[tid] = round(sum(vals) / len(vals), 3)
        tq[tid] = quint(score[tid] / BETA_MAX, "v1")

# Norwegian task texts, when the translation file exists (see
# analysis/07_education/translate_tasks.py). Missing rows fall back to English.
TRANS = {}
tp = os.path.join(X, "onet_task_translations_no.csv")
if os.path.exists(tp):
    TRANS = {norm_task(r["task"]): r["task_no"] for r in read_csv(tp) if r.get("task_no")}

# Anthropic per task: latest sample per platform, matched on task text.
# Older task wordings (the 2014-era statements Anthropic used) are matched too.
texts_for_tid = collections.defaultdict(set)
for tid, t in task_text.items():
    texts_for_tid[tid].add(norm_task(t))
for r in read_csv(os.path.join(X, "handa", "onet_task_statements.csv")):
    texts_for_tid[r["Task ID"].split(".")[0]].add(norm_task(r["Task"]))


def load_aei(platform):
    date = LATEST[platform]
    counts = collections.defaultdict(lambda: collections.Counter())
    for r in read_csv(os.path.join(REL, f"onet_task_collaboration_{platform}_{date}.csv")):
        counts[norm_task(r["task_name"])][r["collaboration"]] += float(r["count"] or 0)
    usage = {}
    for r in read_csv(os.path.join(REL, f"onet_task_{platform}_{date}.csv")):
        usage[norm_task(r["task_name"])] = float(r["pct"] or 0)
    out = {}
    for t, c in counts.items():
        n = sum(c[k] for k in TYPES)
        if n <= 0:
            continue
        rec = {TYPE_KEY[k]: round(c[k] / n, 4) for k in TYPES}
        rec["auto"] = round((c["directive"] + c["feedback loop"]) / n, 4)
        rec["n"] = int(n)
        rec["u"] = round(usage.get(t, 0.0), 4)
        out[t] = rec
    return out


AEI = {p: load_aei(p) for p in ("claude_ai", "api")}


def aei_for(tid, platform):
    for t in texts_for_tid.get(tid, ()):
        if t in AEI[platform]:
            return AEI[platform][t]
    return None


# ---------------------------------------------------------------- register link -> NUS3
dist = collections.defaultdict(collections.Counter)
dist13 = collections.defaultdict(collections.Counter)
nus_name, nus_pop = {}, collections.Counter()      # 6-digit names, for the search box
seen = set()
for fn in ("links_nus2styrk08_by_nus.csv", "links_nus2styrk08.csv"):
    p = os.path.join(U, fn)
    if not os.path.exists(p):
        continue
    rows = [r for r in read_csv(p) if r["retning"] == "nus2styrk08" and ";" not in r["nus"]]
    here = set(r["nus"] for r in rows)
    for r in rows:
        if r["nus"] in seen:
            continue
        g = r["nus"][:3]
        n = int(float(r["antall_personer"] or 0))
        dist[g][r["styrk08"]] += n
        dist13[g][r["styrk08"]] += int(float(r["antall_13"] or 0))
        nus_name[r["nus"]] = (r["nus_navn"], r["nus_kortnavn"])
        nus_pop[r["nus"]] += n
    seen |= here
NUS_EN = {}
p = os.path.join(INP, "nus_codes_utdanning_no.csv")
if os.path.exists(p):
    NUS_EN = {r["nus_kode"]: r["nus_navn_en"] for r in read_csv(p)}
if not dist:
    raise SystemExit(f"No register link files under {U}. Set EDUTECH_DIR.")
REGISTER_VINTAGE = "2024-11-01"


def occ_rows(counter, n):
    emp = {k: v for k, v in counter.items() if k not in STATUS}
    tot = sum(emp.values())
    out = []
    if not tot:
        return out
    for k, v in sorted(emp.items(), key=lambda kv: -kv[1])[:n]:
        out.append({"code": k, "name": OCC_NAME.get(k, k), "name_en": OCC_NAME_EN.get(k, ""),
                    "share": round(v / tot, 4), "e_v1": expo.get(k), "q_v1": quint(expo.get(k), "v1"),
                    "q_v2": quint(expo2.get(k), "v2"),
                    "auto": occ_auto.get(k)})
    return out


groups, task_rows, occ_out = [], [], []
for g in sorted(dist):
    lvl = g[0]
    if lvl not in {l[0] for l in LEVELS} or g not in GROUP_NAME:
        continue
    c = dist[g]
    tot = sum(c.values())
    emp = {k: v for k, v in c.items() if k not in STATUS}
    n_emp = sum(emp.values())
    scored = {k: v for k, v in emp.items() if k in expo}
    n_sc = sum(scored.values())
    if n_sc < MIN_EMP_SCORED:
        continue
    scored2 = {k: v for k, v in emp.items() if k in expo2}
    n_sc2 = sum(scored2.values())
    # occupation-level exposure and quintiles, as elsewhere on the site
    rec = {
        "code": g, "level": lvl, "field": g[1], "name": GROUP_NAME[g],
        "field_name": FIELD_NAMES.get(g[1], ""),
        "n_total": tot, "n_employed": n_emp, "share_employed": round(n_emp / tot, 4),
        "share_studying": round(c.get("9997", 0) / tot, 4),
        "n_occ": len(emp),
        "exposure_v1": round(sum(expo[k] * v for k, v in scored.items()) / n_sc, 4),
        "exposure_v2": round(sum(expo2[k] * v for k, v in scored2.items()) / n_sc2, 4) if n_sc2 else None,
        "q5_v1": round(sum(v for k, v in scored.items() if expo[k] >= TOP5_CUT["v1"]) / n_sc, 4),
        "q5_v2": round(sum(v for k, v in scored2.items() if expo2[k] >= TOP5_CUT["v2"]) / n_sc2, 4) if n_sc2 else None,
        "q_v1": [round(sum(v for k, v in scored.items() if quint(expo[k], "v1") == q) / n_sc, 4) for q in range(1, 6)],
        "q_v2": [round(sum(v for k, v in scored2.items() if quint(expo2[k], "v2") == q) / n_sc2, 4) for q in range(1, 6)] if n_sc2 else None,
    }
    # occupation-level automation, weighted by employment share
    pairs = [(occ_auto[k], v) for k, v in emp.items() if k in occ_auto]
    w = sum(v for _, v in pairs)
    rec["automation"] = round(sum(a * v for a, v in pairs) / w, 4) if w else None
    rec["automation_coverage"] = round(w / n_emp, 4) if n_emp else None

    # tasks: weight = occupation share x 1/n_onet x IM x RT
    tw = collections.Counter()
    main_occ = collections.defaultdict(collections.Counter)
    task_onet = {}
    covered = 0
    for k, v in emp.items():
        onets = onet_per_styrk.get(k)
        if not onets:
            continue
        covered += v
        s = v / n_emp / len(onets)
        for onet in onets:
            for tid in tasks_per_onet[onet]:
                wt = task_share(onet, tid) * s
                if wt <= 0:
                    continue
                tw[tid] += wt
                main_occ[tid][k] += wt
                if tid not in task_onet or wt > task_onet[tid][1]:
                    task_onet[tid] = (onet, wt)
    total_w = sum(tw.values())
    lab_w = [(BETA[label[t]], wv) for t, wv in tw.items() if t in label]
    rec["task_coverage"] = round(covered / n_emp, 4) if n_emp else None
    rec["task_exposure"] = round(sum(b * wv for b, wv in lab_w) / sum(wv for _, wv in lab_w), 4) if lab_w else None
    # task-level automation, weighted by task weight x Claude usage
    au = [(aei_for(t, "claude_ai"), wv) for t, wv in tw.items()]
    au = [(a["auto"], wv * a["u"]) for a, wv in au if a]
    rec["task_automation"] = round(sum(a * wv for a, wv in au) / sum(wv for _, wv in au), 4) if au and sum(wv for _, wv in au) > 0 else None
    tasks = []
    per_occ = collections.Counter()
    for tid, wv in tw.most_common():
        if len(tasks) >= TOP_TASKS:
            break
        occ_code = main_occ[tid].most_common(1)[0][0]
        if per_occ[occ_code] >= MAX_PER_OCC:
            continue
        per_occ[occ_code] += 1
        t = {"id": tid, "text": task_text[tid], "text_no": TRANS.get(norm_task(task_text[tid]), ""),
             "onet": task_onet[tid][0],
             "occ_code": occ_code, "occ_name": OCC_NAME.get(occ_code, occ_code),
             "occ_name_en": OCC_NAME_EN.get(occ_code, ""),
             # every occupation in the group that lists the task, by its share of the task's weight
             "occs": [{"c": k, "n": OCC_NAME.get(k, k), "n_en": OCC_NAME_EN.get(k, ""), "s": round(w2 / wv, 3)}
                      for k, w2 in main_occ[tid].most_common(6)],
             "n_occ": len(main_occ[tid]),
             "w": round(wv / total_w, 4) if total_w else None,
             "label": label.get(tid), "beta": BETA.get(label.get(tid)),
             "score": score.get(tid), "q": tq.get(tid),
             "chat": aei_for(tid, "claude_ai"), "api": aei_for(tid, "api")}
        tasks.append(t)
        task_rows.append({"group": g, "level": lvl, "group_name": GROUP_NAME[g], "rank": len(tasks),
                          "task_id": tid, "task": task_text[tid], "onet_soc": t["onet"],
                          "styrk08": occ_code, "styrk08_name": t["occ_name"], "weight_share": t["w"],
                          "eloundou_label": t["label"], "eloundou_beta": t["beta"],
                          "chat_usage_pct": t["chat"]["u"] if t["chat"] else "",
                          "chat_n_classified": t["chat"]["n"] if t["chat"] else "",
                          "chat_automation_share": t["chat"]["auto"] if t["chat"] else "",
                          "api_automation_share": t["api"]["auto"] if t["api"] else ""})
    rec["tasks"] = tasks
    rec["occ_all"] = occ_rows(c, TOP_OCC)
    rec["occ_recent"] = occ_rows(dist13[g], TOP_OCC)
    rec["n_recent"] = sum(v for k, v in dist13[g].items() if k not in STATUS)
    for cohort, rows in (("all", rec["occ_all"]), ("recent", rec["occ_recent"])):
        for i, o in enumerate(rows, 1):
            occ_out.append({"group": g, "level": lvl, "group_name": GROUP_NAME[g], "cohort": cohort, "rank": i,
                            "styrk08": o["code"], "styrk08_name": o["name"], "share": o["share"],
                            "quintile_v1": o["q_v1"], "quintile_v2": o["q_v2"], "automation_chat": o["auto"]})
    groups.append(rec)

groups.sort(key=lambda r: (r["level"], -r["n_total"]))
# Search index: every 6-digit education with at least 20 persons whose group
# is on the page, so "master i rettsvitenskap" or "siviløkonom" finds a group.
group_codes = {g["code"] for g in groups}
names = []
for code, (nm, short) in nus_name.items():
    if nus_pop[code] < 20 or code[:3] not in group_codes:
        continue
    names.append({"c": code, "g": code[:3], "n": nm, "s": short if short and short != nm else "",
                  "e": NUS_EN.get(code, ""), "p": nus_pop[code]})
names.sort(key=lambda x: -x["p"])
out = {"register_vintage": REGISTER_VINTAGE, "onet_version": "30.1",
       "aei_latest": LATEST, "min_employed_scored": MIN_EMP_SCORED,
       "quintile_cuts": QCUTS, "top5_cut": TOP5_CUT,
       "levels": [{"code": c, "name": n, "name_en": e} for c, n, e in LEVELS],
       "groups": groups, "names": names}
with open(os.path.join(E, "majors.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)


def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(E, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


write_csv("majors_summary.csv", [{k: v for k, v in g.items() if k not in ("tasks", "occ_all", "occ_recent", "q_v1", "q_v2")}
                                 | {"q_v1": json.dumps(g["q_v1"]), "q_v2": json.dumps(g["q_v2"])} for g in groups])
write_csv("majors_top_tasks.csv", task_rows)
write_csv("majors_top_occupations.csv", occ_out)

n_task_lab = sum(1 for g in groups for t in g["tasks"] if t["label"])
n_task_ai = sum(1 for g in groups for t in g["tasks"] if t["chat"])
n_tasks = sum(len(g["tasks"]) for g in groups)
print(f"groups: {len(groups)} | STYRK with O*NET tasks: {len(onet_per_styrk)} | "
      f"top tasks: {n_tasks}, with Eloundou label {n_task_lab}, with Claude data {n_task_ai}")
for g in groups:
    if g["code"] in ("641", "654", "661", "622", "737"):
        print(g["code"], g["name"], "n", g["n_total"], "Q5", g["q5_v1"], "task_exp", g["task_exposure"],
              "auto", g["automation"], "task_auto", g["task_automation"], "cov", g["task_coverage"])
        for t in g["tasks"][:3]:
            print("   ", t["label"], t["w"], (t["chat"] or {}).get("auto"), t["occ_name"], "|", t["text"][:70])
