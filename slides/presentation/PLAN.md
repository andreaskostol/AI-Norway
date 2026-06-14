# Plan: Presentation of paper/main.tex

A seminar presentation of the AI-Norway paper, built in `slides/presentation/`. Style matches `slides/mapping/` (Metropolis, 16:9, two-author title, progress bar, no slide numbers).

## Design choices

| Choice | Decision |
|---|---|
| Language | English (matches paper) |
| Theme | `\usetheme{metropolis}` with the same `\metroset` and color overrides as `slides/mapping/main.tex` |
| Aspect ratio | 16:9 |
| Slide numbering | `numbering=none` (consistent with mapping deck) |
| Authors | Same two-line `\inst{}` superscript layout as the mapping deck |
| Diagrams / TikZ | Reuse `slides/mapping/tikz_macros.tex` (copy in or `\input` with relative path) |
| Figures | `\includegraphics` from `../../analysis/output/figures/` (use `\graphicspath`) |
| Mapping insertion | Re-use `eloundou.tex`, `eloundou_examples.tex`, `eloundou_manytoone.tex`, `eloundou_distribution.tex` from `slides/mapping/`. Drop Handa, Felten, Anthropic. |
| Navigation buttons | Beamer `\hyperlink` + `\beamerbutton` for the LORV detour (link out, link back) |
| Backup detour | LORV_Fig1 slide placed in `\section*{Backup}` after the references; navigated to via a button on the "Why Eloundou" slide |

## File layout

```
slides/presentation/
  PLAN.md                                   (this file)
  main.tex                                  preamble + section glue
  tikz_macros.tex                           copy of mapping deck's macros
  01_motivation.tex                         METR + literature explosion + our contribution
  02_data_methodology.tex                   A-ordningen, sample, exposure construction
  03_eloundou_focus.tex                     "Why Eloundou" slide with button to LORV detour
  04_mapping.tex                            wraps the four Eloundou-only files from mapping/
  05_results_descriptive.tex                Figure 1 occupation case studies + age-quintile grid
  06_results_diffindiff.tex                 cell-level DiD; explicitly framed as validation
  07_firmfe.tex                             firm-FE Poisson + intensive margin
  08_robustness.tex                         cohort adjustment, macro context
  09_discussion.tex                         alternative explanations, cross-country
  10_conclusion.tex                         takeaway
  90_backup.tex                             LORV_Fig1 detour slide + any extras
  LORV_Fig1_Actual_adoptoin_vs_Exposure.JPG (already present)
  METR_time_horizon.JPG                     (already present)
```

`main.tex` `\input`s each numbered file in order, then loads `90_backup.tex` in a `\section*{Backup}` block.

## Slide-by-slide content

### 1. Opening (3 slides)

**S1. Title.** Same layout as mapping deck: title, subtitle, `\inst{}` superscripts for Hernæs (Frisch) and Kostøl (BI).

**S2. METR: AI capability is accelerating.**
- One figure (`METR_time_horizon.JPG`)
- Two bullets:
  - Length of software tasks an LLM can complete at 50% success has roughly doubled every ~7 months since GPT-2
  - The time horizon entered the multi-hour range in 2025; the long-run trend is the conditioning frame for any labor-market analysis
- No claim that labor effects must track capability; just sets the stakes

**S3. Explosion of exposure-employment papers.**
- A compact table of recent post-2022 evidence with direction of effect:
  | Country | Paper | Direction (youngest workers) |
  |---|---|---|
  | US | Brynjolfsson, Chandar, Chen (2025) | Q5 ages 22–25 decline ~15 log points |
  | Sweden | Lodefalk et al. (2026) | Q5 ages 22–25 decline ~5.5% |
  | UK | Teeselink (2025) | Junior decline; small overall |
  | 39 countries | Teeselink (2026) | Hiring declines; sharper under strict EPL |
  | Denmark | Humlum & Vestergaard (2026) | Null on earnings; firm-adoption explains <⅓ |
  | Finland | Kauhanen et al.\ (2024, 2025, 2026) | Null; demographic |
- One line above the table: "Within two years of ChatGPT, ~10+ papers have already estimated post-2022 exposure-employment relationships."

**S4. Where we come in.**
- Three bullets:
  - We use the most recent data on the market (A-ordningen through 2026m02) and will keep updating
  - We replicate the standard cell-level design (exposure × post-ChatGPT) only to **validate** our setup; we do not claim it as a separate contribution
  - The new contribution: firm × time fixed-effect Poisson on individual register data, and the age 41–50 gradient that the cell design misses
- Norway's institutional features (two-tier bargaining, strong public sector, monthly register coverage of universe) sketched in one line for context

### 2. Why Eloundou (1 slide + detour)

**S5. Why we focus on Eloundou.**
- Two bullets:
  - **De facto standard** after Eloundou et al. (2024) appeared in *Science*: Brynjolfsson, Chandar & Chen (2025) call it "a standard measure in subsequent empirical work"; Teeselink (2025), Humlum & Vestergaard (2026), and Lodefalk et al. (2026) all adopt it as the headline measure
  - **Best validation against actual AI use:** in Lodefalk et al. (2026, Fig 1), Eloundou has \(R^2 = 0.30\) against worker-reported adoption, ahead of Handa (0.26), Felten (0.26), and Webb (0.02)
- Beamer button: `\hyperlink{lorv-detail}{\beamerbutton{See LORV Fig 1}}` in the bottom right
- The "transparency" argument is **not** made — Eloundou itself relies on GPT-4 for task ratings, and Felten is arguably more transparent (pure benchmarks × O*NET importance). No paper argues transparency as the reason, so we don't either.

**S5b (backup-section, hyperlinked from S5).** Full-slide image `LORV_Fig1_Actual_adoptoin_vs_Exposure.JPG` with caption "Lodefalk et al. (2026), Figure 1: AI adoption rate vs. four exposure measures across occupations". A `\beamerbutton{back}` returns to S5 via `\hyperlink{after-eloundou}`.

### 3. Mapping (re-used from slides/mapping/, Eloundou only)

These slides are imported via `\input{../mapping/<file>}` and number roughly S6–S18:

- **S6.** *Why a mapping step is needed* — reused
- **S7.** *O\*NET intro* — reused
- **S8–S12.** *Eloundou concept, code chain, Pharmacist 1-1 worked example, 21-task table, other 1-1 examples table* — reused from `eloundou.tex`
- **S13–S18.** *Worked examples for the five additional occupations* — reused from `eloundou_examples.tex` (Carpenters chain + tasks, Teachers chain + tasks, Lawyers chain + tasks, Economists chain + tasks, IKT chain + 9-specialty table)
- **S19.** *Many-to-one example* — reused from `eloundou_manytoone.tex`
- **S20.** *Eloundou β distribution across Norwegian occupations* — reused from `eloundou_distribution.tex`

The Handa, Felten, Anthropic, and comparison-panel slides from the mapping deck are *not* included.

### 4. Data (2 slides)

**S21. A-ordningen.**
- Universe of formal employment in Norway, ~3.1M workers/month, January 2021 through February 2026
- Variables we use: occupation (STYRK-08 4-digit), age (monthly precision), sector, cash earnings, position percentage, hours, new-job flag
- One line on aggregation: from microdata we build (occ × age × month × sector) cell counts and means; from individual-level data we build (firm × age × occ × month) for the firm-FE design
- Index date: October 2022 = 1, the month before ChatGPT's public release

**S22. Construction of quintiles.**
- One paragraph: rank 397 STYRK-08 codes (where Eloundou maps) by \(\beta\), assign to five equal-sized quintiles on the occupation distribution (each 4-digit code counts once, not weighted by employment)
- Reference back to the distribution slide S20

### 5. Results (5 slides)

**S23. Occupations: software, ICT, customer service.**
- `figure1_occupations_by_age.pdf`
- One line: workers aged 21–30 in software development and ICT systems analysis fall to ~0.81 by early 2026 while older cohorts rise to 1.16 (these are case studies, not the average pattern)

**S24. The full grid: private sector.**
- `figure_emp_decade_private.pdf` (employment by quintile × age, normalised to October 2022)
- One line: no clean youngest-worker negative gradient; instead, a 41–50 gap appears that opens after 2022

**S25. Public sector contrast.**
- `figure_emp_decade_public.pdf`
- One line: no exposure gradient at any age in the public sector

**S26. Cash earnings: no divergence.**
- `figure_kontantlonn_decade_private.pdf`
- One line: consistent with adjustment on the hiring margin under two-tier wage bargaining

**S27. Cell-level DiD (validation, not contribution).**
- Table from `table3_did_cell` (or a clean reproduction): coefficient for Q5 × Post by age bin
- Boxed annotation: "Reported for comparison with US/Sweden/Denmark designs. The novel part of the paper is the firm-FE estimate on the next slide."

### 6. Firm fixed effects (3 slides)

**S28. Empirical specification.**
- Poisson PPML with firm × age, firm × month, age × month fixed effects
- Triple-difference coefficient on $\text{Young}_a \times \text{Post}_t \times \text{Exposure}_q$
- Why Poisson:
  - Many (firm × age × occ × month) cells are zero; $\log(y+1)$ is biased and the coefficient has no clean percentage interpretation
  - Estimates are log-points, directly comparable to BCC and Lodefalk
  - Event-study panels include zero cells without dropping them
- Sample: private foretak, $\geq 20$ workers in ages 22--55, 2021m1--2025m7. SE clustered at firm.

**S29. Event study by age bin.**
- `firm_fe_es_q5_by_age_poisson.pdf`
- One line: 22–25 panel is flat with wide CIs; 41–49 panel drifts to −3 to −5 log points by mid-2025; 26–40 rises

**S30. Intensive margin (table).**
- Three rows from the firm-FE table: log wage, position percentage, log base hours
- One line: small wage and position decline, hours unchanged

### 7. Robustness and discussion (3 slides)

**S31. Population and cohort adjustment.**
- One bullet: per-capita and within-bin composition adjustments leave the pattern intact
- Mini-figure thumbnail from `figureA0b_cohort_sizes.pdf`

**S32. Alternative explanations.**
- Norges Bank rate cycle 2021–2024 (`figureA0a_macro_context.pdf` as inset)
- Post-COVID tech correction
- Seniority-based retention rules
- Worker supply-side reallocation
- One line: in aggregate data the AI signal cannot be separated from these; the firm-FE design narrows the candidate set but does not close it

**S33. Cross-country.**
- Mini-table reading: software-developer young-worker decline is −20% in the US, −44% in Sweden, and approximately −30% in Norway
- Norway lands between US and Sweden by magnitude, consistent with intermediate institutional rigidity

### 8. Closing (2 slides)

**S34. Takeaway.**
- The negative AI exposure gradient in Norway is on 41–50, not on the youngest workers, and only in the private sector
- Cash wages do not move; the adjustment is on hiring
- The firm-FE estimate corroborates the cell-level pattern and adds the within-firm reallocation evidence
- Honest caveat: aggregate post-2022 series cannot separate AI from the monetary, COVID, and seniority shocks that ran in parallel

**S35. Thank you / Questions.**

### Backup (after `\section*{Backup}`)

- **B1. LORV_Fig1** with back button (target of the S5 link)
- **B2.** Reserve for any extra exhibits asked about during Q&A (e.g.\ `figure_microdata_poisson_es_grid.pdf` if questions probe the cell-level event study; sector splits for state vs. municipal; Handa augmentation-share figure for a follow-up question on automation vs. augmentation)

## Navigation implementation notes

Beamer link / button pattern, written once at the top of the deck and used twice on S5:

```latex
% On S5 ("Why we focus on Eloundou"), bottom right:
\hyperlink{lorv-detail}{\beamerbutton{Show LORV Fig 1}}
\hypertarget{after-eloundou}{}

% In backup, around the LORV figure:
\hypertarget{lorv-detail}{}
\includegraphics[width=\textwidth]{LORV_Fig1_Actual_adoptoin_vs_Exposure.JPG}
\hyperlink{after-eloundou}{\beamerbutton{Back}}
```

Both hypertargets are placed via `\hypertarget{...}{}` so that the frame title remains the visible content. No new packages are required; `hyperref` ships with the Metropolis theme.

## Re-use from mapping deck (mechanics)

- Either copy `tikz_macros.tex` into `slides/presentation/` (cleaner, avoids cross-directory `\input` issues), or load it via `\input{../mapping/tikz_macros.tex}`. I default to copy, with a one-line comment in the file noting the source.
- The Eloundou-only `.tex` files (`eloundou.tex`, `eloundou_examples.tex`, `eloundou_manytoone.tex`, `eloundou_distribution.tex`, `onet_intro.tex`, plus the "Why a mapping step is needed" frame which currently lives in mapping's `main.tex`) are loaded via `\input` with the `../mapping/` prefix. They render unchanged because they only depend on `tikz_macros.tex` (which is loaded once in our preamble) and the bundled `eloundou_distribution.pdf` (referenced via `\graphicspath`).
- The frame labelled "Why a mapping step is needed" (lines 54-61 of `slides/mapping/main.tex`) is copied into `02_data_methodology.tex` to keep it without bringing in the four-measure roadmap.

## Critical files

To be created:
- `slides/presentation/main.tex`
- `slides/presentation/tikz_macros.tex` (copy of mapping deck's)
- `slides/presentation/01_motivation.tex` through `slides/presentation/10_conclusion.tex`
- `slides/presentation/90_backup.tex`

To be referenced read-only:
- `slides/mapping/eloundou.tex`, `eloundou_examples.tex`, `eloundou_manytoone.tex`, `eloundou_distribution.tex`, `eloundou_distribution.pdf`, `onet_intro.tex`
- `analysis/output/figures/figure1_occupations_by_age.pdf`
- `analysis/output/figures/figure_emp_decade_private.pdf`, `_public.pdf`
- `analysis/output/figures/figure_kontantlonn_decade_private.pdf`
- `analysis/output/figures/figure_microdata_poisson_es_grid.pdf`
- `analysis/output/figures/figure_firmfe_poisson_es_grid.pdf`, `firm_fe_es_q5_by_age_poisson.pdf`
- `analysis/output/figures/figureA0a_macro_context.pdf`, `figureA0b_cohort_sizes.pdf`
- `analysis/output/tables/table3_did_cell.tex` (if it exists; otherwise reconstruct a 5-line summary)
- `slides/presentation/METR_time_horizon.JPG`
- `slides/presentation/LORV_Fig1_Actual_adoptoin_vs_Exposure.JPG`
- `paper/references.bib` (for citation keys on S3)

## LLM-tell discipline

Inherits the discipline of the mapping deck: noun-phrase titles, no "we now turn to" / "importantly" / "in this slide", no emojis or check marks, terse bullets. Em-dashes replaced with colons as in mapping/. Source notes dropped (no `\sourceline`).

## Verification

1. Compile `slides/presentation/main.tex` with `pdflatex` twice.
2. Walk the deck and verify:
   - All `\hyperlink`/`\hypertarget` pairs match (open S5, click button, confirm jump; click "back" on B1, confirm return).
   - Each figure renders (no missing files).
   - The Eloundou-only mapping insertion compiles cleanly with the `../mapping/` prefix.
   - No \overfull boxes > ~30pt.
3. Cross-check numbers on results slides against the paper (S24 41–50 gap, S30 wage row, S33 cross-country magnitudes).
4. Visual scan at presentation scale (Metropolis defaults satisfy ≥18pt body, ≥24pt titles).

## Out of scope

- Handa, Felten, Anthropic worked examples (covered in mapping deck, not here).
- A Norwegian translation.
- Animation/overlays (`\pause`, `\onslide`). One frame = one slide.
- A separate handout PDF.
- Embedding the cell-level event-study figure or the Handa augmentation grid in the main flow; both go to backup.
