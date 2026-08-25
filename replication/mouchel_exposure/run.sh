#!/usr/bin/env bash
# Reproduce the Mouchel (2026) -> STYRK-08 exposure mapping, the combined
# exposure table, and the Mouchel-vs-Eloundou scatter, entirely inside this
# package. Run from the package root:  bash run.sh
set -euo pipefail                       # stop on the first error

# Step 1: rebuild the Eloundou GPT-4 beta mapping (the scatter's x-axis)
# from the raw occupation-level scores and the BLS/SSB crosswalks.
python analysis/03_mappings/build_eloundou_mapping.py

# Step 2: build the Mouchel STYRK-08 mapping (both the grounded A1 arm and
# the calibrated S0 arm) through the same crosswalk chain.
python analysis/03_mappings/build_mouchel_mapping.py

# Step 3: assemble the combined wide exposure table (the file the figures
# and tables key on). The Felten/Handa/Anthropic-2026/relational mappings
# are shipped pre-built as inputs; their own builders live in the main repo.
python analysis/03_mappings/build_combined_styrk_exposure.py

# Step 4: draw the Mouchel-vs-Eloundou scatter (PDF + PNG) and print the
# correlations to the console.
python analysis/06_figures/plot_mouchel_vs_eloundou.py

echo "Done. Outputs:"
echo "  data/ai_exposure/styrk08_eloundou_beta_mapping.csv"
echo "  data/ai_exposure/styrk08_mouchel_mapping.csv"
echo "  data/ai_exposure/styrk08_all_exposure_measures.csv"
echo "  analysis/output/figures/figure_mouchel_vs_eloundou.{pdf,png}"
