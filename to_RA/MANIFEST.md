# Manifest

SHA-256 hashes for every file below are in `CHECKSUMS.txt`. Frozen parsed CSVs
and figure PDFs are not copied into the bundle; their hashes are listed under
"Frozen aggregated inputs" in `CHECKSUMS.txt` and they live in the repo at
`microdata-output/` and `analysis/output/figures/`.

## code/microdata-scripts/ — microdata.no extraction (read-only)
Run only inside microdata.no. Produce the raw monthly cell exports.
- `09a_count_kpos_2021m01_2026m02.mdata` — employment counts, occupation x age x sector, positive-cash filter.
- `09b_kontantlonn_kpos_2021m01_2026m02.mdata` — cash earnings.
- `09c_stillingspst_kpos_2021m01_2026m02.mdata` — contracted hours / FTE share.
- `09f_nyjobb_kpos_2021m01_2026m02.mdata` — new hires.

## code/02_parse/
- `parse_microdata_output.py` — parse raw microdata.no exports into long-format `*_parsed.csv`.

## code/03_mappings/
- `build_eloundou_mapping.py` — STYRK-08 -> Eloundou GPT-4 exposure score and quintile.
- `build_combined_styrk_exposure.py` — master crosswalk joining all exposure measures.
- `styrk08_eloundou_beta_mapping.csv` — frozen Eloundou mapping (regression input).
- `styrk08_all_exposure_measures.csv` — frozen combined exposure table.

## code/05_tables/ — LaTeX table builders
- `make_quintile_yagan_table.R` — Table 4 (cross-sectional quintile change; three-month window).
- `make_quintile_top_occupations.py` — top occupations per quintile.
- `make_did_cell_table.py` — Table 5 (cell DiD).
- `make_did_firmfe_table.py` — Table 6 (firm-FE DiD; reads server coefficients).
- `make_validation_table.py` — Table 7 (cell-vs-firm-FE reconciliation).

## code/06_figures/ — regressions, seasonal adjustment, plots
- `microdata_did_cell.R` — cell-level Poisson event study and DiD; writes the cell coefficient CSVs.
- `seasonal.R`, `seasonal.py` — X-11 seasonal-adjustment helper (frozen 2021--2024 factors).
- `plot_microdata_es_decade.py` — cell event-study figure.
- `plot_firmfe_es_decade.py` — firm-FE event-study figure (server coefficients).
- `plot_cell_vs_firmfe_q5.py` — cell-vs-firm-FE comparison figure.
- `honest_did_quintile_table.R` — Table 8 (HonestDiD 21--30).
- `honest_did_bcc_table.R` — appendix HonestDiD 22--25 (full clustered vcov).
- `recursive_kiindeks_headline.py` — dashboard headline KI-indeks by data vintage.
- `plot_recursive_kiindeks.py` — recursive-headline figure.

## server_code_readonly/ — individual-level secure-server pipeline (read-only)
Numbered pipeline `0_settings.R` through `99_master.R` plus appendix (`A*`) and
diagnostic (`_*`) scripts. Runs only inside the Frisch Centre secure server on
person-level register records. Key scripts the paper depends on:
- `6_event_study_fepois.R` — firm-FE event study.
- `7b_did_byage_fepois.R` — firm-FE DiD by age (feeds Table 6).
- `7d_did_byage_cellspec.R` — cell-spec DiD on individual records (feeds Table 7).
- `99_master.R` — runs the pipeline in order.
- `README_TRANSFER.md` — the original server-transfer note.

## paper/ — the manuscript the RA checks the code against
- `paper_dashboard_v4.tex` — the manuscript source.
- `paper_dashboard_v4.pdf` — the compiled manuscript.
- `references.bib` — the bibliography.

## outputs/tables/ — the 9 LaTeX tables the paper \input's
`table1_measures.tex`, `table_quintile_top_occ.tex`, `table_quintile_yagan.tex`,
`table3_did_cell.tex`, `table4_did_firmfe.tex`,
`table_validation_cell_vs_firmfe.tex`, `table_honest_did.tex`,
`table3_crosscountry.tex`, `table_honest_did_bcc.tex`.
