# Replication package: Mouchel (2026) AI exposure on STYRK-08

Self-contained package for building the Mouchel, Bouquet & Sheffi (2026)
evidence-grounded AI exposure measure on Norwegian 4-digit STYRK-08
occupation codes, adding it to the project's combined exposure table, and
producing the Mouchel-vs-Eloundou scatter. Everything runs from this folder
with no reference to the rest of the repository; scripts are verbatim copies
of the pipeline scripts in the main repo (same relative paths, so they run
unchanged from the package root).

Assembled 2026-08-13 by Hernæs & Kostøl for "AI Exposure and
Age-Differentiated Employment: Evidence from Norwegian Register Data."

## What the measure is

Mouchel, Bouquet & Sheffi (2026), "Jobs' AI Exposure Should Be Measured
from Evidence, Not Model Priors" (arXiv:2605.15474, MIT/EPFL), update the
Eloundou et al. (2024) task-level exposure rubric to the 2026 agentic-AI
frontier. Each of the 18,796 O*NET occupation-task pairs is judged by an
ensemble of seven open-weight reasoning models under an E0/E1/E2/E3 rubric
(E1: an agentic system with standard browser/workspace tools halves task
time; E2: needs enterprise integrations; E3: vision capability is the
binding constraint), with each judgment conditioned on evidence retrieved
from ~30,000 news articles and ~24,000 academic abstracts. Task labels map
to beta = 1 (E1), 0.5 (E2/E3), 0 (E0) and aggregate to occupations with
O*NET task-time shares. Two arms are released:

- **A1 "grounded"** (`simple_avg_exposure` in the source file): unweighted
  ensemble mean. Never calibrated on usage data. This is the arm we treat
  as the 2026 counterpart to the Eloundou GPT-4 beta.
- **S0 "calibrated"** (`calibrated_exposure`): ensemble weights fitted
  against Anthropic Economic Index task penetration. Not independent of the
  revealed-usage measures (Handa 2025, Anthropic 2026).

## Package contents

```
run.sh                                     one-command reproduction (bash run.sh)
analysis/03_mappings/
  build_eloundou_mapping.py                Eloundou beta -> STYRK-08 (scatter x-axis)
  build_mouchel_mapping.py                 Mouchel A1 + S0 -> STYRK-08 (the new measure)
  build_combined_styrk_exposure.py         assembles the combined wide table
analysis/06_figures/
  plot_mouchel_vs_eloundou.py              the scatter (PDF + PNG, prints correlations)
data/ai_exposure/
  mouchel/calibrated_occupation_exposure_2026-07-20.csv   Mouchel source scores
  eloundou_occ_level.csv                   Eloundou source scores
  soc_2010_to_2018_crosswalk.xlsx          BLS crosswalk (Nov 2017)
  isco_soc_crosswalk.xls                   BLS crosswalk (Aug 2012, upd. Jun 2015)
  styrk08_codes.csv                        official SSB STYRK-08 code list
  styrk08_felten_mapping.csv               pre-built input to the combined table
  styrk08_handa_mapping.csv                pre-built input to the combined table
  styrk08_job_exposure_mapping.csv         pre-built input to the combined table
  styrk08_relational_mapping.csv           pre-built input to the combined table
```

The four pre-built mapping CSVs are shipped as data because the combined
table carries all measures; their own build scripts live in the main repo
(`analysis/03_mappings/`) and are outside the scope of this package.

## Data provenance

| File | Source | Retrieved |
|---|---|---|
| `mouchel/calibrated_occupation_exposure_2026-07-20.csv` | https://raw.githubusercontent.com/MIT-Work-Analytics-Laboratory/RAG-Exposure/main/results/calibrated/2026-07-20/calibrated_occupation_exposure.csv (also released as HF dataset `MIT-WAL/evidence-grounded-ai-exposure`) | 2026-08-13 |
| `eloundou_occ_level.csv` | https://raw.githubusercontent.com/openai/GPTs-are-GPTs/main/data/occ_level.csv | see main repo |
| `soc_2010_to_2018_crosswalk.xlsx` | https://www.bls.gov/soc/2018/soc_2010_to_2018_crosswalk.xlsx | see main repo |
| `isco_soc_crosswalk.xls` | https://www.bls.gov/soc/isco_soc_crosswalk.xls | see main repo |
| `styrk08_codes.csv` | SSB Klass 7, https://www.ssb.no/klass/klassifikasjoner/7 | see main repo |

MD5 checksums of the shipped inputs:

```
62176c6e840bb197c7a0d0024755f59d  eloundou_occ_level.csv
bf5167b9060f3d39663576670473c459  styrk08_codes.csv
96ef4dccb0f411429bffb5db711e09d7  styrk08_felten_mapping.csv
e7535247a580fb69fca5745ef593b1f5  styrk08_handa_mapping.csv
136fc7c55f2bdac92c3f21427e990e44  styrk08_job_exposure_mapping.csv
5f8fdf162a80efdcaa61a8b0130276ee  styrk08_relational_mapping.csv
9028ccbdb01cc352147d45d8da32238f  isco_soc_crosswalk.xls
8a358b553965e3eb2bde6701d10e6d9e  soc_2010_to_2018_crosswalk.xlsx
1e3615055f04af67349abd54b7059b1b  calibrated_occupation_exposure_2026-07-20.csv
```

## Method: how the scores reach STYRK-08

1. **O*NET -> SOC 2018.** The Mouchel file has 923 O*NET-SOC 2018 detail
   codes (`11-1011.03` etc.); scores are averaged within their 6-digit
   parent SOC 2018 code (798 codes). Same rule as the Eloundou pipeline.
2. **SOC 2018 -> SOC 2010** via the BLS November 2017 crosswalk (one 2018
   code can fan out to several 2010 codes; scores carried to each).
3. **SOC 2010 -> ISCO-08** via the BLS crosswalk, keeping the BLS partial-
   match flag per link as a quality indicator.
4. **ISCO-08 -> STYRK-08** by filtered 4-digit code match against the
   official SSB list. Where several SOC codes land on one STYRK-08 code,
   the score is their unweighted average.
5. **Manual overrides** (identical to the other measures in the project):
   `2223` Sykepleiere and `2224` Vernepleiere copy `2221` Nursing
   professionals; `2267` Ergoterapeuter uses SOC `29-1122` Occupational
   Therapists; `2269` Kiropraktorer mv. uses SOC `29-1011` Chiropractors.
   All overrides are recorded in the `manual_map` column.
6. **Quintiles** are equal-occupation (each 4-digit code counts once):
   `pd.qcut` on `rank(method='first')`, ties broken by code sort order.

## How to run

Requires Python 3.9+ with `pandas`, `openpyxl`, `xlrd`, and `matplotlib`.

```
bash run.sh
```

or run the four scripts in the order listed in `run.sh`. Outputs land
inside the package: the two mapping CSVs and the combined table under
`data/ai_exposure/`, the figure under `analysis/output/figures/`.

The package ships with these outputs already present as reference results;
a fresh run regenerates them in place. At assembly time the regenerated
files were verified byte-identical to the versions in the main repository
(`cmp` on `styrk08_eloundou_beta_mapping.csv`, `styrk08_mouchel_mapping.csv`,
`styrk08_all_exposure_measures.csv`, and the figure PNG).

## Expected results

- `styrk08_mouchel_mapping.csv`: 397 of 407 STYRK-08 codes mapped
  (97.5 %; unmapped: military codes 0110/0210/0310, `0000` unspecified,
  `3439`, and a few specialty services without SOC analogues).
- Scatter sample n = 397; Pearson r = 0.921 and Spearman rho = 0.943
  between `mouchel_grounded` and `eloundou_beta`; 66 % of occupations in
  the same quintile, 99 % within one.
- Grounded (A1) and calibrated (S0) arms correlate rho = 0.994 across
  occupations, so the Anthropic calibration barely moves rankings.
- Levels: mean `mouchel_grounded` = 0.290 vs mean `eloundou_beta` = 0.339;
  the 2026 agentic rubric moves professional-judgment occupations (law,
  economics, auditing, advisory) up and routine clerical occupations
  (switchboard, secretarial) down.

## References

- Mouchel, L., P. Bouquet, Y. Sheffi (2026). "Jobs' AI Exposure Should Be
  Measured from Evidence, Not Model Priors." arXiv:2605.15474.
  Code/data: https://github.com/MIT-Work-Analytics-Laboratory/RAG-Exposure
- Eloundou, T., S. Manning, P. Mishkin, D. Rock (2024). "GPTs are GPTs:
  Labor market impact potential of LLMs." *Science* 384(6702), 1306-1308.
- Full codebook for the combined table: see
  `data/ai_exposure/docs/styrk08_all_exposure_measures_README.md` in the
  main repository.
