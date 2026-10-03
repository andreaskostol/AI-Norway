"""
build_data.py

Builds the data files for the mapping animations (O*NET -> Norwegian occupations -> exposure scores):

  data/mapping-eloundou.js   window.MAP_ELOUNDOU   Eloundou et al. (2024), GPT-4 beta
  data/mapping-mouchel.js    window.MAP_MOUCHEL    Mouchel, Bouquet and Sheffi (2026), arms A1 and S0

Everything is read from the project files in this run: the task-level labels, the occupation-level
scores, the two BLS crosswalks, the STYRK-08 code list and the two finished mapping files. The chain
is rebuilt with the same rules as analysis/03_mappings/build_eloundou_mapping.py, and the result is
checked against the finished mapping files.

Usage (from anywhere):
    python slides/mapping-pipeline/build_data.py
"""

import json                                   # write the data payloads
import os                                     # paths
import sys                                    # console encoding on Windows
from collections import defaultdict           # accumulate crosswalk links

import numpy as np                            # correlations
import openpyxl                               # SOC 2010 <-> 2018 workbook
import pandas as pd                           # tables
import xlrd                                   # SOC 2010 <-> ISCO-08 workbook (legacy xls)
from scipy import stats                       # Spearman correlation

sys.stdout.reconfigure(encoding="utf-8")      # Norwegian characters in the console

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
D = os.path.join(REPO, "data", "ai_exposure")

# The running example: Public Relations Specialists = STYRK 2432 Informasjonsrådgivere
EXAMPLE_ONET = "27-3031.00"
EXAMPLE_STYRK = "2432"

# Short Norwegian labels for the 18 tasks of the example, by O*NET task id
TASK_NO = {
    1764: "Svare medier eller finne talsperson",
    20555: "Planlegge kommunikasjonsprogrammer",
    23951: "Oppdatere nettside og sosiale medier",
    20554: "Skrive pressemeldinger og medietekst",
    1765: "Bygge relasjoner til interessegrupper",
    1770: "Rådgi ledere om trender og interesser",
    1772: "Trene talspersoner i kommunikasjon",
    1769: "Utvikle PR-strategier",
    20557: "Redigere interne og eksterne publikasjoner",
    1768: "Arrangere opptredener og arrangementer",
    1775: "Gjennomføre markeds- og opinionsundersøkelser",
    19811: "Formidle miljø- og samfunnstiltak",
    1767: "Koordinere reklame- og kampanjeproduksjon",
    1771: "Planlegge kampanjer med byråer og medier",
    1773: "Skrive eller holde taler",
    19809: "Håndtere offentlig respons ved hendelser",
    19810: "Markedsføre miljøteknologi og -tjenester",
    1774: "Kjøpe annonseplass og sendetid",
}

# Short titles for the seven STYRK codes that one SOC code fans out to (shortened by hand from the SSB names)
SHORT_FAN = {
    "1112": "Toppledere i det offentlige",
    "1114": "Toppledere i organisasjoner",
    "1120": "Administrerende direktører",
    "1343": "Ledere av eldreomsorg",
    "1346": "Ledere i forsikring og finans",
    "1420": "Varehandelssjefer",
    "5221": "Kiosk og liten butikk",
}

MERGE_STYRK = "7411"                          # several SOC codes become one STYRK code (Elektrikere)
FAN_SOC10 = "11-1021"                         # one SOC code becomes several STYRK codes
EXCEPTIONS = ["2223", "2224", "2267", "2269"] # Norwegian codes with manual sources
RESULT_ROWS_E = ["2432", "2512", "1120", "7411", "5223", "2223"]


def jdump(path, var, obj):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"window.{var} = ")
        json.dump(obj, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print(f"Skrev {os.path.relpath(path, REPO)} ({os.path.getsize(path) / 1024:.0f} kB)")


def load_crosswalks():
    """The two BLS crosswalks, with titles and partial flags (same layout as the mapping builders)."""
    wb = openpyxl.load_workbook(os.path.join(D, "soc_2010_to_2018_crosswalk.xlsx"))
    s18_to_10, t10, t18 = defaultdict(list), {}, {}
    for row in wb.active.iter_rows(min_row=10, values_only=True):
        a = str(row[0]).strip() if row[0] else ""
        b = str(row[2]).strip() if row[2] else ""
        if a and b and "-" in a:
            s18_to_10[b].append(a)
            t10[a] = str(row[1]).strip()
            t18[b] = str(row[3]).strip()
    xb = xlrd.open_workbook(os.path.join(D, "isco_soc_crosswalk.xls"))
    xs = xb.sheet_by_name("2010 SOC to ISCO-08")
    s10_to_isco, partial, t_isco = defaultdict(list), {}, {}
    for i in range(7, xs.nrows):
        s = str(xs.cell_value(i, 0)).strip()
        flag = str(xs.cell_value(i, 2)).strip()
        isco = str(xs.cell_value(i, 3)).strip()
        if s and isco and "-" in s:
            isco = isco.split(".")[0].zfill(4)
            s10_to_isco[s].append(isco)
            partial[(s, isco)] = flag == "*"
            t_isco[isco] = str(xs.cell_value(i, 4)).strip()
    return s18_to_10, t10, t18, s10_to_isco, partial, t_isco


def styrk_names():
    c = pd.read_csv(os.path.join(D, "styrk08_codes.csv"), dtype=str, encoding="cp1252")
    c = c[c["level"] == "4"]
    return dict(zip(c["code"], c["name"])), len(c)


def soc10_scores(score_by_soc18, s18_to_10):
    """SOC 2018 scores carried to SOC 2010, averaged where several 2018 codes feed one 2010 code."""
    acc = defaultdict(list)
    for soc18, v in score_by_soc18.items():
        for s10 in s18_to_10.get(soc18, []):
            acc[s10].append(v)
    return {s: sum(v) / len(v) for s, v in acc.items()}


def chain_counts(score_by_soc18, s18_to_10, s10_to_isco, styrk_codes):
    n18 = len(score_by_soc18)
    s10 = soc10_scores(score_by_soc18, s18_to_10)
    isco = {i for s in s10 if s in s10_to_isco for i in s10_to_isco[s]}
    return {"nSoc18": n18, "nSoc10": len(s10), "nIsco": len(isco)}


def dots_block(m, names, cols):
    """Dots for the 397 occupations, in code order, with ranks the way the builders assign quintiles."""
    m = m.sort_values("styrk08").reset_index(drop=True)
    out = []
    ranks = {c: m[c].astype(float).rank(method="first").astype(int).tolist() for c in cols}
    for i, r in m.iterrows():
        row = {"c": r["styrk08"], "n": names.get(r["styrk08"], r["styrk08"])}
        for c in cols:
            row[c] = round(float(r[c]), 6)
            row["r_" + c] = ranks[c][i]
        out.append(row)
    return m, out


def main():
    s18_to_10, t10, t18, s10_to_isco, partial, t_isco = load_crosswalks()
    names, n_styrk_all = styrk_names()

    occ = pd.read_csv(os.path.join(D, "eloundou_occ_level.csv"))
    occ["soc18"] = occ["O*NET-SOC Code"].str[:7]
    beta18 = occ.groupby("soc18")["dv_rating_beta"].mean().to_dict()
    mou = pd.read_csv(os.path.join(D, "mouchel", "calibrated_occupation_exposure_2026-07-20.csv"))
    mou["soc18"] = mou["onet_soc_code"].str[:7]
    a1_18 = mou.groupby("soc18")["simple_avg_exposure"].mean().to_dict()

    me = pd.read_csv(os.path.join(D, "styrk08_eloundou_beta_mapping.csv"), dtype={"styrk08": str})
    mm = pd.read_csv(os.path.join(D, "styrk08_mouchel_mapping.csv"), dtype={"styrk08": str})
    qcount = me["quintile"].value_counts().sort_index().tolist()

    # ---- task level for the example ----
    t = pd.read_csv(os.path.join(D, "eloundou", "full_labelset.tsv"), sep="\t", index_col=0)
    x = t[t["O*NET-SOC Code"] == EXAMPLE_ONET]
    tasks = []
    for _, r in x.iterrows():
        tid = int(r["Task ID"])
        tasks.append({"no": TASK_NO[tid], "type": "K" if r["Task Type"] == "Core" else "T",
                      "e": r["gpt4_exposure"], "b": float(r["beta"])})
    w = np.array([2 if k["type"] == "K" else 1 for k in tasks], dtype=float)
    b = np.array([k["b"] for k in tasks])
    pub = float(occ.loc[occ["O*NET-SOC Code"] == EXAMPLE_ONET, "dv_rating_beta"].iloc[0])
    assert abs((w * b).sum() / w.sum() - pub) < 1e-9, "task-level weighting does not reproduce the published score"
    counts = {e: int((x["gpt4_exposure"] == e).sum()) for e in ("E0", "E1", "E2")}
    title_onet = str(x["Title"].iloc[0])
    print(f"Eksempel {EXAMPLE_ONET}: {len(tasks)} oppgaver {counts}, vektet {int(w.sum())} -> {pub:.6f}")

    # ---- the chain for the example ----
    soc18_ex = EXAMPLE_ONET[:7]
    soc10_ex = s18_to_10[soc18_ex][0]
    isco_ex = s10_to_isco[soc10_ex][0]
    assert isco_ex == EXAMPLE_STYRK and len(s18_to_10[soc18_ex]) == 1 and len(s10_to_isco[soc10_ex]) == 1
    chain = [
        {"k": "O*NET-SOC", "c": EXAMPLE_ONET, "n": title_onet},
        {"k": "SOC 2018", "c": soc18_ex, "n": t18[soc18_ex]},
        {"k": "SOC 2010", "c": soc10_ex, "n": t10[soc10_ex]},
        {"k": "ISCO-08", "c": isco_ex, "n": t_isco[isco_ex]},
        {"k": "STYRK-08", "c": EXAMPLE_STYRK, "n": names[EXAMPLE_STYRK]},
    ]
    cnt_e = chain_counts(beta18, s18_to_10, s10_to_isco, None)
    cnt_m = chain_counts(a1_18, s18_to_10, s10_to_isco, None)
    print("Antall koder, kjeden:", {"onet": len(occ), **cnt_e}, "STYRK", len(me), "av", n_styrk_all)

    # ---- merge example: several SOC 2010 codes become one STYRK code ----
    s10_e = soc10_scores(beta18, s18_to_10)
    s10_m = soc10_scores(a1_18, s18_to_10)
    feeders = sorted(s for s, lst in s10_to_isco.items() if MERGE_STYRK in lst and s in s10_e)
    merge = {"styrk": {"c": MERGE_STYRK, "n": names[MERGE_STYRK],
                       "b": float(me.loc[me["styrk08"] == MERGE_STYRK, "eloundou_beta"].iloc[0])},
             "soc10": [{"c": s, "n": t10[s], "b": round(s10_e[s], 6)} for s in feeders]}
    assert abs(np.mean([f["b"] for f in merge["soc10"]]) - merge["styrk"]["b"]) < 1e-5

    # ---- fan-out example: one SOC 2010 code becomes several STYRK codes ----
    targets = [i for i in s10_to_isco[FAN_SOC10] if i in set(me["styrk08"])]
    assert set(targets) == set(SHORT_FAN), "short titles do not match the fan-out targets"
    fan = {"src": {"c": FAN_SOC10, "n": t10[FAN_SOC10], "b": round(s10_e[FAN_SOC10], 6)},
           "to": [{"c": i, "n": names[i], "s": SHORT_FAN[i]} for i in targets]}

    # ---- Norwegian exceptions ----
    exc = []
    for c in EXCEPTIONS:
        r = me[me["styrk08"] == c].iloc[0]
        src = str(r["manual_map"])
        how = ("kopi av " + src + " " + names[src]) if not src.startswith("SOC:") else \
              ("fra SOC " + src[4:] + " " + t10[src[4:]])
        exc.append({"c": c, "n": names[c], "b": round(float(r["eloundou_beta"]), 6), "how": how})

    # ---- dots, ranks, examples ----
    me_s, dots_e = dots_block(me, names, ["eloundou_beta"])
    for d_, q in zip(dots_e, me_s["quintile"]):
        d_["q"] = int(q)
    mm_s, dots_m_raw = dots_block(mm, names, ["mouchel_grounded", "mouchel_calibrated"])
    emap = dict(zip(me_s["styrk08"], me_s["eloundou_beta"]))
    eq = dict(zip(me_s["styrk08"], me_s["quintile"]))
    er = {d_["c"]: d_["r_eloundou_beta"] for d_ in dots_e}
    dots_m = []
    for d_, q, q0 in zip(dots_m_raw, mm_s["quintile"], mm_s["quintile_calibrated"]):
        dots_m.append({"c": d_["c"], "n": d_["n"], "e": round(float(emap[d_["c"]]), 6),
                       "a": d_["mouchel_grounded"], "s": d_["mouchel_calibrated"],
                       "q": int(q), "qs": int(q0), "qe": int(eq[d_["c"]]),
                       "ra": d_["r_mouchel_grounded"], "re": er[d_["c"]]})

    def ex_row_e(c):
        d_ = next(z for z in dots_e if z["c"] == c)
        return {"c": c, "n": d_["n"], "b": d_["eloundou_beta"], "q": d_["q"], "r": d_["r_eloundou_beta"]}
    ex_e = sorted((ex_row_e(c) for c in RESULT_ROWS_E), key=lambda r: -r["b"])    # highest score first

    # ---- Mouchel versus Eloundou ----
    ee = np.array([z["e"] for z in dots_m]); aa = np.array([z["a"] for z in dots_m])
    shift = np.array([z["ra"] - z["re"] for z in dots_m])
    qe = np.array([z["qe"] for z in dots_m]); qa = np.array([z["q"] for z in dots_m])
    corr = {"pearson": round(float(np.corrcoef(ee, aa)[0, 1]), 3),
            "spearman": round(float(stats.spearmanr(ee, aa)[0]), 3),
            "sameQ": round(float(100 * (qe == qa).mean()), 1),
            "withinOne": round(float(100 * (np.abs(qe - qa) <= 1).mean()), 1)}
    order = np.argsort(shift)
    movers = {"up": [dots_m[i]["c"] for i in order[::-1][:2]], "down": [dots_m[i]["c"] for i in order[:2]]}
    print("Korrelasjoner:", corr, " flyttere:", movers)

    m_row = mou[mou["onet_soc_code"] == EXAMPLE_ONET].iloc[0]
    mou_occ = {"onet": EXAMPLE_ONET, "title": title_onet, "e": round(pub, 6),
               "a": round(float(m_row["simple_avg_exposure"]), 6),
               "s": round(float(m_row["calibrated_exposure"]), 6)}
    ex_ids_m = ["2432", "2512"] + movers["up"] + movers["down"]
    ex_m = []
    for c in ex_ids_m:
        z = next(zz for zz in dots_m if zz["c"] == c)
        ex_m.append({"c": c, "n": z["n"], "e": z["e"], "qe": z["qe"], "a": z["a"], "q": z["q"], "s": z["s"], "qs": z["qs"]})
    ex_m.sort(key=lambda r: -r["a"])                                              # highest Mouchel A1 first

    # ---- checks and files ----
    assert len(dots_e) == len(dots_m) == 397
    assert t["O*NET-SOC Code"].nunique() == len(occ), "task file and occupation file differ in occupations"
    meta = {"nOnet": int(len(occ)), "nTasks": int(len(t)), "nStyrk": int(len(me)), "nStyrkAll": int(n_styrk_all), "q": qcount,
            "example": {"onet": EXAMPLE_ONET, "styrk": EXAMPLE_STYRK}}

    jdump(os.path.join(HERE, "data", "mapping-eloundou.js"), "MAP_ELOUNDOU", {
        "meta": {**meta, **cnt_e},
        "tasks": tasks,
        "occ": {"onet": EXAMPLE_ONET, "title": title_onet, "beta": round(pub, 6), "num": float((w * b).sum()),
                "den": float(w.sum()), "core": int((w == 2).sum()), "supp": int((w == 1).sum()), "counts": counts},
        "chain": chain, "merge": merge, "fan": fan, "exc": exc, "dots": dots_e, "ex": ex_e,
    })
    jdump(os.path.join(HERE, "data", "mapping-mouchel.js"), "MAP_MOUCHEL", {
        "meta": {**meta, **cnt_m, "nPairs": 18796, "nModels": 7, "nNews": 30000, "nAbstracts": 24000},
        "occ": mou_occ, "chain": chain, "dots": dots_m, "corr": corr, "movers": movers, "ex": ex_m,
    })


if __name__ == "__main__":
    main()
