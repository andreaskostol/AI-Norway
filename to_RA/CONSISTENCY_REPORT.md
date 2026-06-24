# Code–paper consistency report

Audit of `paper/paper_dashboard_v4.tex` against the code in `analysis/` and
`analysis-indiv/`. Checks whether every cited number traces to a code output and
whether each specification (sample, fixed effects, clustering, weights, time
window) matches the prose.

**Verdict: minor discrepancies only — no major ones.**

## Major discrepancies
None. Every cited number traces to a regenerated output or coefficient CSV, and
every specification in the prose matches the generating code.

## Minor discrepancies
1. **Stale HonestDiD footnote (§4.5).** The footnote said the 22–25 HonestDiD
   approximated the variance-covariance matrix as diagonal. The code
   (`honest_did_bcc_table.R`) uses the full clustered vcov from the secure
   server, and Appendix B already said so. **Fixed** in the manuscript.
2. **Software-developer decline rounding (§5.1 / Table 3).** The "about 18
   percent" per-capita decline for young software developers is −17.7 percent;
   it rounds to 18. Cosmetic.
3. **Cross-country direction label.** Table 3 Panel B labels Norway 22–25 as
   "Mixed"; the table note explains it. Wording nuance, no numeric mismatch.

## Coverage gaps (not errors)
- `table1_measures.tex` and `table3_crosscountry.tex` are hand-maintained (no
  generating script). Their numbers trace to `data/ai_exposure/docs/` and to the
  external papers cited in the text.
- "≈3.1 million employment records per month" (§2.1) and the "<5 observations"
  suppression rule are citations to SSB / microdata.no documentation, not code
  outputs. The balanced-panel zero-coding they imply is implemented in
  `microdata_did_cell.R` (`balance_counts`).
- The §2.3 footnote statistic ("35,828 worker-months, 0.023 percent" for code
  0000) is a one-time hand computation; it is not reproduced by a current script.

## Verified numeric claims (verbatim)
- Abstract/intro "0.1% vs 0.3%": `table_quintile_yagan.tex` "Average change" row
  Q5 = +0.08, Q1 = +0.30. Q5−Q1 "Difference vs Q1" = −0.21 (2.38), insignificant.
  374 occupations. Window: mean of Dec 2025–Feb 2026 over Oct 2022, SA, ages
  21–60, private, weighted by Oct 2022 headcount (matches the kiindeksen index).
- §4.2 `table3_did_cell.tex`: 31–40 Q5 = 0.0782*** (paper +0.078); 41–50 Q5 =
  −0.0146 (paper −0.015). Event study: 41–50 reaches −0.083 at 2025-06, ends
  −0.026; 31–40 ends +0.145; 21–30 ends +0.011. Occ+month FE, Poisson, cluster
  occ, 2021m1–2026m2.
- §4.3 `table4_did_firmfe.tex`: 31–40 Q5 = 0.0503*** ; 41–50 Q5 = −0.0206*.
  Firm×quintile and firm×month FE, cluster firm, foretak ≥20 in 21–60 window.
- §4.4 `table_validation_cell_vs_firmfe.tex`: (1)+0.0213 vs (2)+0.0202 (≤0.003);
  size restriction early-career +0.0202→+0.0101; cell→firm-FE 31–40
  +0.0843→+0.0503.
- §4.5 `table_honest_did.tex`: original interval [−0.022, +0.065], breakdown 0.
- §4.6 / Appendix B: 22–25 post avg ≈ −0.029 (≈3 log pts), ends −0.363 by Feb
  2026 (≈35 log pts), opens spring 2025, exceeds the US 15 log pts.
- §5.2 dashboard: vintage 2025-01 KI = +1.685, last (2026-02) KI = −0.230 (paper
  +1.7→−0.2); bootstrap SE 1.77–2.42 (≈2 pp); reproduces dashboard.json −0.23.
- Exposure coverage: Eloundou 397 codes / 97.5%; Handa 352 / 86.5% (confirmed in
  `data/ai_exposure/docs/`).

## Script → output map
| Paper output | Script |
|---|---|
| `table_quintile_top_occ` | `analysis/05_tables/make_quintile_top_occupations.py` |
| `table1_measures` | hand-written (`data/ai_exposure/docs/`) |
| `table_quintile_yagan` (Table 4) | `analysis/05_tables/make_quintile_yagan_table.R` |
| `table3_did_cell` (Table 5) | `analysis/05_tables/make_did_cell_table.py`; regression `analysis/06_figures/microdata_did_cell.R` |
| `table4_did_firmfe` (Table 6) | `analysis/05_tables/make_did_firmfe_table.py`; regression `analysis-indiv/scripts/7b_did_byage_fepois.R` |
| `table_validation_cell_vs_firmfe` (Table 7) | `analysis/05_tables/make_validation_table.py`; `7d_did_byage_cellspec.R`, `7b` |
| `table_honest_did` (Table 8) | `analysis/06_figures/honest_did_quintile_table.R` |
| `table_honest_did_bcc` (App. B) | `analysis/06_figures/honest_did_bcc_table.R` |
| `table3_crosscountry` | hand-written (external studies) |
| `figure_microdata_poisson_es_grid` | `analysis/06_figures/plot_microdata_es_decade.py` |
| `figure_firmfe_poisson_es_grid` | `analysis/06_figures/plot_firmfe_es_decade.py` |
| `figure_cell_vs_firmfe_q5_grid` | `analysis/06_figures/plot_cell_vs_firmfe_q5.py` |
| recursive kiindeks figure (§5.2) | `analysis/06_figures/recursive_kiindeks_headline.py` + `plot_recursive_kiindeks.py` |
