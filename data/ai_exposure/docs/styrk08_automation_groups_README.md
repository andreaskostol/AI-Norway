# styrk08_automation_groups.csv — codebook and decisions

Grouping of STYRK-08 occupations by how Claude is used on their tasks
(automation vs augmentation), for the exposure x usage heterogeneity
analysis in Hernæs & Kostøl. One row per occupation in the canaries
sample (397 codes with an Eloundou et al. 2024 score).

This file is a decision layer. The measurements live in
`styrk08_aei_collaboration.csv` (one row per occupation x platform x
vintage, no decisions taken); this file applies the choices below once,
so the DiD scripts, tables, dashboard packages and paper text read
identical groups. Built by
[build_automation_groups.py](../../analysis/03_mappings/build_automation_groups.py);
never edited by hand.

## Columns

| Column | Description |
|---|---|
| `styrk08` | 4-digit STYRK-08 code, zero-padded string. |
| `automation_share` | Share of the occupation's classified Claude.ai conversations that are automation (directive + feedback loop), pooled over Aug 2025, Nov 2025 and Feb 2026, count-weighted. |
| `n_classified` | Classified Claude.ai conversations behind `automation_share`, summed over the three vintages. 0 if the occupation is absent from the file. |
| `n_vintages` | Number of the three vintages in which the occupation appears (0-3). |
| `usage_pct_mean` | The occupation's share of all Claude.ai usage, mean over the vintages it appears in (percent). |
| `passes_threshold` | 1 if `n_classified` >= 100. |
| `automation_group` | `low`, `mid`, `high`: equal-occupation terciles of `automation_share` among codes passing the threshold; `too_few` otherwise. This is the column the analysis uses. |
| `directive_share` | Pooled share counting only directive conversations as automation (the convention in `build_handa_mapping.py` and the dashboard's usage groups). |
| `directive_group` | Terciles of `directive_share` under the same gate. |
| `automation_share_feb`, `n_feb`, `automation_group_feb` | Feb 2026 vintage alone; gated at `n_feb` >= 100; own terciles. |
| `automation_share_handa`, `automation_group_handa` | The original Handa et al. (2025) vintage (Claude.ai, Dec 2024-Jan 2025); no counts exist, so no gate; terciles among the 312 covered codes. |

Group sizes: 97 / 97 / 97 grouped, 106 `too_few`. Tercile cutpoints of
the pooled share: 0.408 and 0.512 (Feb alone: 0.371 / 0.488; Handa:
0.312 / 0.414; directive-only: 0.362 / 0.467).

## Decisions and evidence

All figures below are computed from `styrk08_aei_collaboration.csv`
(Claude.ai rows unless stated) and the register aggregates for April
2026, ages 21-60, both sectors.

**1. Claude.ai chat only.** The first-party API automation share does
not separate occupations: interquartile range 0.84-1.00 in Feb 2026 and
60 percent of codes at or above 0.90. Its Spearman correlation with the
chat share is 0.13-0.28. The API share of usage remains available in the
measurement file for a delegation measure; it is not used for grouping.

**2. Pool the three counted vintages.** Pairwise Spearman correlations of
the chat automation share are 0.61 (Aug-Nov), 0.70 (Aug-Feb) and 0.75
(Nov-Feb). Pooling Aug and Nov raises the correlation with Feb to 0.78,
and the Spearman-Brown formula implies a reliability of about 0.82 for a
three-vintage pool against 0.61 for one vintage. The instability is a
thin-cell phenomenon: between Nov and Feb the mean absolute change in the
share is 0.138 in the lowest usage tercile (median 150 conversations)
and 0.033 in the highest (median 4,900). The Handa vintage is excluded
from the pool because it has no conversation counts (it was rebuilt from
published shares, so it cannot be gated or weighted) and because it
comes from a different regime: chat only, pre-agentic, mean automation
share 0.36 against 0.45-0.52 in the 2025-26 vintages, directive share
27 percent rising to 39 percent by Aug 2025. Its Spearman correlation
with Feb 2026 is 0.34 overall, 0.14 in the lowest Handa-usage tercile and
0.70 in the highest.

**3. Anthropic's definition of automation.** Directive plus feedback
loop, as in every Economic Index report. The directive-only convention
in `build_handa_mapping.py` gives a within-vintage Spearman of 0.81-0.90
against the Anthropic rule and agrees on the group for 76 percent of
grouped codes; it is carried as `directive_group` for continuity with
the dashboard's usage groups.

**4. Threshold of 100 classified conversations.** A share estimated
from n conversations has a binomial standard error of about 0.09 at
n = 30, 0.05 at 100 and 0.03 at 300, against a tercile width of about
0.10; and the realised noise is larger than binomial because small
occupations rest on two to five shared tasks. Between Nov and Feb, 72
percent of codes keep their tercile without a gate, 75 percent with a
gate at 100 and 75 percent at 300 (Spearman 0.75, 0.82, 0.85), so the
gain flattens above 100 while coverage keeps falling. Without a gate 10
percent of codes have a share of exactly 0 or 1; with it none.
Occupations absent from the file (no task above Anthropic's release
floor of 15 conversations and 5 accounts) and occupations below 100 are
one category, `too_few`. Precedents: Massenkoff & McCrory (2026) set
task exposure to zero below 100 work-related conversations; Brynjolfsson,
Chandar & Chen (2025, Figure A17) keep occupations below the usage floor
as a separate category coded 0.

Coverage with the pooled gate: 291 of 397 codes and 86 percent of
employment. By Eloundou quintile (codes grouped of codes in quintile;
employment share grouped): Q1 24/80, 54 percent; Q2 50/79, 83 percent;
Q3 67/79, 94 percent; Q4 73/79, 96 percent; Q5 77/80, 99 percent. The
`too_few` category is therefore almost entirely a Q1-Q2 phenomenon
(cleaners, carpenters, food-processing operators, drivers, caretakers);
the exposure x automation interaction is identified on Q3-Q5, and Q1
cells (24 grouped codes) should be reported but not leaned on.

**5. Terciles, not quintiles or a continuous ranking.** Rank agreement
between vintages is 0.6-0.75, so a fine ranking is not reproducible;
Tomlinson et al. (2025) make the same point for usage-based coverage
measures, that only relative comparisons between groups are robust.
Terciles are equal-occupation, computed on the gated sample (so noisy
extremes do not set the cutpoints), with ties broken by STYRK-08 code
(the repo's quintile convention).

**6. Universe.** The 397 STYRK-08 codes with an Eloundou score, i.e. the
canaries sample; every occupation in the measurement file is in it.

## Robustness columns

Agreement on the group among codes grouped in both variants: pooled vs
Feb alone 0.81; pooled vs directive-only 0.76; pooled vs Handa 0.52. The
Handa column exists for the appendix comparison with the earlier
literature, not as an alternative baseline.

## How to use

Merge on `styrk08` with the exposure quintiles
(`styrk08_eloundou_beta_mapping.csv`) and interact `automation_group`
with the quintile. Treat `too_few` as its own category with its own
dummy (and its own line in figures), not as missing; it keeps the
occupation universe fixed across specifications. Do not compare
`automation_share` levels across platforms or with the Handa column.

## Provenance and rebuild

Input `styrk08_aei_collaboration.csv` is built on the `arbeidsmarkedet`
branch by `analysis/03_mappings/build_aei_collaboration_mapping.py` from
the Anthropic Economic Index releases (Hugging Face
`Anthropic/EconomicIndex`, task x interaction-type tables for Claude.ai
and the first-party API), walked through the Handa crosswalk chain
(O*NET task -> SOC 2010 -> ISCO-08 -> STYRK-08). It was copied verbatim
to main on 2026-08-26 (sha256 f377f87c...). To rebuild the groups:

```
python analysis/03_mappings/build_automation_groups.py
```

## Interpretation caveats (to be carried into the paper)

1. **The share is conditional on the task still being used in the chat
   channel.** Tasks that automate successfully migrate out of Claude.ai
   into agentic and API surfaces, where they are no longer observed by
   this measure. Between Aug 2025 and Feb 2026 the most automated task
   category (computer and mathematical work) lost 18 percent of its chat
   share while gaining 14 percent in the API (Anthropic Economic Index,
   March 2026), and roughly half of the fall in the aggregate chat
   automation share over the same period is this compositional shift
   rather than within-task change. The measure therefore understates
   automation where it succeeds: `high` is a lower bound on automation
   intensity for occupations whose tasks have moved to production
   workflows, and a fall in an occupation's share over time can mean
   more automation, not less.
2. **Shares of conversations, not of work time; global, and Claude
   only.** The share is the fraction of Claude.ai conversations
   worldwide, mapped to the occupation's tasks, that are automative. It
   is not a Norwegian measure, not a multi-provider measure, and not a
   share of working time: a task with many short conversations and a
   task with few long ones count by conversations alone, and the
   occupation's share of usage (`usage_pct_mean`) is a share of
   conversations, not of hours.

## Known limitations

1. Occupations are inferred from tasks, not observed: a conversation is
   mapped to an O*NET task, and tasks are shared across occupations, so a
   small occupation's share partly reflects other occupations' users.
2. US user base and US task content, as for every usage measure in the
   repo; the crosswalk averages several SOC codes into one STYRK-08 code.
3. Each 2025-26 vintage is a one-week sample (Nov 13-20, Feb 5-12);
   pooling reduces but does not remove week effects such as model
   launches.
4. The automation share moves with the product surface (agentic tools
   run far more automative than chat), so the grouping describes chat
   use in 2025-26, not a fixed property of the occupation.
