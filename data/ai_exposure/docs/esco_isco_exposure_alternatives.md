# ESCO- and ISCO-native AI exposure measures

Literature search conducted 2026-05-23. Question: are there published GenAI
exposure measures built on ESCO skills or directly on ISCO-08 occupations,
that we could use as a robustness alternative to the SOC-based measures
(Eloundou, Felten, Handa, Anthropic 2026) that we currently bring into
STYRK-08 via the BLS SOC -> ISCO crosswalk?

## Motivation

All four headline measures in this paper start from US SOC codes and reach
STYRK-08 via SOC-2018 -> SOC-2010 -> ISCO-08 = STYRK-08. The BLS crosswalk
has 38.8 % partial-match rows and 57.7 % of Eloundou-mapped STYRK codes have
at least one partial-match contributor (paper section 3.3). The literature
also flags this concern explicitly: Gmyrek (2025) shows that national
task lists give meaningfully different exposure than US task lists when run
through the same scoring method. An ESCO- or ISCO-native exposure measure
would short-circuit the SOC -> ISCO step entirely and produce a check on
whether our gradient is an artifact of imported US task content.

## What exists

### 1. Demirev (2026), *Industry and Innovation* — ESCO-based, publicly available

The closest off-the-shelf answer.

- Method: ~27,000 AI product capabilities extracted from corporate press
  releases via a fine-tuned DistilBERT classifier and an LLM (o3-mini),
  matched via cosine similarity to ESCO skills, aggregated to ESCO
  occupations.
- Decomposed into Automation and Augmentation components based on
  press-release language ("replaces" vs. "assists" framing).
- Published at ISCO-08 4-digit level (426 codes) as a CSV on GitHub.
- Paper: Demirev, G. (2026). "AI product innovation and occupational
  exposure: automation and augmentation in commercial AI deployments."
  *Industry and Innovation*. DOI: 10.1080/13662716.2026.2623903
- Code/data repo (CC license, public): https://github.com/demirev/ai-products
- Direct CSV link (the one we would use):
  https://raw.githubusercontent.com/demirev/ai-products/master/results/occupational_exposure_to_ai_products/scored_esco_occupations_isco_4_digit.csv
- File format: two columns, `isco_level_4, ai_product_exposure_score`,
  427 rows including header. Scores are continuous in [0, 1].

### 2. ILO Gmyrek et al. (2025), Working Paper 140 — ISCO-08 native, not ESCO

Methodologically distinct from everything else in the literature.

- Method: combines (a) algorithmic predictions from GPT-4o and Gemini,
  (b) a survey of 1,640 Polish workers assessing automation potential of
  2,861 tasks (anchored on Poland's 6-digit occupational classification,
  which is aligned with ISCO-08 at the 4-digit level), and
  (c) Delphi-style expert validation rounds.
- Outputs four exposure gradients at the ISCO-08 4-digit level.
- Scores are published in Annex Table A1 of WP140 (page 48 onward) but
  do not appear to be released as a downloadable CSV. Would need to be
  extracted from the PDF table or requested from the ILO.
- Paper: Gmyrek, P., Berg, J., Kaminski, K., Konopczynski, F., Ladna, A.,
  Nafradi, B., Roslaniec, K., Troszynski, M. (2025). "Generative AI and
  Jobs: A Refined Global Index of Occupational Exposure." ILO Working
  Paper 140. DOI: 10.54394/HETP0387
- PDF: https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf
- Web page: https://webapps.ilo.org/static/english/intserv/working-papers/wp140/index.html
- Updates the original 2023 ILO index (Gmyrek, Berg, Bescond, ILO WP 96).

### 3. Colombo, Mercorio, Mezzanzanica, Serino (2024) — O*NET-based, not useful for our purpose

"Towards the Terminator Economy: Assessing Job Exposure to AI through LLMs."
arXiv:2407.19204. Uses O*NET as the underlying taxonomy, so reproduces the
same SOC-based measurement problem we already have.

### 4. Pizzinelli, Panton, Mendes Tavares, Cazzaniga, Li (2023) — IMF, ISCO-mapped but O*NET-based

C-AIOE extends Felten/AIOE with a complementarity adjustment and maps to
ISCO. Already cited in our paper (section 2). Used by Kauhanen for Finland.
The underlying task content is still O*NET -> SOC -> ISCO.

## Recommendation

Add **Demirev (2026)** as a fifth exposure measure in the paper.

Rationale:
1. It is the only off-the-shelf measure that is ESCO-native and therefore
   bypasses the SOC -> ISCO crosswalk we worry about in section 5.1.
2. The score is published at ISCO-08 4-digit level, which is identical to
   STYRK-08 4-digit (SSB Notater 17/2011), so no further crosswalk work is
   needed.
3. The automation/augmentation decomposition gives a second check on the
   Handa automation/augmentation split in section 4.3.
4. The CSV is permissively licensed and ready to use.

Trade-offs:
1. Demirev's scoring window (corporate press releases through ~2024) is
   different from Eloundou (early-2023 theoretical) and Anthropic 2026
   (time-weighted Claude usage). This is a feature for robustness, not a
   bug: we want the gradient to survive across different measurement
   approaches.
2. The Demirev measure is built on actual AI products being launched, so it
   captures market-revealed exposure rather than theoretical capability.
   Conceptually closer to Anthropic 2026 / Handa than to Eloundou.
3. Demirev is a single-author paper in a non-top journal; it's not yet a
   canonical reference. Worth noting in the section 5 robustness discussion
   that the measure is recent.

## Practical steps if we add this measure

1. Download `scored_esco_occupations_isco_4_digit.csv` from the GitHub repo
   above into this folder. The data is already a STYRK-08 mapping (since
   STYRK-08 = ISCO-08 at 4-digit), so the only processing step is
   zero-padding the ISCO code to 4 characters if needed.
2. Add to `analysis/03_mappings/` a script that produces
   `styrk08_demirev_mapping.csv` with the same column structure as the
   existing four mapping files (`styrk08`, `quintile`, `exposure_score`,
   plus an automation/augmentation split if we want it).
3. Add a row to `analysis/output/tables/table1_measures.tex` and a column
   to `table2_correlations.tex`.
4. Add a `analysis/06_figures/plot_demirev.py` mirroring `plot_handa.py`
   or `plot_felten.py`. Produces the corresponding age-by-quintile grid.
5. Add a paragraph block in `paper/section4_results.tex` after the
   "Anthropic (2026) job exposure" sub-block.
6. Add a paragraph in `paper/section5_robustness.tex` framing this as the
   "non-SOC-based measure" check, citing Gmyrek (2025) on cross-country
   measurement comparability.

## All sources from the literature search

- ILO Working Paper 140 (Gmyrek et al. 2025):
  https://www.ilo.org/sites/default/files/2025-05/WP140_web.pdf
- ILO 2025 Research Brief (companion to WP140):
  https://www.ilo.org/sites/default/files/2025-05/Research%20brief_GenAI%202025%20Update.pdf
- ILO 2026 Research Brief (follow-up discussion):
  https://www.ilo.org/sites/default/files/2026-03/Research%20Brief_Workers%20exposure%20to%20AI.pdf
- ILO WP140 landing page:
  https://webapps.ilo.org/static/english/intserv/working-papers/wp140/index.html
- ILO original 2023 index (WP96, Gmyrek, Berg, Bescond):
  https://webapps.ilo.org/static/english/intserv/working-papers/wp096/index.html
- Demirev (2026) Industry and Innovation paper:
  https://doi.org/10.1080/13662716.2026.2623903
- Demirev GitHub repo:
  https://github.com/demirev/ai-products
- Direct CSV (ISCO-08 4-digit scores):
  https://raw.githubusercontent.com/demirev/ai-products/master/results/occupational_exposure_to_ai_products/scored_esco_occupations_isco_4_digit.csv
- Colombo et al. (Terminator Economy, 2024):
  https://arxiv.org/pdf/2407.19204
