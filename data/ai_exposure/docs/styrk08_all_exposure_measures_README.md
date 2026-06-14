# styrk08_all_exposure_measures.csv — codebook

Combined crosswalk from Norwegian 4-digit STYRK-08 occupation codes to four
AI exposure measures used in Hernæs & Kostøl, "AI Exposure and
Age-Differentiated Employment: Evidence from Norwegian Register Data."

## Contents

407 rows (all 4-digit STYRK-08 codes in the SSB register), 16 columns.
UTF-8, comma-separated, one header row. Missing values are blank.

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
| 15 | `anthropic2026_job_exposure` | Anthropic (2026) `job_exposure` measure. Time-weighted observed Claude usage with an automation penalty; postdates BCC and Kauhanen. |
| 16 | `anthropic2026_q` | Quintile of `anthropic2026_job_exposure`. |

## Coverage

| Measure | Mapped | Coverage |
|---|---|---|
| Eloundou GPT-4 β | 397 / 407 | 97.5 % |
| Felten AIOE (overall + LM sub-index) | 392 / 407 | 96.3 % |
| Handa overall + automation/augmentation | 352 / 407 | 86.5 % |
| Anthropic 2026 `job_exposure` | 388 / 407 | 95.3 % |

Codes with no mapping include the military groups (0110, 0210, 0310), the
"unspecified" code (0000), and a small number of specialty service
occupations whose SOC analogues do not exist or are too narrowly defined
for the underlying scoring exercise. Handa coverage is lowest because
observed Claude usage concentrates in a narrow set of task types and many
occupations have negligible recorded usage.

## How the scores reach STYRK-08

All four measures originate in US SOC codes. The crosswalk runs:

```
SOC 2018 ─(BLS, Nov 2017)─▶ SOC 2010 ─(BLS, Aug 2012, updated Jun 2015)─▶ ISCO-08 ≡ STYRK-08
```

The last step is an identity at the 4-digit level (SSB Notater 17/2011).
Where the BLS crosswalk is one-to-many (multiple SOC codes map to a single
STYRK-08), the score is the unweighted average of the source-SOC scores.
38.8 % of BLS crosswalk rows are partial matches; 57.7 % of the
Eloundou-mapped STYRK-08 codes have at least one partial-match contributor.

The Felten and Handa measures map from SOC 2010 directly; the Eloundou
measure adds the SOC 2018 → SOC 2010 step. Anthropic 2026 was released
mapped to SOC and reaches STYRK-08 through the same crosswalk.

## Quintile construction

Quintiles are computed on each measure's STYRK-08 distribution, with each
4-digit code counting once (equal-occupation quintiles). Q1 contains
roughly 20 % of mapped codes with the lowest scores; Q5 contains the top
20 %. Quintiles are not employment-weighted. For continuous-exposure work,
use the underlying score column rather than the quintile.

## Spearman rank correlations (pairwise intersection)

| Pair | n | ρ |
|---|---|---|
| Eloundou — Felten AIOE | 392 | 0.890 |
| Eloundou — Felten LM | 392 | 0.867 |
| Eloundou — Handa overall | 352 | 0.637 |
| Eloundou — Anthropic 2026 | 388 | 0.782 |
| Felten AIOE — Felten LM | 392 | 0.980 |
| Felten AIOE — Handa overall | 351 | 0.620 |
| Felten AIOE — Anthropic 2026 | 386 | 0.761 |
| Handa overall — Anthropic 2026 | 347 | 0.716 |

The theoretical/ability-based measures (Eloundou and Felten) correlate
strongly with each other; the revealed-usage measures (Handa and
Anthropic 2026) correlate strongly with each other; correlations across
the two families are lower.

## Source files

The combined CSV is built by [build_combined_styrk_exposure.py](../../analysis/03_mappings/build_combined_styrk_exposure.py) from these individual mapping files in the same folder:

- `styrk08_eloundou_beta_mapping.csv` (Eloundou)
- `styrk08_felten_mapping.csv` (Felten, both overall AIOE and LM sub-index)
- `styrk08_handa_mapping.csv` (Handa overall, automation, augmentation)
- `styrk08_job_exposure_mapping.csv` (Anthropic 2026)

To rebuild after updating any of the sources:

```
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

## Crosswalks used

- BLS SOC 2018 → SOC 2010 (November 2017):
  https://www.bls.gov/soc/2018/crosswalks.htm
- BLS SOC 2010 → ISCO-08 (August 2012, updated June 2015):
  https://www.bls.gov/soc/soccrosswalks.htm
- STYRK-08 ≡ ISCO-08 at 4-digit level (SSB Notater 17/2011):
  https://www.ssb.no/klass/klassifikasjoner/7

## Known limitations

1. **SOC→ISCO crosswalk noise.** Because all four measures pass through the
   BLS crosswalk, occupations with many one-to-many or many-to-one mappings
   inherit averaged scores. Under classical measurement error this
   attenuates regression estimates toward zero. See `crosswalk_audit.md`
   for code-level details and `mapping_methodology.md` for the per-measure
   processing decisions.
2. **US task content.** All four measures use US task or skill taxonomies
   (O*NET / Anthropic API data on the US user base). For a non-US
   counterpart see Demirev (2026), which is ESCO-based and already at
   ISCO-08 4-digit level — discussed in `esco_isco_exposure_alternatives.md`
   and recommended for inclusion as a fifth measure.
3. **Quintiles are equal-occupation, not employment-weighted.** Q5 contains
   ~20 % of occupation codes, not ~20 % of workers. If you need
   employment-weighted quintiles, recompute using your own employment
   weights.
4. **`styrk08_name` is in Norwegian.** Use the official ISCO-08 English
   labels if you need English names; they are identical to STYRK-08 at the
   4-digit level (with translation).

## Contact

Øystein Hernæs (Frisch Centre) and Andreas R. Kostøl (BI Norwegian Business
School).
