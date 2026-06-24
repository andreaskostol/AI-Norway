# RA audit package — aggregated microdata.no analysis

This bundle lets a research assistant check the code behind *"Has AI Widened
Employment Gaps? Tracking Early-Career Employment by Occupational Exposure"*
(`paper/paper_dashboard_v4.tex`) against what the paper says. It covers the
aggregated, cell-level pipeline built on Statistics Norway's microdata.no
platform, plus read-only copies of the individual-level secure-server code.

## What to check, and what runs

The task is to read the code and confirm that each number, table, and figure in
the paper is produced by code that does what the text describes (sample, fixed
effects, clustering, weights, time window).

Three layers, two of which you read but cannot run:

1. **microdata.no extraction** (`code/microdata-scripts/*.mdata`). These run only
   inside the microdata.no browser environment on the population registers. You
   read them to confirm the variables, status date (the 16th of each month),
   sector, and age groups. They produce the raw exports that
   `parse_microdata_output.py` turns into the parsed CSVs below.
2. **Aggregated local pipeline** (`code/02_parse`, `code/03_mappings`,
   `code/05_tables`, `code/06_figures`). This runs locally on the parsed,
   cell-level CSVs (no person-level data). Given those frozen inputs it
   reproduces every table and figure listed below.
3. **Secure-server individual-level pipeline** (`server_code_readonly/`). This
   runs only inside the Frisch Centre secure server on person-level register
   records. **Read-only: do not run it.** Its outputs are coefficient CSVs that
   feed the firm-fixed-effects table, the firm-FE figure, the validation table,
   and the 22--25 HonestDiD table.

## Layout

```
to_RA/
  README.md                  this file
  MANIFEST.md                file-by-file inventory
  HOW_TO_BUILD.md            how this package is (re)created
  CHECKSUMS.txt              SHA-256 of code, outputs, paper, and frozen inputs
  data_aggregated.zip        snapshot of the parsed cell-level inputs
  paper/                     the manuscript (tex, pdf, bib) the RA checks code against
  code/
    microdata-scripts/       .mdata extraction (read-only; runs on microdata.no)
    02_parse/                parse raw exports -> long-format CSVs
    03_mappings/             STYRK-08 -> AI-exposure crosswalk + the mapping CSVs
    05_tables/               build the paper's LaTeX tables
    06_figures/              cell-level regressions, seasonal adjustment, plots
  server_code_readonly/      individual-level secure-server pipeline (read-only)
  outputs/tables/            the 9 LaTeX tables the paper \input's
```

The parsed cell-level CSVs that the aggregated pipeline reads are bundled as a
stable snapshot in `data_aggregated.zip` (about 22 MB zipped); unzip it from the
repo root to restore `microdata-output/*.csv` and `data/ai_exposure/*.csv`. The
figure PDFs (about 17 MB) are not copied; they stay in
`analysis/output/figures/`. SHA-256 hashes for the zip, the frozen inputs, and
every bundled file are in `CHECKSUMS.txt`. To recreate the whole package, see
`HOW_TO_BUILD.md` (run `bash build_to_RA.sh` from the repo root).

## Paper -> code map

| Paper element | Built by | Reads | Output |
|---|---|---|---|
| Table 1 (`tab:measures`) exposure-measure coverage (397/97.5%, 352/86.5%) | hand-maintained from `data/ai_exposure/docs/` | exposure mapping CSVs | `outputs/tables/table1_measures.tex` |
| Top occupations per quintile (`tab:quintile_top_occ`) | `code/05_tables/make_quintile_top_occupations.py` | parsed counts + mapping | `table_quintile_top_occ.tex` |
| Table 4 (`tab:quintile_yagan`); abstract/intro "0.1% vs 0.3%" | `code/05_tables/make_quintile_yagan_table.R` | `09_occ_agedecade_sektor_kpos...parsed.csv`, `styrk08_eloundou_beta_mapping.csv` | `table_quintile_yagan.tex` |
| Table 5 (`tab:did_cell`) cell DiD | regression `code/06_figures/microdata_did_cell.R` -> `coef_microdata_did_cell.csv`; table `code/05_tables/make_did_cell_table.py` | parsed counts + mapping | `table3_did_cell.tex` |
| Figure: cell event study (`fig:microdata_poisson_grid`) | `code/06_figures/plot_microdata_es_decade.py` | `coef_microdata_es_decade.csv` | `figure_microdata_poisson_es_grid.pdf` |
| Table 6 (`tab:did_firmfe`) firm-FE DiD | server `server_code_readonly/7b_did_byage_fepois.R` -> `coef_did_byage_fepois.csv`; table `code/05_tables/make_did_firmfe_table.py` | server coefficients (read-only) | `table4_did_firmfe.tex` |
| Figure: firm-FE event study (`fig:firmfe_poisson_grid`) | `code/06_figures/plot_firmfe_es_decade.py` | `coef_event_study_fepois.csv` | `figure_firmfe_poisson_es_grid.pdf` |
| Table 7 (`tab:validation`) cell-vs-firm-FE reconciliation | `code/05_tables/make_validation_table.py` | cell coefs + server coefs (`7d_did_byage_cellspec.R`, `7b`) | `table_validation_cell_vs_firmfe.tex` |
| Figure: cell vs firm-FE (`fig:cell_vs_firmfe_q5`) | `code/06_figures/plot_cell_vs_firmfe_q5.py` | cell + firm-FE coefs | `figure_cell_vs_firmfe_q5_grid.pdf` |
| Table 8 (`tab:honest_did`) HonestDiD 21--30 | `code/06_figures/honest_did_quintile_table.R` | `coef_honest_did_quintile.csv` | `table_honest_did.tex` |
| Appendix (`tab:honest_did_bcc`) HonestDiD 22--25 | `code/06_figures/honest_did_bcc_table.R` | server BCC coefs + full vcov | `table_honest_did_bcc.tex` |
| Section 5.2 dashboard headline; recursive figure (`fig:recursive_kiindeks`) | `code/06_figures/recursive_kiindeks_headline.py` -> `coef_recursive_kiindeks_headline.csv`; plot `plot_recursive_kiindeks.py` | parsed counts + mapping | `figure_recursive_kiindeks_ci.pdf` |
| Cross-country table (`tab:crosscountry`) | hand-maintained from cited papers | external studies | `table3_crosscountry.tex` |
| AI-exposure quintiles (all measures) | `code/03_mappings/build_eloundou_mapping.py`, `build_combined_styrk_exposure.py` | crosswalks + exposure scores | `styrk08_eloundou_beta_mapping.csv`, `styrk08_all_exposure_measures.csv` |
| Seasonal adjustment used throughout | `code/06_figures/seasonal.R` (and `seasonal.py`) | series passed in | (helper) |

`table1_measures.tex` and `table3_crosscountry.tex` are hand-maintained; their
numbers trace to `data/ai_exposure/docs/` and to the external papers cited in the
text, not to a generating script.

## Run order (aggregated pipeline only)

The microdata.no and secure-server layers cannot be run outside their platforms.
Given the frozen parsed CSVs, the local pipeline runs in this order:

1. `code/03_mappings/build_eloundou_mapping.py`, then `build_combined_styrk_exposure.py` (exposure quintiles)
2. `code/06_figures/microdata_did_cell.R` (cell-level event study and DiD coefficients)
3. `code/06_figures/recursive_kiindeks_headline.py` (dashboard headline by vintage)
4. server coefficient CSVs are taken as given (produced inside the secure server by `server_code_readonly/99_master.R`)
5. `code/05_tables/*` and `code/06_figures/honest_did_*.R` (LaTeX tables)
6. `code/06_figures/plot_*.py` (figures)

Each script carries a header block (Purpose, Inputs, Outputs, Usage) and a
plain-English comment on essentially every line.

## Notes from the latest consistency check

- The cross-section change (Table 4 and the abstract "0.1% vs 0.3%") uses the
  mean over the most recent three months (Dec 2025--Feb 2026) relative to October
  2022, the same window as the kiindeksen.no headline index.
- The "about 18 percent" decline for young software developers is -17.7 percent
  per capita; it rounds to 18.
- The 22--25 HonestDiD uses the full clustered variance-covariance matrix from
  the secure server (see `server_code_readonly/` and `honest_did_bcc_table.R`).
