"""
Lager en Markdown-tabell fra analysis/output/macro_signals/summary.csv med de samme seriene og gruppene
som overview_0_sammendrag (GROUPS i plot_overview.py). Skriver analysis/output/macro_signals/summary_table.md.
Tabellen limes inn i exploration/macro_signals_norway_2026.md.

Kjor: cd analysis/09_macro_signals && python summary_table.py
"""
import pandas as pd

from plot_overview import GROUPS, OUT

s = pd.read_csv(OUT / "summary.csv")
FREQ = {"M": "måned", "Q": "kvartal", "Y": "år"}


def cell(r):
    if r["class"] == "for kort":
        return "for kort"
    gap = f"{r.gap_last12_pct:+.1f}".replace(".", ",").replace("-", "−")
    return f"{r['class']} ({gap} %, ±{r.band_halfwidth_pct:.0f})"


lines = ["| Serie | Frekvens | Fra | Nov. 2022 | Feb. 2025 |", "|---|---|---|---|---|"]
for head, items in GROUPS:
    lines.append(f"| **{head}** | | | | |")
    for name, label in items:
        g = s[s.series == name]
        if g.empty:
            continue
        a, b = g[g["break"] == "2022m11"].iloc[0], g[g["break"] == "2025m02"].iloc[0]
        lines.append(f"| {label} | {FREQ[a.freq]} | {a.pre_start} | {cell(a)} | {cell(b)} |")
text = "\n".join(lines) + "\n"
(OUT / "summary_table.md").write_text(text, encoding="utf-8")
print(text)
