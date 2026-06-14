"""Publication-ready DiD tables, one per age group, 6 columns:
   (1)-(3) ChatGPT  M1/M2/M3 ; (4)-(6) Agentic  M1/M2/M3.

M1 = exposure only, M2 = ln wage only, M3 = exposure + ln wage + interaction
(all interacted with Post = 1[k>=0]; pre-period reference). A coefficient row is
blank in the columns where that term is not in the model, which makes the nesting
explicit. Writes LaTeX (booktabs) per age group and prints markdown.
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
DEPVAR = {"count": "employment headcount",
          "nyjobb": "new hires = round(count $\\times$ ny\\_jobb)"}[OUTCOME]
ESTIMATOR = sys.argv[2] if len(sys.argv) > 2 else "ppml"
assert ESTIMATOR in ("ppml", "olslog")
NOUN = "employment" if OUTCOME == "count" else "new hires"
if ESTIMATOR == "olslog":
    SUF += "_olslog"
    DEPVAR = f"log {NOUN}"
ESTLINE = ("Poisson PPML" if ESTIMATOR == "ppml" else
           f"OLS on log {NOUN}, weighted by baseline (pre-period) {NOUN} "
           r"(zero cells dropped)")
R2LINE = (r"Pseudo $R^2 \approx 0.99$ (FE-driven). " if ESTIMATOR == "ppml"
          else "")

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients" / f"coef_ca_did_stdexp{SUF}.csv"
STAT = BASE / "analysis" / "output" / "coefficients" / f"coef_ca_did_stdexp{SUF}_modelstats.csv"
TBL = BASE / "analysis" / "output" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}
COLS = [("chatgpt", "m1"), ("chatgpt", "m2"), ("chatgpt", "m3"),
        ("agentic", "m1"), ("agentic", "m2"), ("agentic", "m3")]
TERMS = [("exp", "Exposure $\\times$ Post", "Exposure × Post"),
         ("wage", "ln wage $\\times$ Post", "ln wage × Post"),
         ("exp_x_wage", "Exp $\\times$ wage $\\times$ Post", "Exp × wage × Post")]

df = pd.read_csv(COEF)
st = pd.read_csv(STAT)


def star(c, se):
    if not (np.isfinite(c) and np.isfinite(se)) or se == 0:
        return ""
    z = abs(c / se)
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""


def get(timing, model, term, age):
    r = df[(df.timing == timing) & (df.model == model)
           & (df.term == term) & (df.age_group == age)]
    if len(r):
        return float(r.coef.iloc[0]), float(r.se.iloc[0])
    return np.nan, np.nan


def getstat(timing, model, age, col):
    r = st[(st.timing == timing) & (st.model == model) & (st.age_group == age)]
    return r[col].iloc[0] if len(r) else np.nan


# ---------------- LaTeX (one file per age group) ----------------
for ag, lab in AGE.items():
    L = [r"\begin{table}[htbp]\centering",
         rf"\caption{{AI exposure, wage, and private-sector {DEPVAR}: ages {lab}}}",
         rf"\label{{tab:ca_did_age{ag}}}", r"\small",
         r"\begin{tabular}{lcccccc}", r"\toprule",
         r" & \multicolumn{3}{c}{ChatGPT (ref.\ Oct 2022)} "
         r"& \multicolumn{3}{c}{Agentic (ref.\ Apr 2025)} \\",
         r"\cmidrule(lr){2-4} \cmidrule(lr){5-7}",
         r" & (1) & (2) & (3) & (4) & (5) & (6) \\", r"\midrule"]
    for term, tex_lab, _ in TERMS:
        coefs, ses = [], []
        for timing, model in COLS:
            c, se = get(timing, model, term, ag)
            coefs.append(f"{c:+.4f}{star(c, se)}" if np.isfinite(c) else "")
            ses.append(f"({se:.4f})" if np.isfinite(se) else "")
        L.append(tex_lab + " & " + " & ".join(coefs) + r" \\")
        L.append(" & " + " & ".join(ses) + r" \\")
    L.append(r"\midrule")
    L.append(r"Occupation FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    L.append(r"Month FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    obs = [f"{int(getstat(t, m, ag, 'nobs')):,}" for t, m in COLS]
    occ = [f"{int(getstat(t, m, ag, 'n_clusters'))}" for t, m in COLS]
    pr2 = [f"{getstat(t, m, ag, 'pr2'):.4f}" for t, m in COLS]
    L.append(r"Observations & " + " & ".join(obs) + r" \\")
    L.append(r"Occupations (clusters) & " + " & ".join(occ) + r" \\")
    L.append(r"Pseudo $R^2$ & " + " & ".join(pr2) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}",
          r"\begin{minipage}{\linewidth}\vspace{2pt}\footnotesize",
          rf"\emph{{Notes:}} {ESTLINE} (cell-level {DEPVAR}, private "
          r"sector). Columns (1)--(3) anchor the event window on ChatGPT "
          r"(Oct 2022 = $k{=}{-}1$, through 2025m4); (4)--(6) on agentic AI "
          r"(Apr 2025 = $k{=}{-}1$, from 2023m7). Each coefficient is the average "
          r"post-period effect relative to the reference month ($k{=}{-}1$), with "
          r"each pre-period month as a separate control. Treatments are "
          r"standardized within age group: "
          r"$z(\text{exp})$ = Eloundou $\beta$, $z(\text{lnw})$ = ln full-time "
          r"-equivalent wage (kontantl\o nn$/$stillingsprosent, pre-ChatGPT). "
          r"Occupation and month fixed effects; SE clustered at occupation in "
          r"parentheses. Coefficients are $\Delta\log$ employment per 1 SD. "
          r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.",
          r"\end{minipage}", r"\end{table}"]
    out = TBL / f"table_ca_did_age{ag}{SUF}.tex"
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"[wrote {out}]")

# ---------------- combined 4-panel table (one per outcome) ----------------
PANEL = {1: "A", 2: "B", 3: "C", 4: "D"}
C = [r"\begin{table}[H]\centering",
     rf"\caption{{AI exposure, wage, and private-sector {DEPVAR}, by age group}}",
     rf"\label{{tab:ca_did_combined{SUF}}}", r"\small",
     r"\begin{tabular}{lcccccc}", r"\toprule",
     r" & \multicolumn{3}{c}{ChatGPT (ref.\ Oct 2022)} "
     r"& \multicolumn{3}{c}{Agentic (ref.\ Apr 2025)} \\",
     r"\cmidrule(lr){2-4} \cmidrule(lr){5-7}",
     r" & (1) & (2) & (3) & (4) & (5) & (6) \\"]
for ag, lab in AGE.items():
    C.append(r"\midrule")
    C.append(rf"\multicolumn{{7}}{{@{{}}l}}{{\textit{{Panel {PANEL[ag]}: "
             rf"ages {lab}}}}} \\")
    for term, tex_lab, _ in TERMS:
        coefs, ses = [], []
        for timing, model in COLS:
            c, se = get(timing, model, term, ag)
            coefs.append(f"{c:+.4f}{star(c, se)}" if np.isfinite(c) else "")
            ses.append(f"({se:.4f})" if np.isfinite(se) else "")
        C.append(tex_lab + " & " + " & ".join(coefs) + r" \\")
        C.append(" & " + " & ".join(ses) + r" \\")
    nc, na = (int(getstat(t, "m1", ag, "nobs")) for t in ("chatgpt", "agentic"))
    oc, oa = (int(getstat(t, "m1", ag, "n_clusters"))
              for t in ("chatgpt", "agentic"))
    C.append(rf"\quad Observations & \multicolumn{{3}}{{c}}{{{nc:,}}} "
             rf"& \multicolumn{{3}}{{c}}{{{na:,}}} \\")
    C.append(rf"\quad Occupations & \multicolumn{{3}}{{c}}{{{oc}}} "
             rf"& \multicolumn{{3}}{{c}}{{{oa}}} \\")
C.append(r"\midrule")
C.append(r"Occupation FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
C.append(r"Month FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
C += [r"\bottomrule", r"\end{tabular}",
      r"\begin{minipage}{\linewidth}\vspace{2pt}\footnotesize",
      rf"\emph{{Notes:}} {ESTLINE} (cell-level {DEPVAR}, private sector). "
      r"Columns (1)--(3): ChatGPT window (Oct 2022 $=k{=}{-}1$, through 2025m4); "
      r"(4)--(6): agentic (Apr 2025 $=k{=}{-}1$, from 2023m7). Each coefficient "
      r"is the average post-period effect relative to the reference month "
      r"($k{=}{-}1$); each pre-period month enters as a separate control. "
      r"M1 = exposure only, M2 = ln wage only, M3 = both $+$ interaction. Treatments "
      r"standardized: $z(\text{exp})$ = Eloundou $\beta$ (pooled), "
      r"$z(\text{lnw})$ = ln full-time-equivalent wage within age group. "
      r"Occupation and month fixed effects in all columns; SE clustered at "
      r"occupation in parentheses; coefficients are $\Delta\log$ per 1 SD. "
      + R2LINE +
      r"$^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.",
      r"\end{minipage}", r"\end{table}"]
combined = TBL / f"table_ca_did_combined{SUF}.tex"
combined.write_text("\n".join(C), encoding="utf-8")
print(f"[wrote {combined}]")

# ---------------- markdown preview ----------------
for ag, lab in AGE.items():
    print(f"\n### Ages {lab}  —  Δlog employment per SD (Post vs. pre)\n")
    print("Cols (1)-(3): **ChatGPT** [M1 exp · M2 wage · M3 full] · "
          "(4)-(6): **Agentic** [M1 · M2 · M3]\n")
    print("| Term | (1) | (2) | (3) | (4) | (5) | (6) |")
    print("|" + "---|" * 7)
    for term, _, md_lab in TERMS:
        cells = []
        for timing, model in COLS:
            c, se = get(timing, model, term, ag)
            cells.append(f"{c:+.4f}{star(c, se)} ({se:.4f})"
                         if np.isfinite(c) else "")
        print(f"| {md_lab} | " + " | ".join(cells) + " |")
    obs = [f"{int(getstat(t, m, ag, 'nobs')):,}" for t, m in COLS]
    occ = [f"{int(getstat(t, m, ag, 'n_clusters'))}" for t, m in COLS]
    pr2 = [f"{getstat(t, m, ag, 'pr2'):.4f}" for t, m in COLS]
    print("| Observations | " + " | ".join(obs) + " |")
    print("| Occupations | " + " | ".join(occ) + " |")
    print("| Pseudo R² | " + " | ".join(pr2) + " |")
