"""YoY-matched CA pooled DiD tables: counterpart to build_ca_did_yagan_tables.py.

For each outcome produces a combined 4-panel LaTeX table (one panel per
decade age group) with M1/M2/M3 columns for ChatGPT and agentic anchors.

Inputs:
    coef_ca_did_yoy.csv             (outcome, timing, age_group, model,
                                     term, coef, se, n_obs, n_occ)
    coef_ca_did_yoy_modelstats.csv  (outcome, timing, age_group, model,
                                     nobs, n_clusters, r2)

Outputs (2 files): table_ca_did_yoy_combined_<outcome>.tex
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = Path(__file__).resolve().parents[2]
COEF = BASE / "analysis" / "output" / "coefficients" / "coef_ca_did_yoy.csv"
STAT = BASE / "analysis" / "output" / "coefficients" / \
    "coef_ca_did_yoy_modelstats.csv"
TBL  = BASE / "analysis" / "output" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}
COLS = [("chatgpt", "m1"), ("chatgpt", "m2"), ("chatgpt", "m3"),
        ("agentic", "m1"), ("agentic", "m2"), ("agentic", "m3")]
TERMS = [("exp", r"Exposure $\times$ Post"),
         ("wage", r"ln wage $\times$ Post"),
         ("exp_x_wage", r"Exp $\times$ wage $\times$ Post")]
PANEL = {1: "A", 2: "B", 3: "C", 4: "D"}

OUTCOME_LABEL = {
    "count":  "employment headcount",
    "nyjobb": r"new hires = round(count $\times$ ny\_jobb)",
}
VLAB = r"YoY ratio ($y_{c,t} / y_{c, m(t)}^{\,\mathrm{pre}}$)"


def star(c, se):
    if not (np.isfinite(c) and np.isfinite(se)) or se == 0:
        return ""
    z = abs(c / se)
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""


def get(df, timing, model, term, age, outcome):
    r = df[(df.timing == timing) & (df.model == model)
           & (df.term == term) & (df.age_group == age)
           & (df.outcome == outcome)]
    if len(r):
        return float(r.coef.iloc[0]), float(r.se.iloc[0])
    return np.nan, np.nan


def getstat(st, timing, model, age, outcome, col):
    r = st[(st.timing == timing) & (st.model == model)
           & (st.age_group == age) & (st.outcome == outcome)]
    if not len(r):
        return np.nan
    return r[col].iloc[0]


def build_combined(df, st, outcome):
    depvar = OUTCOME_LABEL[outcome]
    suf = f"_{outcome}"

    C = [r"\begin{table}[H]\centering",
         rf"\caption{{YoY-matched CA pooled DiD on private-sector {depvar} "
         rf"({VLAB}), by age group}}",
         rf"\label{{tab:ca_did_yoy_combined{suf}}}", r"\small",
         r"\begin{tabular}{lcccccc}", r"\toprule",
         r" & \multicolumn{3}{c}{ChatGPT (ref.\ Oct 2022)} "
         r"& \multicolumn{3}{c}{Agentic (ref.\ Apr 2025)} \\",
         r"\cmidrule(lr){2-4} \cmidrule(lr){5-7}",
         r" & (1) & (2) & (3) & (4) & (5) & (6) \\"]
    for ag, lab in AGE.items():
        C.append(r"\midrule")
        C.append(rf"\multicolumn{{7}}{{@{{}}l}}{{\textit{{Panel {PANEL[ag]}: "
                 rf"ages {lab}}}}} \\")
        for term, tex_lab in TERMS:
            coefs, ses = [], []
            for timing, model in COLS:
                c, se = get(df, timing, model, term, ag, outcome)
                coefs.append(f"{c:+.4f}{star(c, se)}"
                             if np.isfinite(c) else "")
                ses.append(f"({se:.4f})" if np.isfinite(se) else "")
            C.append(tex_lab + " & " + " & ".join(coefs) + r" \\")
            C.append(" & " + " & ".join(ses) + r" \\")
        nc = int(getstat(st, "chatgpt", "m1", ag, outcome, "nobs"))
        na = int(getstat(st, "agentic", "m1", ag, outcome, "nobs"))
        oc = int(getstat(st, "chatgpt", "m1", ag, outcome, "n_clusters"))
        oa = int(getstat(st, "agentic", "m1", ag, outcome, "n_clusters"))
        C.append(rf"\quad Observations & \multicolumn{{3}}{{c}}{{{nc:,}}} "
                 rf"& \multicolumn{{3}}{{c}}{{{na:,}}} \\")
        C.append(rf"\quad Occupations & \multicolumn{{3}}{{c}}{{{oc}}} "
                 rf"& \multicolumn{{3}}{{c}}{{{oa}}} \\")
    C.append(r"\midrule")
    C.append(r"Occupation FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    C.append(r"Month FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    C += [r"\bottomrule", r"\end{tabular}",
          r"\begin{minipage}{\linewidth}\vspace{2pt}\footnotesize",
          rf"\emph{{Notes:}} Linear OLS (\texttt{{fixest::feols}}) on the "
          rf"microdata.no cell aggregates (private sector, sektor = 2). "
          rf"Outcome is the YoY ratio $y_{{c,t}} / y_{{c, m(t)}}$ where "
          rf"$m(t)$ is the unique pre-window month (within $k \in [-12, -1]$ "
          rf"per anchor) with the same month-of-year as $t$. The pre-window "
          rf"is fixed at $k \in [-12, -1]$, so the baseline never enters "
          rf"the post-treatment region even for $k \geq 12$. Columns "
          r"(1)--(3): ChatGPT window (Oct 2022 $=k{=}{-}1$, through 2025m4); "
          r"(4)--(6): agentic (Apr 2025 $=k{=}{-}1$, from 2023m7). Each "
          r"coefficient is the average post-period effect on the YoY ratio "
          r"relative to the reference month ($k{=}{-}1$). M1 = exposure "
          r"only, M2 = ln wage only, M3 = both $+$ interaction. Treatments "
          r"standardized: $z(\text{exp})$ = Eloundou $\beta$ (pooled), "
          r"$z(\text{lnw})$ = ln full-time-equivalent wage within age group. "
          r"Cells weighted by the pre-window baseline count. SE clustered "
          r"at occupation in parentheses. $^{*}p<0.10$, $^{**}p<0.05$, "
          r"$^{***}p<0.01$.",
          r"\end{minipage}", r"\end{table}"]
    out = TBL / f"table_ca_did_yoy_combined{suf}.tex"
    out.write_text("\n".join(C), encoding="utf-8")
    print(f"[wrote {out}]")
    return out


def main():
    if not COEF.exists():
        sys.exit(f"missing input: {COEF}")
    if not STAT.exists():
        sys.exit(f"missing input: {STAT}")
    df = pd.read_csv(COEF)
    st = pd.read_csv(STAT)

    for outcome in ("count", "nyjobb"):
        build_combined(df, st, outcome)

    # Markdown preview
    for outcome in ("count", "nyjobb"):
        print(f"\n## YoY DiD ({outcome})\n")
        for ag, lab in AGE.items():
            print(f"\n### Ages {lab}\n")
            print("Cols (1)-(3): **ChatGPT** [M1 · M2 · M3] · "
                  "(4)-(6): **Agentic** [M1 · M2 · M3]\n")
            print("| Term | (1) | (2) | (3) | (4) | (5) | (6) |")
            print("|" + "---|" * 7)
            for term, _ in TERMS:
                cells = []
                for timing, model in COLS:
                    c, se = get(df, timing, model, term, ag, outcome)
                    cells.append(f"{c:+.4f}{star(c, se)} ({se:.4f})"
                                 if np.isfinite(c) else "")
                print(f"| {term} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main()
