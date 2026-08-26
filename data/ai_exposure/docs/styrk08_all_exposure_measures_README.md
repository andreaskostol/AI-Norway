# styrk08_all_exposure_measures.csv — codebook

Combined crosswalk from Norwegian 4-digit STYRK-08 occupation codes to seven
AI exposure measures used in Hernæs & Kostøl, "AI Exposure and
Age-Differentiated Employment: Evidence from Norwegian Register Data."

## Contents

407 rows (all 4-digit STYRK-08 codes in the SSB register), 31 columns.
UTF-8, comma-separated, one header row. Missing values are blank.
Columns 26--31 (`relational`, `relational_q`, `ai_exposure_z`,
`relational_z`, `exposure_relational_interaction`, `quadrant`) belong to the
relational-economy extension and are documented in
`relational-economy/INTEGRATION_PLAN.md`.

| # | Column | Description |
|---|---|---|
| 1 | `styrk08` | 4-digit STYRK-08 occupation code, zero-padded string. |
| 2 | `styrk08_name` | Official Norwegian occupation name from the SSB register. |
| 3 | `eloundou_beta` | Eloundou et al. (2024) GPT-4 β exposure score. Theoretical share of tasks where access to an LLM would reduce completion time by ≥50 %. Defined as E₁ + 0.5·E₂. |
| 4 | `eloundou_q` | Quintile of `eloundou_beta`, 1 = least exposed, 5 = most exposed. Equal-occupation quintiles (each STYRK-08 code counts once). |
| 5 | `felten_aioe` | Felten et al. (2021) AI Occupational Exposure (AIOE), overall score. Weighted sum of AI progress on the abilities the occupation requires. |
| 6 | `felten_q` | Quintile of `felten_aioe`. |
| 7 | `felten_aioe_lm` | Felten AIOE Language Modeling sub-index. AI progress restricted to the language-modeling benchmark. Closer in spirit to LLM exposure than the overall AIOE. |
| 8 | `felten_lm_q` | Quintile of `felten_aioe_lm`. |
| 9 | `handa_overall` | Handa et al. (2025) Anthropic Economic Index, overall exposure. Share of Claude.ai conversations associated with the occupation's tasks. |
| 10 | `handa_overall_q` | Quintile of `handa_overall`. |
| 11 | `handa_automation` | Handa share of conversations classified as automation mode (directive: request → output). |
| 12 | `handa_automation_q` | Quintile of `handa_automation`. |
| 13 | `handa_augmentation` | Handa share of conversations classified as augmentation mode (iterative collaboration). |
| 14 | `handa_augmentation_q` | Quintile of `handa_augmentation`. |
| 15 | `anthropic2026_job_exposure` | Anthropic (2026) `job_exposure` ("observed exposure") measure: the time-weighted share of the occupation's tasks with gated, work-related Claude/API usage. Augmentative use counts at half weight (automation and API use at full weight) and tasks are gated on Eloundou feasibility, so it is not pure usage. Postdates BCC and Kauhanen. |
| 16 | `anthropic2026_q` | Quintile of `anthropic2026_job_exposure`. |
| 17 | `mouchel_grounded` | Mouchel, Bouquet & Sheffi (2026) evidence-grounded exposure, arm A1: unweighted mean of an ensemble of open-weight models judging each O*NET task under a 2026 agentic-AI rubric (E0/E1/E2 + vision-dependent E3, β mapped 0/1/0.5/0.5), conditioned on retrieved news and research evidence. Never calibrated on usage data, so it is the theoretical-exposure counterpart to `eloundou_beta` for the 2026 frontier. Vintage 2026-07-20. |
| 18 | `mouchel_grounded_q` | Quintile of `mouchel_grounded`. |
| 19 | `mouchel_calibrated` | Mouchel et al. (2026) arm S0: same grounded task scores, ensemble-weighted by fit against Anthropic Economic Index task penetration. NOT independent of the revealed-usage measures (Handa, Anthropic 2026); use `mouchel_grounded` where independence matters. |
| 20 | `mouchel_calibrated_q` | Quintile of `mouchel_calibrated`. |
| 21 | `microsoft_applicability` | Tomlinson et al. (2025) AI applicability score, release v1.1: 200k de-identified Bing Copilot conversations (US, Jan--Sep 2024) scored against O*NET work activities. Average of the user-goal and AI-action sides; range roughly 0--0.5. A revealed-usage measure from a second provider. |
| 22 | `microsoft_user` | The user-goal side alone: AI assists the user's own work goal (augmentation-flavored). |
| 23 | `microsoft_action` | The AI-action side alone: AI performs the work activity, nonphysical task weights (automation-flavored). |
| 24 | `microsoft_q` | Quintile of `microsoft_applicability`. |
| 25 | `atlas_repr_ratio` | Google ATLAS (2026) Gemini representation ratio: the SOC major group's share of US work-related Gemini interactions divided by its OEWS employment share. Digitized from Figure 1 of the report (no occupation-level ATLAS data is public), so the column varies only across 22 SOC major groups -- no genuine 4-digit variation, and no quintile is assigned. |

## Coverage

| Measure | Mapped | Coverage |
|---|---|---|
| Eloundou GPT-4 β | 397 / 407 | 97.5 % |
| Felten AIOE (overall + LM sub-index) | 392 / 407 | 96.3 % |
| Handa overall + automation/augmentation | 352 / 407 | 86.5 % |
| Anthropic 2026 `job_exposure` | 388 / 407 | 95.3 % |
| Mouchel grounded + calibrated | 397 / 407 | 97.5 % |
| Microsoft applicability (+ user/action sides) | 393 / 407 | 96.6 % |
| ATLAS representation ratio (major-group level) | 403 / 407 | 99.0 % |

Codes with no mapping on any measure include the military groups 0110 and
0210 (0310 is mapped on Eloundou, Anthropic 2026, and Mouchel, but not on
Felten or Handa), the "unspecified" code (0000), and a small number of
specialty service occupations whose SOC analogues do not exist or are too
narrowly defined for the underlying scoring exercise. Handa coverage is lowest because
observed Claude usage concentrates in a narrow set of task types and many
occupations have negligible recorded usage.

Four STYRK-08 codes in the register list are not present as 4-digit codes in
the BLS SOC--ISCO crosswalk: `0000`, `2223`, `2224`, and `3439`. We treat
them as follows:

- `2223` Sykepleiere and `2224` Vernepleiere are manually assigned the
  scores of `2221` Nursing professionals in the Eloundou, Mouchel,
  Microsoft, ATLAS, Handa, and Felten mappings; the source code is
  recorded in `manual_map = 2221`.
- `0000` Uoppgitt / unidentified receives no exposure score and is excluded
  from exposure-quintile analyses. In the parsed analysis aggregates for ages
  21--60 it appears only in January--March 2021 and accounts for 35,828
  worker-months, 0.023 % of worker-months across the two analysis sectors.
- `3439` Andre yrker innen estetiske fag is currently left unmapped. A
  plausible flagged robustness alternative is to map it to ISCO `3435` Other
  artistic and cultural associate professionals, but this is not used in the
  baseline files.

Two overlapping-code Norwegian adaptations are also corrected manually after
checking SSB detailed occupation titles against the BLS titles. `2267`
Ergoterapeuter uses SOC `29-1122` Occupational Therapists rather than
BLS/ISCO 2267 optometrists/ophthalmic opticians. `2269` Kiropraktorer mv.
uses SOC `29-1011` Chiropractors rather than the broad BLS/ISCO 2269
residual health-professional group. These corrections are recorded as
`manual_map = SOC:29-1122` and `manual_map = SOC:29-1011` in the Eloundou,
Mouchel, Microsoft, ATLAS, Handa, and Felten mapping files; the Anthropic
2026 job-exposure file is built with the same overrides but keeps its
compact three-column schema. We do not add a separate optometrist reassignment in the baseline.

## How the scores reach STYRK-08

All measures originate in US SOC codes. The crosswalk runs:

```
SOC 2018 ─(BLS, Nov 2017)─▶ SOC 2010 ─(BLS, Aug 2012, updated Jun 2015)─▶ ISCO-08 ─▶ STYRK-08
```

The last step matches overlapping 4-digit ISCO-08 codes to the official
STYRK-08 list by code. STYRK-08 is based on ISCO-08, but it includes
Norwegian adaptations, so this is a filtered code match rather than a
claim that the two classifications are exactly the same. Where the BLS
crosswalk is one-to-many (multiple SOC codes map to a single STYRK-08),
the score is the unweighted average of the source-SOC scores.
38.8 % of BLS crosswalk rows are partial matches; 57.7 % of the
Eloundou-mapped STYRK-08 codes have at least one partial-match contributor.

The Felten and Handa measures map from SOC 2010 directly; the Eloundou and
Mouchel measures add the SOC 2018 → SOC 2010 step (both are published on
O*NET-SOC 2018 codes, averaged to 6-digit SOC first). Anthropic 2026 was
released mapped to SOC and reaches STYRK-08 through the same crosswalk.
The Microsoft measure is published on detailed SOC 2018 and follows the
same chain. The ATLAS ratio is published only at SOC 2018 major-group
level: every detailed SOC code inherits its group's value before the
crosswalk, so the STYRK-08 column mixes group values where a code draws
on several groups but carries no genuine 4-digit variation.

## Quintile construction

Quintiles are computed on each measure's STYRK-08 distribution, with each
4-digit code counting once (equal-occupation quintiles). Q1 contains
roughly 20 % of mapped codes with the lowest scores; Q5 contains the top
20 %. Quintiles are not employment-weighted. For continuous-exposure work,
use the underlying score column rather than the quintile. The ATLAS column
has no quintile: with only 22 distinct source values, equal-frequency
quintiles would split identical values arbitrarily.

## Spearman rank correlations (pairwise intersection)

| Pair | n | ρ |
|---|---|---|
| Eloundou — Felten AIOE | 392 | 0.889 |
| Eloundou — Felten LM | 392 | 0.867 |
| Eloundou — Handa overall | 352 | 0.635 |
| Eloundou — Anthropic 2026 | 388 | 0.780 |
| Felten AIOE — Felten LM | 392 | 0.980 |
| Felten AIOE — Handa overall | 351 | 0.623 |
| Felten AIOE — Anthropic 2026 | 386 | 0.762 |
| Handa overall — Anthropic 2026 | 347 | 0.715 |
| Mouchel grounded — Eloundou | 397 | 0.943 |
| Mouchel grounded — Felten AIOE | 392 | 0.889 |
| Mouchel grounded — Handa overall | 352 | 0.632 |
| Mouchel grounded — Anthropic 2026 | 388 | 0.774 |
| Mouchel grounded — Mouchel calibrated | 397 | 0.994 |
| Microsoft — Eloundou | 393 | 0.772 |
| Microsoft — Felten AIOE | 388 | 0.747 |
| Microsoft — Handa overall | 349 | 0.599 |
| Microsoft — Anthropic 2026 | 388 | 0.714 |
| Microsoft — Mouchel grounded | 393 | 0.775 |

The theoretical/ability-based measures (Eloundou, Mouchel, and Felten)
correlate strongly with each other; the revealed-usage measures (Handa and
Anthropic 2026) correlate strongly with each other; correlations across
the two families are lower. Rank agreement between Eloundou and usage
data is stable across providers (Anthropic 2026: 0.780, Microsoft Copilot:
0.772, ATLAS/Gemini computed at major-group level: 0.79 over 22 groups;
at STYRK level the coarse ATLAS column gives 0.709 over 397 codes), while
usage measures from different providers agree with each other no more
than with the theoretical family, reflecting their different user bases. The Mouchel grounded and calibrated arms are
nearly identical at the occupation level (ρ = 0.994), so the Anthropic
calibration barely moves occupation rankings. Against Eloundou, the Mouchel
grounded arm keeps 66 % of occupations in the same quintile and 99 % within
one quintile; the agentic 2026 rubric shifts professional-judgment
occupations (law, economics, auditing, advisory) up and routine clerical
occupations (switchboard, secretarial) down.

## Source files

The combined CSV is built by [build_combined_styrk_exposure.py](../../analysis/03_mappings/build_combined_styrk_exposure.py) from these individual mapping files in the same folder:

- `styrk08_eloundou_beta_mapping.csv` (Eloundou)
- `styrk08_felten_mapping.csv` (Felten, both overall AIOE and LM sub-index)
- `styrk08_handa_mapping.csv` (Handa overall, automation, augmentation)
- `styrk08_job_exposure_mapping.csv` (Anthropic 2026)
- `styrk08_mouchel_mapping.csv` (Mouchel grounded A1 + calibrated S0)
- `styrk08_microsoft_mapping.csv` (Microsoft applicability + user/action sides)
- `styrk08_atlas_mapping.csv` (ATLAS representation ratio, major-group level)

To rebuild after updating any of the sources:

```
python analysis/03_mappings/build_eloundou_mapping.py
python analysis/03_mappings/build_handa_mapping.py
python analysis/03_mappings/archive/build_felten_mapping.py
python analysis/03_mappings/build_job_exposure_mapping.py
python analysis/03_mappings/build_mouchel_mapping.py
python analysis/03_mappings/build_microsoft_mapping.py
python analysis/03_mappings/build_atlas_mapping.py
python analysis/03_mappings/build_combined_styrk_exposure.py
```

## Primary sources

- Eloundou, T., S. Manning, P. Mishkin, D. Rock (2024). "GPTs are GPTs:
  Labor market impact potential of LLMs." *Science* 384(6702), 1306–1308.
- Felten, E., M. Raj, R. Seamans (2021). "Occupational, industry, and
  geographic exposure to artificial intelligence: A novel dataset and its
  potential uses." *Strategic Management Journal* 42(12), 2195–2217.
- Handa, K., et al. (2025). "Which Economic Tasks are Performed with AI?
  Evidence from Millions of Claude Conversations." arXiv:2503.04761.
- Anthropic (2026). "Anthropic Economic Index `job_exposure` measure."
  Released March 2026.
  GitHub: https://github.com/anthropics/anthropic-economic-index
- Mouchel, L., P. Bouquet, Y. Sheffi (2026). "Jobs' AI Exposure Should Be
  Measured from Evidence, Not Model Priors." arXiv:2605.15474.
  GitHub: https://github.com/MIT-Work-Analytics-Laboratory/RAG-Exposure
  (occupation-level scores, vintage 2026-07-20; local copy in
  `mouchel/calibrated_occupation_exposure_2026-07-20.csv`).
- Tomlinson, K., S. Jaffe, W. Wang, S. Counts, S. Suri (2025). "Working
  with AI: Measuring the Applicability of Generative AI to Occupations."
  arXiv:2507.07935 (v6 / release v1.1, December 2025). CC BY 4.0.
  GitHub: https://github.com/microsoft/working-with-ai (local copy with
  pinned commit in `microsoft/`).
- Google AI & Economy Research Program (2026). "ATLAS v1.0: Mapping
  Gemini Usage in the Economy." arXiv:2608.00038. No occupation-level
  data release; Figure 1 digitized at SOC major-group level (method and
  validation in `atlas/README.md`).

## Crosswalks used

- BLS SOC 2018 → SOC 2010 (November 2017):
  https://www.bls.gov/soc/2018/crosswalks.htm
- BLS SOC 2010 → ISCO-08 (August 2012, updated June 2015):
  https://www.bls.gov/soc/soccrosswalks.htm
- STYRK-08, based on ISCO-08 with overlapping 4-digit codes matched by code:
  https://www.ssb.no/klass/klassifikasjoner/7

## Known limitations

1. **SOC→ISCO crosswalk noise.** Because all four measures pass through the
   BLS crosswalk, occupations with many one-to-many or many-to-one mappings
   inherit averaged scores. Under classical measurement error this
   attenuates regression estimates toward zero. See `crosswalk_audit.md`
   for code-level details and `mapping_methodology.md` for the per-measure
   processing decisions.
2. **US task content.** All measures use US task or skill taxonomies
   (O*NET) and/or US user bases (Claude, Bing Copilot, Gemini). For a
   non-US counterpart see Demirev (2026), which is ESCO-based and already
   at ISCO-08 4-digit level — discussed in
   `esco_isco_exposure_alternatives.md` and recommended for inclusion as
   an additional measure.
3. **Quintiles are equal-occupation, not employment-weighted.** Q5 contains
   ~20 % of occupation codes, not ~20 % of workers. If you need
   employment-weighted quintiles, recompute using your own employment
   weights.
4. **`styrk08_name` is in Norwegian.** Use official ISCO-08 English labels
   for overlapping codes if you need English names; Norwegian-specific
   STYRK-08 codes need register labels or direct translation.
5. **`atlas_repr_ratio` is major-group-level only.** The 22 source values
   are digitized from a published figure (±0.1 pp) and assigned to every
   detailed code in the group. Use it for group-level contrasts and
   robustness, never for within-group occupation comparisons.

## Contact

Øystein Hernæs (Frisch Centre) and Andreas R. Kostøl (BI Norwegian Business
School).
