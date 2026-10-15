"""
build_data.py

Builds the data file for the usage animations (Claude conversations -> O*NET tasks -> Norwegian occupations):

  data/bruk-anthropic.js   window.BRUK_ANTHROPIC

Everything is read from the project files in this run: the task x interaction-type tables for the three
counted Claude.ai vintages (Aug 2025, Nov 2025, Feb 2026), the March 2025 task shares, the O*NET task list
behind the Anthropic tables, the BLS SOC 2010 -> ISCO-08 crosswalk, the STYRK-08 code list and the finished
measurement and grouping files. The chain is rebuilt with the rules of
analysis/03_mappings/build_aei_collaboration_mapping.py, and the pooling, threshold and terciles with the
rules of analysis/03_mappings/build_automation_groups.py. Both are checked against the finished files, so
the animation shows the numbers the measure is actually built from.

The crosswalk loaders come from analysis/03_mappings/build_handa_mapping.py, and the Norwegian task labels
and crosswalk titles from slides/mapping-pipeline/build_data.py, so the two presentations use the same
names.

Usage (from anywhere):
    python slides/bruk-pipeline/build_data.py
"""

import importlib.util                         # load the sibling build scripts by path
import os                                     # paths
import re                                     # sample windows from the extract script
import sys                                    # console encoding on Windows
from collections import defaultdict           # accumulate counts along the chain

import numpy as np                            # means and correlations
import pandas as pd                           # tables
from scipy import stats                       # Spearman correlation

sys.stdout.reconfigure(encoding="utf-8")      # Norwegian characters in the console

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
D = os.path.join(REPO, "data", "ai_exposure")
REL = os.path.join(D, "handa", "aei_releases")
MAPS = os.path.join(REPO, "analysis", "03_mappings")


def load_module(name, path):
    """Import a script by path, without running its main()."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


handa = load_module("build_handa_mapping", os.path.join(MAPS, "build_handa_mapping.py"))
mp = load_module("mapping_pipeline_build_data", os.path.join(REPO, "slides", "mapping-pipeline", "build_data.py"))

PLATFORM = "claude_ai"
POOL_DATES = ["2025-08-04", "2025-11-13", "2026-02-05"]    # the three counted vintages (build_automation_groups.py)
MARCH_KEY = "2024-12-01"     # key of the March 2025 vintage in the measurement file: an identifier, not the sample period
TYPES = ["directive", "feedback loop", "task iteration", "validation", "learning"]
AUTOMATE = TYPES[:2]
MIN_N = 100                                                 # threshold on the pooled count (build_automation_groups.py)
SHORT = {"directive": "d", "feedback loop": "fb", "task iteration": "ti", "validation": "va", "learning": "le",
         "none": "no", "not_classified": "nc"}

EXAMPLE_ONET = mp.EXAMPLE_ONET                # 27-3031.00 Public Relations Specialists
EXAMPLE_STYRK = mp.EXAMPLE_STYRK              # 2432 Informasjonsrådgivere
# The O*NET list behind the Anthropic tables is older than the one Eloundou used. 17 of the 18 tasks have
# the same id. The 18th, 20556 "Update and maintain content posted on the Web", is the earlier wording of
# 23951 "Post and update content on the company's Web site and social media outlets" in O*NET 27.2.
OLD_TO_NEW_ID = {20556: 23951}
TASK_NO = dict(mp.TASK_NO)
TASK_NO[20556] = "Oppdatere innhold på nettsiden"

DEFINITION = "2512"                           # Programvareutviklere: directive only against Anthropic's rule
UNSTABLE = "5223"                             # Butikkmedarbeidere: one weekly sample is not enough
UNKNOWN = "1411"                              # Hotellsjefer: every task filtered in March 2025, share unknown
MERGE_STYRK = mp.MERGE_STYRK                  # 7411 Elektrikere: several SOC codes become one STYRK code
FAN_SOC10 = mp.FAN_SOC10                      # 11-1021: one SOC code becomes several STYRK codes
EXCEPTIONS = mp.EXCEPTIONS                    # 2223, 2224, 2267, 2269
RESULT_ROWS = ["2432", "2512", "4222", "7411", "5223", "2262"]


def r6(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 6)


# ---------------------------------------------------------------------------------------------------
# reading the Anthropic tables
# ---------------------------------------------------------------------------------------------------
def read_vintage(date):
    """Task x type counts and task usage shares for one vintage, read the way the measurement builder reads them.

    The March 2025 vintage has no counts. As in build_aei_collaboration_mapping.py it becomes pseudo-counts:
    usage share x 1000 x the task's share of each type.
    """
    counts, usage = defaultdict(dict), {}
    if date == MARCH_KEY:
        pct, ava = handa.load_task_pct(), handa.load_ava()
        for task, p in pct.items():
            a = ava.get(task)
            if not a:
                continue
            usage[task] = p
            counts[task] = {"directive": p * 1000.0 * a["directive"], "feedback loop": p * 1000.0 * a["feedback_loop"],
                            "task iteration": p * 1000.0 * a["task_iteration"],
                            "validation": p * 1000.0 * a["validation"], "learning": p * 1000.0 * a["learning"]}
        return counts, usage
    c = pd.read_csv(os.path.join(REL, f"onet_task_collaboration_{PLATFORM}_{date}.csv"))
    for r in c.dropna(subset=["count"]).itertuples(index=False):
        counts[r.task_name][r.collaboration] = float(r.count)
    u = pd.read_csv(os.path.join(REL, f"onet_task_{PLATFORM}_{date}.csv"))
    usage = dict(zip(u["task_name"], u["pct"].astype(float)))
    return counts, usage


def overall(platform, date):
    """Totals for one release slice, summed over the published tasks."""
    u = pd.read_csv(os.path.join(REL, f"onet_task_{platform}_{date}.csv"))
    c = pd.read_csv(os.path.join(REL, f"onet_task_collaboration_{platform}_{date}.csv"))
    special = u["task_name"].isin(["none", "not_classified"])
    tot = c.groupby("collaboration")["count"].sum()
    cls = float(tot[TYPES].sum())
    return {"nTasks": int((~special).sum()), "nConv": int(round(u["count"].sum())),
            "noTask": int(round(u.loc[u["task_name"] == "none", "count"].sum())),
            "notCls": int(round(u.loc[u["task_name"] == "not_classified", "count"].sum())),
            "classified": int(round(cls)),
            "shares": {SHORT[t]: r6(tot[t] / cls) for t in TYPES},
            "auto": r6(tot[AUTOMATE].sum() / cls)}


def sample_windows():
    """First and last day of each counted sample, from the raw file names listed in the extract script."""
    with open(os.path.join(MAPS, "extract_aei_release_slices.py"), encoding="utf-8") as fh:
        text = fh.read()
    found = dict(re.findall(r"aei_raw_\*_(\d{4}-\d{2}-\d{2})_to_(\d{4}-\d{2}-\d{2})\.csv", text))
    assert set(POOL_DATES) <= set(found), "sample windows not found in extract_aei_release_slices.py"
    return {d: found[d] for d in POOL_DATES}


# ---------------------------------------------------------------------------------------------------
# the chain, with the rules of build_aei_collaboration_mapping.py
# ---------------------------------------------------------------------------------------------------
def run_chain(counts, usage, task_to_soc, soc_to_isco, styrk_codes):
    """O*NET task -> SOC 2010 -> ISCO-08 -> STYRK-08.

    A task under several SOC codes is split evenly across them. Each SOC code gets its own shares. A STYRK
    code gets the plain mean of the shares of its SOC codes, over the codes with classified conversations.
    The count behind the share is the sum of their classified conversations.
    """
    soc_type, soc_usage = defaultdict(lambda: defaultdict(float)), defaultdict(float)
    for task, types in counts.items():
        socs = task_to_soc.get(task.lower().strip())
        if not socs:
            continue
        for s in socs:
            for t in TYPES:
                soc_type[s][t] += types.get(t, 0.0) / len(socs)
            soc_usage[s] += usage.get(task, 0.0) / len(socs)
    soc_cls = {s: sum(v[t] for t in TYPES) for s, v in soc_type.items()}

    contrib = defaultdict(list)
    for s in soc_type:
        for i in soc_to_isco.get(s, []):
            contrib[i].append(s)
    for target, socs in handa.MANUAL_STYRK_SOC_MAP.items():
        contrib[target] = [s for s in socs if s in soc_type]
    for target, source in handa.MANUAL_STYRK_MAP.items():
        if target not in contrib and source in contrib:
            contrib[target] = contrib[source]

    occ = {}
    for i in sorted(contrib):
        used = [s for s in contrib[i] if soc_cls[s] > 0]
        if i not in styrk_codes or not used:
            continue
        sh = {t: float(np.mean([soc_type[s][t] / soc_cls[s] for s in used])) for t in TYPES}
        occ[i] = {"auto": sh["directive"] + sh["feedback loop"], "aug": 1.0 - sh["directive"] - sh["feedback loop"],
                  "dir": sh["directive"], "fb": sh["feedback loop"], "n": sum(soc_cls[s] for s in used),
                  "u": sum(soc_usage[s] for s in used), "socs": used}
    soc = {s: {"auto": (soc_type[s]["directive"] + soc_type[s]["feedback loop"]) / soc_cls[s],
               "dir": soc_type[s]["directive"] / soc_cls[s], "n": soc_cls[s], "u": soc_usage[s]}
           for s in soc_type if soc_cls[s] > 0}
    return occ, soc, contrib


def terciles(share):
    """Equal-occupation terciles, ties broken by code (build_automation_groups.py)."""
    ranks = share.sort_index().rank(method="first")
    return pd.qcut(ranks, 3, labels=["low", "mid", "high"]).astype(str).reindex(share.index)


def main():
    _, t10, _, s10_to_isco_mp, _, t_isco = mp.load_crosswalks()
    names, n_styrk_all = mp.styrk_names()
    task_to_soc = handa.load_onet_task_to_soc()
    soc_to_isco, _ = handa.load_soc2010_to_isco08()
    styrk_codes = handa.load_styrk08_codes()
    assert {k: sorted(v) for k, v in soc_to_isco.items()} == {k: sorted(v) for k, v in s10_to_isco_mp.items()}, \
        "the two readers of the SOC 2010 -> ISCO-08 crosswalk disagree"

    coll = pd.read_csv(os.path.join(D, "styrk08_aei_collaboration.csv"), dtype={"styrk08": str})
    coll["styrk08"] = coll["styrk08"].str.zfill(4)
    chat = coll[coll["platform"] == PLATFORM]
    grp = pd.read_csv(os.path.join(D, "styrk08_automation_groups.csv"), dtype={"styrk08": str})
    grp["styrk08"] = grp["styrk08"].str.zfill(4)
    grp = grp.set_index("styrk08")
    elo = pd.read_csv(os.path.join(D, "styrk08_eloundou_beta_mapping.csv"), dtype={"styrk08": str})
    elo["styrk08"] = elo["styrk08"].str.zfill(4)
    elo = elo[elo["quintile"].notna()].set_index("styrk08").sort_index()
    front = pd.read_csv(os.path.join(D, "styrk08_handa_mapping.csv"), dtype={"styrk08": str}).set_index("styrk08")

    # ---- 1. rebuild every Claude.ai vintage and compare with the measurement file ----
    vint, soc_by_v, contrib_by_v, raw = {}, {}, {}, {}
    for d in [MARCH_KEY] + POOL_DATES:
        counts, usage = read_vintage(d)
        raw[d] = (counts, usage)
        vint[d], soc_by_v[d], contrib_by_v[d] = run_chain(counts, usage, task_to_soc, soc_to_isco, styrk_codes)
        f = chat[chat["date_start"] == d].set_index("styrk08")
        assert set(f.index) == set(vint[d]), f"{d}: the rebuilt chain gives other STYRK codes than the measurement file"
        for c, o in vint[d].items():
            r = f.loc[c]
            assert abs(o["auto"] - r["automation_share"]) < 1e-6, f"{d} {c}: automation share"
            assert abs(o["dir"] - r["directive_share"]) < 1e-6, f"{d} {c}: directive share"
            assert abs(o["u"] - r["usage_pct"]) < 1e-6, f"{d} {c}: usage share"
            assert int(r["n_soc_matched"]) == len(o["socs"]), f"{d} {c}: number of SOC codes"
            if d != MARCH_KEY:
                assert abs(o["n"] - r["n_classified"]) < 0.051, f"{d} {c}: classified conversations"
        print(f"Utvalg {d}: {len(vint[d])} STYRK-koder, kjeden gjenskapt og lik styrk08_aei_collaboration.csv")

    # ---- 2. pooling, threshold and terciles, compared with the grouping file ----
    universe = elo.index
    pool = chat[chat["date_start"].isin(POOL_DATES)]
    num = (pool["automation_share"] * pool["n_classified"]).groupby(pool["styrk08"]).sum()
    den = pool.groupby("styrk08")["n_classified"].sum()
    pooled = (num / den).reindex(universe)
    n_pool = den.reindex(universe).fillna(0).astype(int)
    gated = pooled[n_pool >= MIN_N]
    group = pd.Series("too_few", index=universe)
    group[gated.index] = terciles(gated)
    g = grp.reindex(universe)
    ok = g["automation_share"].notna()
    assert (pooled[ok].round(4) - g.loc[ok, "automation_share"]).abs().max() < 1e-9, "pooled share differs from the grouping file"
    assert pooled[~ok].isna().all(), "pooled share where the grouping file has none"
    assert (n_pool == g["n_classified"]).all(), "pooled count differs from the grouping file"
    assert (group == g["automation_group"]).all(), "groups differ from the grouping file"
    sizes = [int((group == k).sum()) for k in ["low", "mid", "high", "too_few"]]
    assert sizes == [97, 97, 97, 106], f"group sizes {sizes}"
    cuts = [round(float(gated.quantile(1 / 3)), 4), round(float(gated.quantile(2 / 3)), 4)]
    # The same pooling on the rebuilt, unrounded shares
    rebuilt = {}
    for c in universe:
        parts = [(vint[d][c]["auto"], vint[d][c]["n"]) for d in POOL_DATES if c in vint[d]]
        if parts:
            rebuilt[c] = sum(a * n for a, n in parts) / sum(n for _, n in parts)
    assert max(abs(rebuilt[c] - pooled[c]) for c in rebuilt) < 1e-5, "pooling the rebuilt shares gives another result"
    print(f"Sammenslått: {len(gated)} yrker i grupper {sizes[:3]}, {sizes[3]} too_few, grenser {cuts}, lik styrk08_automation_groups.csv")

    # ---- 3. the example: the 18 tasks of Informasjonsrådgivere ----
    on = pd.read_csv(os.path.join(D, "handa", "onet_task_statements.csv"))
    x = on[on["O*NET-SOC Code"] == EXAMPLE_ONET]
    ids = set(x["Task ID"].astype(int))
    assert len(x) == 18 and ids - set(mp.TASK_NO) == set(OLD_TO_NEW_ID) and \
        set(mp.TASK_NO) - ids == set(OLD_TO_NEW_ID.values()), "the example tasks are not the 18 of the Eloundou animation"
    tasks = []
    for r in x.itertuples(index=False):
        key = r.Task.lower().strip()
        row = {"id": int(r[2]), "no": TASK_NO[int(r[2])], "en": r.Task, "type": "K" if r[4] == "Core" else "T",
               "nSoc": len(task_to_soc[key]), "v": {}}
        for d in POOL_DATES:
            counts, usage = raw[d]
            hit = next((t for t in counts if t.lower().strip() == key), None)
            types = counts.get(hit, {}) if hit else {}
            row["v"][d] = {**{SHORT[t]: r6(types.get(t, 0.0)) for t in SHORT},
                           "p": r6(usage.get(hit, 0.0)) if hit else 0.0}
        tasks.append(row)
    tasks.sort(key=lambda t: -(t["v"]["2026-02-05"]["p"] or 0))
    assert all(t["nSoc"] == 1 for t in tasks), "an example task sits under several SOC codes; the split must be shown"

    by_v = {}
    for d in POOL_DATES:
        cls = sum(sum(t["v"][d][SHORT[k]] for k in TYPES) for t in tasks)
        auto = sum(t["v"][d]["d"] + t["v"][d]["fb"] for t in tasks) / cls
        f = chat[(chat["date_start"] == d) & (chat["styrk08"] == EXAMPLE_STYRK)].iloc[0]
        assert abs(cls - f["n_classified"]) < 0.051, f"{d}: the task counts do not add up to the occupation count"
        assert abs(auto - f["automation_share"]) < 1e-6, f"{d}: the task counts do not give the occupation share"
        by_v[d] = {"auto": r6(auto), "dir": r6(f["directive_share"]), "n": int(round(cls)), "u": r6(f["usage_pct"]),
                   "nTasks": sum(1 for t in tasks if sum(t["v"][d][SHORT[k]] for k in TYPES) > 0)}
    pooled_ex = sum(by_v[d]["auto"] * by_v[d]["n"] for d in POOL_DATES) / sum(by_v[d]["n"] for d in POOL_DATES)
    assert round(pooled_ex, 4) == g.loc[EXAMPLE_STYRK, "automation_share"], "the example's pooled share"
    assert sum(by_v[d]["n"] for d in POOL_DATES) == g.loc[EXAMPLE_STYRK, "n_classified"], "the example's pooled count"
    m = chat[(chat["date_start"] == MARCH_KEY) & (chat["styrk08"] == EXAMPLE_STYRK)].iloc[0]
    example = {"onet": EXAMPLE_ONET, "soc": EXAMPLE_ONET[:7], "styrk": EXAMPLE_STYRK, "name": names[EXAMPLE_STYRK],
               "title": t10[EXAMPLE_ONET[:7]], "tasks": tasks, "v": by_v,
               "pooled": {"auto": r6(pooled_ex), "n": int(g.loc[EXAMPLE_STYRK, "n_classified"]),
                          "group": g.loc[EXAMPLE_STYRK, "automation_group"],
                          "uMean": r6(g.loc[EXAMPLE_STYRK, "usage_pct_mean"])},
               "march": {"auto": r6(m["automation_share"]), "dir": r6(m["directive_share"]), "u": r6(m["usage_pct"]),
                         "front": r6(front.loc[EXAMPLE_STYRK, "automation_share"]),
                         "frontQ": int(front.loc[EXAMPLE_STYRK, "q_automation_share"])}}
    print(f"Eksempel {EXAMPLE_STYRK}: oppgaver med samtaler {[by_v[d]['nTasks'] for d in POOL_DATES]} av 18, "
          f"andeler {[by_v[d]['auto'] for d in POOL_DATES]}, samtaler {[by_v[d]['n'] for d in POOL_DATES]} "
          f"-> {pooled_ex:.4f} av {example['pooled']['n']}")

    # ---- 4. the code chain for the example, and the number of codes at each link ----
    soc_ex = EXAMPLE_ONET[:7]
    assert soc_to_isco[soc_ex] == [EXAMPLE_STYRK] and vint["2026-02-05"][EXAMPLE_STYRK]["socs"] == [soc_ex]
    chain = [{"k": "O*NET-SOC", "c": EXAMPLE_ONET, "n": str(x["Title"].iloc[0])},
             {"k": "SOC 2010", "c": soc_ex, "n": t10[soc_ex]},
             {"k": "ISCO-08", "c": EXAMPLE_STYRK, "n": t_isco[EXAMPLE_STYRK]},
             {"k": "STYRK-08", "c": EXAMPLE_STYRK, "n": names[EXAMPLE_STYRK]}]
    counts_by_v = {}
    for d in POOL_DATES:
        counts, _ = raw[d]
        n_tasks = sum(1 for t, ty in counts.items()
                      if t.lower().strip() in task_to_soc and sum(ty.get(k, 0.0) for k in TYPES) > 0)
        socs = set(soc_by_v[d])
        iscos = {i for s in socs for i in soc_to_isco.get(s, [])}
        counts_by_v[d] = {"nTasks": n_tasks, "nSoc10": len(socs), "nIsco": len(iscos), "nStyrk": len(vint[d])}
    any_v = set().union(*(vint[d] for d in POOL_DATES))
    chain_n = {"byVintage": counts_by_v, "nStyrkAny": len(any_v), "nUniverse": int(len(universe)),
               "nUniverseAny": int((g["n_vintages"] > 0).sum()), "nGrouped": len(gated), "nStyrkAll": int(n_styrk_all)}
    print("Antall koder i kjeden:", chain_n)

    # ---- 5. the definition matters: Programvareutviklere ----
    def series(c):
        return {d: {"auto": r6(vint[d][c]["auto"]), "dir": r6(vint[d][c]["dir"]), "fb": r6(vint[d][c]["fb"]),
                    "n": int(round(vint[d][c]["n"]))} for d in POOL_DATES if c in vint[d]}
    definition = {"c": DEFINITION, "n": names[DEFINITION], "v": series(DEFINITION),
                  "pooled": {"auto": r6(g.loc[DEFINITION, "automation_share"]), "dir": r6(g.loc[DEFINITION, "directive_share"]),
                             "group": g.loc[DEFINITION, "automation_group"], "groupDir": g.loc[DEFINITION, "directive_group"]}}
    unstable = {"c": UNSTABLE, "n": names[UNSTABLE], "v": series(UNSTABLE),
                "pooled": {"auto": r6(g.loc[UNSTABLE, "automation_share"]), "n": int(g.loc[UNSTABLE, "n_classified"]),
                           "group": g.loc[UNSTABLE, "automation_group"]}}
    # Unknown share in March 2025: every task filtered, so the front-page measure sets the share to 0 and
    # puts the occupation in Q1, while the rebuilt chain (which skips SOC codes without classified
    # conversations) gives it no value at all.
    fr = front.loc[UNKNOWN]
    assert fr["automation_share"] == 0 and fr["augmentation_share"] == 0 and fr["q_automation_share"] == 1 \
        and UNKNOWN not in vint[MARCH_KEY], f"{UNKNOWN} is not an occupation with unknown share in March 2025"
    unknown = {"c": UNKNOWN, "n": names[UNKNOWN], "front": 0.0, "frontQ": 1, "v": series(UNKNOWN),
               "pooled": {"auto": r6(g.loc[UNKNOWN, "automation_share"]), "n": int(g.loc[UNKNOWN, "n_classified"]),
                          "group": g.loc[UNKNOWN, "automation_group"]}}
    print(f"Definisjon {DEFINITION}: {definition['v']['2026-02-05']}, sammenslått {definition['pooled']}")
    print(f"Ukjent i mars 2025, {UNKNOWN}: forsiden 0 i Q1, sammenslått {unknown['pooled']}")
    print(f"Ustabil {UNSTABLE}: {[unstable['v'][d]['auto'] for d in POOL_DATES]} -> {unstable['pooled']}")

    # ---- 6. when the codes do not fit: merge, fan-out and the Norwegian exceptions (Feb 2026) ----
    feb = "2026-02-05"
    occ_f, soc_f = vint[feb], soc_by_v[feb]
    feeders = occ_f[MERGE_STYRK]["socs"]
    assert len(feeders) >= 2 and abs(np.mean([soc_f[s]["auto"] for s in feeders]) - occ_f[MERGE_STYRK]["auto"]) < 1e-9
    merge = {"styrk": {"c": MERGE_STYRK, "n": names[MERGE_STYRK], "auto": r6(occ_f[MERGE_STYRK]["auto"]),
                       "nConv": int(round(occ_f[MERGE_STYRK]["n"]))},
             "soc10": [{"c": s, "n": t10.get(s, s), "auto": r6(soc_f[s]["auto"]), "nConv": int(round(soc_f[s]["n"]))}
                       for s in feeders]}
    targets = [i for i in soc_to_isco.get(FAN_SOC10, []) if i in occ_f]
    fan = {"src": {"c": FAN_SOC10, "n": t10[FAN_SOC10], "auto": r6(soc_f[FAN_SOC10]["auto"]),
                   "nConv": int(round(soc_f[FAN_SOC10]["n"]))},
           "to": [{"c": i, "n": names[i], "s": mp.SHORT_FAN.get(i, names[i]), "auto": r6(occ_f[i]["auto"]),
                   "only": occ_f[i]["socs"] == [FAN_SOC10]} for i in targets]}
    exc = []
    for c in EXCEPTIONS:
        src = handa.MANUAL_STYRK_MAP.get(c)
        how = ("kopi av " + src + " " + names[src]) if src else \
              ("fra SOC " + ", ".join(handa.MANUAL_STYRK_SOC_MAP[c]) + " " + t10[handa.MANUAL_STYRK_SOC_MAP[c][0]])
        exc.append({"c": c, "n": names[c], "how": how, "auto": r6(g.loc[c, "automation_share"]),
                    "nConv": int(g.loc[c, "n_classified"]), "group": g.loc[c, "automation_group"]})
    print(f"Flere blir én, {MERGE_STYRK}: {[(f['c'], f['auto']) for f in merge['soc10']]} -> {merge['styrk']['auto']}")
    print(f"Én blir flere, {FAN_SOC10} ({fan['src']['auto']}): {[(t['c'], t['auto'], t['only']) for t in fan['to']]}")
    print("Unntak:", [(e["c"], e["auto"], e["group"]) for e in exc])

    # ---- 7. too few conversations, the dots, terciles and Eloundou ----
    tf = group == "too_few"
    no_data = g["n_vintages"] == 0                 # no task of the occupation in any of the three tables
    too_few = {"n": int(tf.sum()), "nNoData": int(no_data.sum()), "nUnder": int((tf & ~no_data).sum()),
               "byQ": [int(((elo["quintile"] == q) & tf).sum()) for q in range(1, 6)],
               "codes": [{"c": c, "n": names.get(c, c), "nConv": int(n_pool[c]), "qe": int(elo.loc[c, "quintile"])}
                         for c in universe[tf]]}
    assert too_few["n"] == sizes[3] and not (no_data & ~tf).any(), "an occupation without data is in a group"
    ranks = gated.sort_index().rank(method="first").astype(int)
    gnum = {"low": 1, "mid": 2, "high": 3}
    dots = [{"c": c, "n": names.get(c, c), "s": r6(gated[c]), "r": int(ranks[c]), "g": gnum[group[c]],
             "e": r6(elo.loc[c, "eloundou_beta"]), "qe": int(elo.loc[c, "quintile"]), "nConv": int(n_pool[c])}
            for c in sorted(gated.index)]
    ss = np.array([d_["s"] for d_ in dots]); ee = np.array([d_["e"] for d_ in dots])
    corr = {"pearson": round(float(np.corrcoef(ss, ee)[0, 1]), 3), "spearman": round(float(stats.spearmanr(ss, ee)[0]), 3),
            "n": len(dots)}
    print(f"too_few: {too_few['nNoData']} uten data, {too_few['nUnder']} under {MIN_N} samtaler, "
          f"etter Eloundou-kvintil {too_few['byQ']}. Mot Eloundou: {corr}")

    # ---- 8. Anthropic's side: the releases and the totals behind them ----
    win = sample_windows()
    rel_meta = [
        {"id": "release_2025_02_10", "pub": "2025-02", "name": "Handa m.fl. (2025)", "sample": "des. 2024 til jan. 2025",
         "platforms": ["Claude.ai"], "table": "ingen tabell per oppgave"},
        {"id": "release_2025_03_27", "pub": "2025-03", "name": "Claude 3.7 Sonnet", "sample": "11 dager fra 24. feb. 2025",
         "platforms": ["Claude.ai"], "table": "andeler"},
        {"id": "release_2025_09_15", "pub": "2025-09", "key": "2025-08-04", "platforms": ["Claude.ai", "API"], "table": "antall"},
        {"id": "release_2026_01_15", "pub": "2026-01", "key": "2025-11-13", "platforms": ["Claude.ai", "API"], "table": "antall"},
        {"id": "release_2026_03_24", "pub": "2026-03", "key": "2026-02-05", "platforms": ["Claude.ai", "API"], "table": "antall"},
        {"id": "release_2026_06_26", "pub": "2026-06", "name": "Cadences", "sample": "april og mai 2026, per måned",
         "platforms": ["Claude.ai og Cowork", "API"], "table": "andeler, ny metode"},
    ]
    for r in rel_meta:
        if "key" in r:
            r["sample"] = {"start": r["key"], "end": win[r["key"]]}
            r["chat"] = overall("claude_ai", r["key"])
            r["api"] = overall("api", r["key"])
    by_task = pd.read_csv(os.path.join(D, "handa", "automation_vs_augmentation_by_task.csv"))
    pct_v2 = pd.read_csv(os.path.join(D, "handa", "task_pct_v2.csv"))
    bt = by_task.merge(pct_v2, on="task_name")
    cols = {"directive": "d", "feedback_loop": "fb", "task_iteration": "ti", "validation": "va", "learning": "le"}
    w = bt["pct"] * (1 - bt["filtered"])
    march = {"nTasks": int(len(by_task)), "nFiltered": int((by_task["filtered"] == 1).sum()),
             "shares": {v: r6((bt[k] * bt["pct"]).sum() / w.sum()) for k, v in cols.items()}}
    march["auto"] = r6(march["shares"]["d"] + march["shares"]["fb"])
    rel_meta[1]["chat"] = march
    for r in rel_meta:
        if "chat" in r:
            print(f"{r['id']}: chat automatisering {r['chat']['auto']}"
                  + (f", API {r['api']['auto']}, samtaler {r['chat']['nConv']}, uten oppgave {r['chat']['noTask']}"
                     if "api" in r else f", {r['chat']['nFiltered']} av {r['chat']['nTasks']} oppgaver filtrert"))

    # ---- 9. the result table ----
    ex = []
    for c in RESULT_ROWS:
        mrow = chat[(chat["date_start"] == MARCH_KEY) & (chat["styrk08"] == c)]
        ex.append({"c": c, "n": names[c], "auto": r6(g.loc[c, "automation_share"]), "aug": r6(1 - g.loc[c, "automation_share"]),
                   "nConv": int(g.loc[c, "n_classified"]), "group": g.loc[c, "automation_group"],
                   "march": r6(mrow["automation_share"].iloc[0]) if len(mrow) else None,
                   "e": r6(elo.loc[c, "eloundou_beta"]), "qe": int(elo.loc[c, "quintile"])})
    ex.sort(key=lambda r: -r["auto"])                                              # highest share first

    meta = {"platform": PLATFORM, "pool": POOL_DATES, "minN": MIN_N, "groups": sizes, "cuts": cuts,
            "nUniverse": int(len(universe)), "nGrouped": len(gated), "nStyrkAll": int(n_styrk_all),
            "example": {"onet": EXAMPLE_ONET, "styrk": EXAMPLE_STYRK}, "oldToNewTaskId": OLD_TO_NEW_ID}
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    mp.jdump(os.path.join(HERE, "data", "bruk-anthropic.js"), "BRUK_ANTHROPIC", {
        "meta": meta, "releases": rel_meta, "example": example, "chain": chain, "chainN": chain_n,
        "definition": definition, "unstable": unstable, "unknown": unknown, "merge": merge, "fan": fan, "exc": exc,
        "tooFew": too_few, "dots": dots, "corr": corr, "ex": ex,
    })


if __name__ == "__main__":
    main()
