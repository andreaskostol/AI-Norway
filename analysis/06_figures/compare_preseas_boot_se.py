"""Sammenligner cluster-bootstrap-SE vs naive SE for preseas-modellene.

Kjor etter at de to bootstrap-R-scriptsene har fullfort:
  coef_microdata_es_decade_q3_preseas_boot.csv  (har se_naive og se = se_boot)
  coef_microdata_es_decade_agentic_preseas_boot.csv

Rapporterer:
  - Median og spread av se_boot / se_naive per aldersgruppe og kvintil
  - Hvor mange (k, q)-celler skifter signifikans (p < 0.05) med boot-SE
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
COEF = ROOT / "analysis" / "output" / "coefficients"

INPUTS = {
    "ChatGPT (q3)": COEF / "coef_microdata_es_decade_q3_preseas_boot.csv",
    "Agentic":      COEF / "coef_microdata_es_decade_agentic_preseas_boot.csv",
}


def main() -> None:
    for label, path in INPUTS.items():
        if not path.exists():
            print(f"[skip] {label}: {path.name} not found")
            continue
        d = pd.read_csv(path)
        d = d[d["k"] != -1].copy()
        d["ratio"] = d["se"] / d["se_naive"]
        d["z_naive"] = d["coef"].abs() / d["se_naive"]
        d["z_boot"] = d["coef"].abs() / d["se"]
        d["sig_naive"] = d["z_naive"] > 1.96
        d["sig_boot"] = d["z_boot"] > 1.96
        d["lost_sig"] = d["sig_naive"] & ~d["sig_boot"]

        print(f"\n=== {label} ===")
        print(f"  n_boot = {d['n_boot'].iloc[0]}")
        print(f"  cells = {len(d)}")
        print(f"  ratio se_boot/se_naive: "
              f"p10={d['ratio'].quantile(0.1):.3f}  "
              f"median={d['ratio'].median():.3f}  "
              f"mean={d['ratio'].mean():.3f}  "
              f"p90={d['ratio'].quantile(0.9):.3f}")
        print(f"\n  Per (age_group, ai_q): median ratio")
        piv = d.pivot_table(index="age_group", columns="ai_q",
                            values="ratio", aggfunc="median")
        print(piv.round(3).to_string())
        print(f"\n  Cells |coef|/se > 1.96 (5%-sig):")
        print(f"    naive: {d['sig_naive'].sum()}  ({d['sig_naive'].mean():.1%})")
        print(f"    boot:  {d['sig_boot'].sum()}  ({d['sig_boot'].mean():.1%})")
        print(f"    lost sig (naive->boot): {d['lost_sig'].sum()}")


if __name__ == "__main__":
    main()
