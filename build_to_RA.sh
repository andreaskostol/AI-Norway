#!/usr/bin/env bash
# build_to_RA.sh
#
# Rebuild the RA audit package in to_RA/ from the repo.
# Copies the aggregated-pipeline code, the read-only server and microdata.no
# scripts, the 9 paper tables, zips the aggregate input data, and writes
# checksums. It does NOT overwrite the authored docs (README.md, MANIFEST.md,
# HOW_TO_BUILD.md) — edit those by hand.
#
# Usage: bash build_to_RA.sh   (run from the repo root)

set -euo pipefail                                   # stop on any error
cd "$(dirname "$0")"                                # run from the repo root

mkdir -p to_RA/code/{02_parse,03_mappings,05_tables,06_figures,microdata-scripts} \
         to_RA/server_code_readonly to_RA/outputs/tables to_RA/paper   # bundle skeleton

# --- the manuscript the RA checks the code against --------------------------
cp paper/paper_dashboard_v4.tex paper/paper_dashboard_v4.pdf \
   paper/references.bib  to_RA/paper/ 2>/dev/null || true

# --- aggregated local pipeline (commented, runnable on the parsed CSVs) ------
cp analysis/02_parse/parse_microdata_output.py            to_RA/code/02_parse/
cp analysis/03_mappings/build_eloundou_mapping.py \
   analysis/03_mappings/build_combined_styrk_exposure.py  to_RA/code/03_mappings/
cp analysis/05_tables/make_quintile_yagan_table.R \
   analysis/05_tables/make_quintile_top_occupations.py \
   analysis/05_tables/make_did_cell_table.py \
   analysis/05_tables/make_validation_table.py \
   analysis/05_tables/make_did_firmfe_table.py            to_RA/code/05_tables/
for f in microdata_did_cell.R seasonal.R seasonal.py \
         plot_microdata_es_decade.py plot_firmfe_es_decade.py \
         plot_cell_vs_firmfe_q5.py honest_did_quintile_table.R \
         honest_did_bcc_table.R recursive_kiindeks_headline.py \
         plot_recursive_kiindeks.py; do
  cp "analysis/06_figures/$f" to_RA/code/06_figures/      # one figure/regression script
done

# --- microdata.no extraction scripts (read-only; run on microdata.no) --------
cp microdata-scripts/monthly/09a_count_kpos_2021m01_2026m02.mdata \
   microdata-scripts/monthly/09b_kontantlonn_kpos_2021m01_2026m02.mdata \
   microdata-scripts/monthly/09c_stillingspst_kpos_2021m01_2026m02.mdata \
   microdata-scripts/monthly/09f_nyjobb_kpos_2021m01_2026m02.mdata        to_RA/code/microdata-scripts/

# --- individual-level secure-server pipeline (read-only; do not run) ---------
cp analysis-indiv/scripts/*.R                  to_RA/server_code_readonly/
cp analysis-indiv/scripts/README_TRANSFER.md   to_RA/server_code_readonly/ 2>/dev/null || true

# --- frozen mapping inputs + the 9 LaTeX tables the paper \input's -----------
cp data/ai_exposure/styrk08_eloundou_beta_mapping.csv \
   data/ai_exposure/styrk08_all_exposure_measures.csv   to_RA/code/03_mappings/
for t in table1_measures table_quintile_top_occ table_quintile_yagan \
         table3_did_cell table4_did_firmfe table_validation_cell_vs_firmfe \
         table_honest_did table3_crosscountry table_honest_did_bcc; do
  cp "analysis/output/tables/$t.tex" to_RA/outputs/tables/   # one paper table
done

# --- zip the aggregate-analysis input data (stable snapshot for the RA) ------
rm -f to_RA/data_aggregated.zip                     # rebuild fresh
zip -q to_RA/data_aggregated.zip \
  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv \
  microdata-output/09a_count_kpos_2021m01_2026m02_parsed.csv \
  microdata-output/09b_kontantlonn_kpos_2021m01_2026m02_parsed.csv \
  microdata-output/09c_stillingspst_kpos_2021m01_2026m02_parsed.csv \
  microdata-output/09f_nyjobb_kpos_2021m01_2026m02_parsed.csv \
  data/ai_exposure/styrk08_eloundou_beta_mapping.csv \
  data/ai_exposure/styrk08_all_exposure_measures.csv

# --- SHA-256 checksums for code, outputs, frozen inputs, and the data zip ----
{
  echo "# SHA-256 checksums"
  echo "## Bundle code + outputs (relative to to_RA/)"
  ( cd to_RA && find code outputs paper -type f -exec shasum -a 256 {} \; | sort -k2 )
  echo
  echo "## Frozen aggregated inputs (in repo, referenced not copied)"
  shasum -a 256 \
    microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv \
    microdata-output/09a_count_kpos_2021m01_2026m02_parsed.csv \
    microdata-output/09b_kontantlonn_kpos_2021m01_2026m02_parsed.csv \
    microdata-output/09c_stillingspst_kpos_2021m01_2026m02_parsed.csv \
    microdata-output/09f_nyjobb_kpos_2021m01_2026m02_parsed.csv
  echo
  echo "## Data snapshot"
  ( cd to_RA && shasum -a 256 data_aggregated.zip )
} > to_RA/CHECKSUMS.txt

echo "Built to_RA/: $(find to_RA -type f | wc -l) files, $(du -sh to_RA | cut -f1)."
