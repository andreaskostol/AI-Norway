"""
Simuleringstest av trend_break.py med kjent svar.

Serie: log(y) = 8 + 0,10 t + sesong + AR(1)-feil (rho 0,5, sd 0,05), maaned 2016-01 til 2026-08.
Tre tilfeller: ingen hopp, +20 % og -20 % fra februar 2025. 200 trekninger per tilfelle.
Skriver andel av hver klassifisering til analysis/output/macro_signals/test/test_trend_break.csv og
en eksempelfigur per tilfelle.

Kjor: cd analysis/09_macro_signals && python test_trend_break.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

import trend_break as tb

tb.OUT = Path(__file__).resolve().parents[2] / "analysis" / "output" / "macro_signals" / "test"
rng = np.random.default_rng(1)
idx = pd.period_range("2016-01", "2026-08", freq="M")
t = np.arange(len(idx)) / 12
season = 0.08 * np.sin(2 * np.pi * idx.month / 12)

rows = []
for jump in (0.0, 0.20, -0.20):
    for rep in range(200):
        e, u = np.zeros(len(idx)), rng.normal(0, 0.05, len(idx))
        for i in range(1, len(idx)):
            e[i] = 0.5 * e[i - 1] + u[i]
        y = pd.Series(np.exp(8 + 0.10 * t + season + e + jump * (idx >= pd.Period("2025-02", "M"))), index=idx)
        res = {b: tb.fit_break(y, p) for b, p in tb.BREAKS.items()}
        rows += [{"jump": jump, "rep": rep, "break": b, "class": r[0]["class"], "gap": r[0]["gap_last12_pct"]}
                 for b, r in res.items()]
    tb.plot(y, res, f"synthetic_{int(jump * 100)}", f"Simulert serie, hopp {int(jump * 100)} % fra feb. 2025", "simulert")

df = pd.DataFrame(rows)
out = df.groupby(["jump", "break"])["class"].value_counts(normalize=True).unstack(fill_value=0).round(3)
out["mean_gap"] = df.groupby(["jump", "break"])["gap"].mean().round(1)
out.to_csv(tb.OUT / "test_trend_break.csv")
print(out)
