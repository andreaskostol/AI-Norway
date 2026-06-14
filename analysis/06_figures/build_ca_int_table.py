"""Pooled-DiD comparison table across the five INT specifications.

One table per timing (ChatGPT / agentic). Columns = the five interaction
definitions; within each age-group panel, three rows: exposure × Post,
ln wage × Post, interaction × Post. All effects shown per 1 SD of the construct
(interaction = coef * sd_int). Writes LaTeX (booktabs) and prints markdown.

Usage: python build_ca_int_table.py [count|nyjobb]   (default count)
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

OUTCOME = sys.argv[1] if len(sys.argv) > 1 else "count"
assert OUTCOME in ("count", "nyjobb")
SUF = "" if OUTCOME == "count" else f"_{OUTCOME}"
NOUN = "employment" if OUTCOME == "count" else "new hires"

BASE = Path(__file__).resolve().parents[2]
CDIR = BASE / "analysis" / "output" / "coefficients"
DID = pd.read_csv(CDIR / f"coef_ca_int_did{SUF}.csv")
ST = pd.read_csv(CDIR / f"coef_ca_int_did{SUF}_modelstats.csv")
TBL = BASE / "analysis" / "output" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}
VARIANTS = [("prod", "raw product"), ("rect0", r"rect.\ ${>}$mean"),
            ("rect1", r"rect.\ ${>}{+}1$SD"),
            ("corner75", r"corner $p75$"), ("corner80", r"corner $p80$")]
VMD = {"prod": "raw prod", "rect0": "rect>mean", "rect1": "rect>+1SD",
       "corner75": "corner p75", "corner80": "corner p80"}
TERMS = [("exp", r"Exposure $\times$ Post", "Exp×Post"),
         ("wage", r"ln wage $\times$ Post", "Wage×Post"),
         ("int", r"Interaction $\times$ Post", "Int×Post")]
TIMINGS = [("chatgpt", "ChatGPT (ref.\\ Oct 2022)"),
           ("agentic", "Agentic (ref.\\ Apr 2025)")]


def star(c, se):
    if not (np.isfinite(c) and np.isfinite(se)) or se == 0:
        return ""
    z = abs(c / se)
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""


def get(timing, variant, term, age):
    r = DID[(DID.timing == timing) & (DID.variant == variant)
            & (DID.term == term) & (DID.age_group == age)]
    if not len(r):
        return np.nan, np.nan
    c, se = float(r.coef.iloc[0]), float(r.se.iloc[0])
    if term == "int":                      # per-SD display
        sd = float(r.sd_int.iloc[0])
        c, se = c * sd, se * sd
    return c, se


def getstat(timing, variant, age, col):
    r = ST[(ST.timing == timing) & (ST.variant == variant)
           & (ST.age_group == age)]
    return r[col].iloc[0] if len(r) else np.nan


for timing, tlab in TIMINGS:
    # ---------- LaTeX ----------
    ncol = len(VARIANTS)
    L = [r"\begin{table}[H]\centering",
         rf"\caption{{Interaction specifications compared: AI exposure, wage, "
         rf"and private-sector {NOUN} ({tlab}).}}",
         rf"\label{{tab:ca_int_{timing}{SUF}}}", r"\small",
         r"\begin{tabular}{l" + "c" * ncol + "}", r"\toprule",
         " & " + " & ".join(f"({i+1})" for i in range(ncol)) + r" \\",
         " & " + " & ".join(lab for _, lab in VARIANTS) + r" \\", r"\midrule"]
    for ag, albl in AGE.items():
        L.append(rf"\multicolumn{{{ncol+1}}}{{@{{}}l}}{{\textit{{Panel: ages "
                 rf"{albl}}}}} \\")
        for term, tex_lab, _ in TERMS:
            coefs, ses = [], []
            for v, _ in VARIANTS:
                c, se = get(timing, v, term, ag)
                coefs.append(f"{c:+.4f}{star(c, se)}" if np.isfinite(c) else "")
                ses.append(f"({se:.4f})" if np.isfinite(se) else "")
            L.append(tex_lab + " & " + " & ".join(coefs) + r" \\")
            L.append(" & " + " & ".join(ses) + r" \\")
        nobs = getstat(timing, "prod", ag, "nobs")
        occ = getstat(timing, "prod", ag, "n_clusters")
        pr2 = [f"{getstat(timing, v, ag, 'pr2'):.4f}" for v, _ in VARIANTS]
        L.append(rf"\quad Observations & \multicolumn{{{ncol}}}{{c}}"
                 rf"{{{int(nobs):,} \quad (occ.\ {int(occ)})}} \\")
        L.append(r"\quad Pseudo $R^2$ & " + " & ".join(pr2) + r" \\")
        L.append(r"\addlinespace")
    L += [r"\bottomrule", r"\end{tabular}",
          r"\begin{minipage}{\linewidth}\vspace{2pt}\footnotesize",
          rf"\emph{{Notes:}} Poisson PPML, cell-level {NOUN}, private sector. "
          r"Each column is one model: the free linear gradients "
          r"$z(\text{exp})\times$Post and $z(\text{lnw})\times$Post are always "
          r"included; only the \emph{interaction} term changes. (1) raw product "
          r"$z(\text{exp})z(\text{lnw})$; (2) rectified "
          r"$\max\{z(\text{exp}),0\}\max\{z(\text{lnw}),0\}$; (3) rectified at "
          r"$+1$ SD; (4)--(5) joint upper-quartile / quintile corner dummies. "
          r"Coefficients are average post-period effects vs.\ the reference month "
          r"($k{=}{-}1$), each pre-month a separate control. All effects shown "
          r"per 1 SD of the construct ($\Delta\log$ per SD). Occupation and "
          r"month FE; SE clustered at occupation in parentheses. "
          r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.",
          r"\end{minipage}", r"\end{table}"]
    out = TBL / f"table_ca_int_{timing}{SUF}.tex"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[wrote {out}]")

    # ---------- markdown ----------
    print(f"\n## {tlab}  —  Δlog {NOUN} per 1 SD (pooled Post vs. k=−1)\n")
    for ag, albl in AGE.items():
        print(f"\n**Ages {albl}**\n")
        print("| Term | " + " | ".join(VMD[v] for v, _ in VARIANTS) + " |")
        print("|" + "---|" * (len(VARIANTS) + 1))
        for term, _, md in TERMS:
            cells = []
            for v, _ in VARIANTS:
                c, se = get(timing, v, term, ag)
                cells.append(f"{c:+.4f}{star(c, se)} ({se:.4f})"
                             if np.isfinite(c) else "")
            print(f"| {md} | " + " | ".join(cells) + " |")
        pr2 = [f"{getstat(timing, v, ag, 'pr2'):.4f}" for v, _ in VARIANTS]
        print("| pseudo R² | " + " | ".join(pr2) + " |")
