"""Firm-FE CA pooled DiD tables: firm-FE analogue of build_ca_did_tables.py.

For each (outcome, fe_spec) combination produces a combined 4-panel LaTeX
table (one panel per decade age group) with M1/M2/M3 columns for ChatGPT and
agentic anchors. Reads the secure-server outputs:

  coef_ca_did_firmfe.csv             (timing, outcome, fe, age_bin, model,
                                      term, coef, se, n_obs, n_frtk)
  coef_ca_did_firmfe_modelstats.csv  (timing, outcome, fe, age_bin, model,
                                      nobs, n_frtk, pr2)

Usage:  python build_ca_did_firmfe_tables.py
        Produces 4 LaTeX tables in analysis/output/tables/:
            table_ca_did_firmfe_combined_<outcome>_<fe>.tex
        and prints a markdown preview.
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
COEF = BASE / "analysis-indiv" / "from_secure_server" / "coefficients" / \
    "coef_ca_did_firmfe.csv"
STAT = BASE / "analysis-indiv" / "from_secure_server" / "coefficients" / \
    "coef_ca_did_firmfe_modelstats.csv"
TBL = BASE / "analysis" / "output" / "tables"
TBL.mkdir(parents=True, exist_ok=True)

AGE = {1: "21–30", 2: "31–40", 3: "41–50", 4: "51–60"}
COLS = [("chatgpt", "m1"), ("chatgpt", "m2"), ("chatgpt", "m3"),
        ("agentic", "m1"), ("agentic", "m2"), ("agentic", "m3")]
TERMS = [("exp", r"Exposure $\times$ Post", "Exposure × Post"),
         ("wage", r"ln wage $\times$ Post", "ln wage × Post"),
         ("exp_x_wage", r"Exp $\times$ wage $\times$ Post",
          "Exp × wage × Post")]
PANEL = {1: "A", 2: "B", 3: "C", 4: "D"}

DEPVAR = {"count": "employment headcount",
          "nyjobb": r"new hires = round(count $\times$ ny\_jobb)"}

# Two FE variants. The first is the continuous-treatment-faithful spec
# (firm x occupation absorbs firm-occupation baselines); the second is the
# BCC-literal coarse cell.
FE_LABELS = {
    "occ":   r"firm $\times$ occupation",
    "quint": r"firm $\times$ quintile",
}
FE_NAMES = {
    "occ":   "firm-occupation",
    "quint": "firm-quintile",
}


def star(c, se):
    if not (np.isfinite(c) and np.isfinite(se)) or se == 0:
        return ""
    z = abs(c / se)
    return "***" if z > 2.576 else "**" if z > 1.96 else "*" if z > 1.645 else ""


def get(df, outcome, timing, model, term, age, fe):
    r = df[(df.outcome == outcome) & (df.timing == timing) & (df.model == model)
           & (df.term == term) & (df.age_bin == age) & (df.fe == fe)]
    if len(r):
        return float(r.coef.iloc[0]), float(r.se.iloc[0])
    return np.nan, np.nan


def getstat(st, outcome, timing, model, age, fe, col):
    r = st[(st.outcome == outcome) & (st.timing == timing) & (st.model == model)
           & (st.age_bin == age) & (st.fe == fe)]
    if not len(r):
        return np.nan
    return r[col].iloc[0]


def build_combined(df, st, outcome, fe):
    """Produce one combined 4-panel table for given (outcome, fe)."""
    fe_label = FE_LABELS[fe]
    fe_name  = FE_NAMES[fe]
    depvar   = DEPVAR[outcome]

    suf = f"_{outcome}_{fe}"
    C = [r"\begin{table}[H]\centering",
         rf"\caption{{Firm-FE CA pooled DiD on private-sector {depvar}, "
         rf"by age group ({fe_name} cell)}}",
         rf"\label{{tab:ca_did_firmfe_combined{suf}}}", r"\small",
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
                c, se = get(df, outcome, timing, model, term, ag, fe)
                coefs.append(f"{c:+.4f}{star(c, se)}"
                             if np.isfinite(c) else "")
                ses.append(f"({se:.4f})" if np.isfinite(se) else "")
            C.append(tex_lab + " & " + " & ".join(coefs) + r" \\")
            C.append(" & " + " & ".join(ses) + r" \\")
        # Per-panel observation/cluster lines: shared across M1..M3 for the
        # same timing (the sample is the same; only the regressors differ).
        nc = int(getstat(st, outcome, "chatgpt", "m1", ag, fe, "nobs"))
        na = int(getstat(st, outcome, "agentic", "m1", ag, fe, "nobs"))
        oc = int(getstat(st, outcome, "chatgpt", "m1", ag, fe, "n_frtk"))
        oa = int(getstat(st, outcome, "agentic", "m1", ag, fe, "n_frtk"))
        C.append(rf"\quad Observations & \multicolumn{{3}}{{c}}{{{nc:,}}} "
                 rf"& \multicolumn{{3}}{{c}}{{{na:,}}} \\")
        C.append(rf"\quad Foretak (clusters) & "
                 rf"\multicolumn{{3}}{{c}}{{{oc:,}}} "
                 rf"& \multicolumn{{3}}{{c}}{{{oa:,}}} \\")
    C.append(r"\midrule")
    C.append(rf"{fe_label} FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    C.append(r"Firm $\times$ month FE & Yes & Yes & Yes & Yes & Yes & Yes \\")
    C += [r"\bottomrule", r"\end{tabular}",
          r"\begin{minipage}{\linewidth}\vspace{2pt}\footnotesize",
          rf"\emph{{Notes:}} Poisson PPML (\texttt{{fixest::fepois}}) on the "
          rf"individual-level firm panel (private sector, "
          rf"\texttt{{in\_headline\_priv}}). Outcome: cell-level {depvar} "
          rf"summed within (foretak, occupation, age, month). Fixed effects: "
          rf"{fe_label} $+$ firm $\times$ month (BCC eq.\ 4.1 within-firm "
          rf"time-shock control). Columns (1)--(3): ChatGPT window "
          r"(Oct 2022 $=k{=}{-}1$, through 2025m4); (4)--(6): agentic "
          r"(Apr 2025 $=k{=}{-}1$, from 2023m7). Each coefficient is the "
          r"average post-period effect relative to the reference month "
          r"($k{=}{-}1$); each pre-period month enters as a separate "
          r"control. M1 = exposure only, M2 = ln wage only, M3 = both $+$ "
          r"interaction. Treatments standardized: $z(\text{exp})$ = "
          r"Eloundou $\beta$ (pooled across occupations), "
          r"$z(\text{lnw})$ = ln full-time-equivalent wage within age group "
          r"(pre-ChatGPT, native to the secure private sample). SE clustered "
          r"at foretak in parentheses; coefficients are $\Delta\log$ per 1 "
          r"SD. $^{*}p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$.",
          r"\end{minipage}", r"\end{table}"]
    out = TBL / f"table_ca_did_firmfe_combined{suf}.tex"
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
        for fe in ("occ", "quint"):
            build_combined(df, st, outcome, fe)

    # Markdown preview
    for outcome in ("count", "nyjobb"):
        for fe in ("occ", "quint"):
            print(f"\n## Firm-FE DiD ({outcome}, {FE_NAMES[fe]} cell)\n")
            for ag, lab in AGE.items():
                print(f"\n### Ages {lab}\n")
                print("Cols (1)-(3): **ChatGPT** [M1 · M2 · M3] · "
                      "(4)-(6): **Agentic** [M1 · M2 · M3]\n")
                print("| Term | (1) | (2) | (3) | (4) | (5) | (6) |")
                print("|" + "---|" * 7)
                for term, _, md_lab in TERMS:
                    cells = []
                    for timing, model in COLS:
                        c, se = get(df, outcome, timing, model, term, ag, fe)
                        cells.append(f"{c:+.4f}{star(c, se)} ({se:.4f})"
                                     if np.isfinite(c) else "")
                    print(f"| {md_lab} | " + " | ".join(cells) + " |")
                nc = int(getstat(st, outcome, "chatgpt", "m1", ag, fe, "nobs"))
                na = int(getstat(st, outcome, "agentic", "m1", ag, fe, "nobs"))
                oc = int(getstat(st, outcome, "chatgpt", "m1", ag, fe, "n_frtk"))
                oa = int(getstat(st, outcome, "agentic", "m1", ag, fe, "n_frtk"))
                print(f"| Observations | {nc:,} | {nc:,} | {nc:,} | "
                      f"{na:,} | {na:,} | {na:,} |")
                print(f"| Foretak | {oc:,} | {oc:,} | {oc:,} | "
                      f"{oa:,} | {oa:,} | {oa:,} |")


if __name__ == "__main__":
    main()
