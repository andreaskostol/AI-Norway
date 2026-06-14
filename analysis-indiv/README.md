# analysis-indiv

Firm-FE event study, triple-difference and per-age DiD on individual-level
Norwegian register data (SSB project **1191**), run on the secure server and
post-processed locally. The whole pipeline is **R** (haven + data.table +
fixest); the original Stata prep pipeline (1183) is archived in
`scripts/stata_archive/`.

**See [`DESIGN_CHOICES.md`](DESIGN_CHOICES.md) for documentation and rationale
of all methodological choices** (estimator, identification, cell unit, sample,
weighting, exposure mapping, the 1191/R migration §21, the 7b/7d
specification-comparison module §22, the full estimation window §23). Each
script header points to the relevant sections.

## Workflow

1. **Develop scripts locally** in `scripts/` (all `.R`).
2. **Validate before transfer** (local, no data needed):
   ```
   Rscript analysis-indiv/scripts/_dryrun_validate.R
   ```
   Checks every raw-data (file, variable, type) reference against
   `datadoc/metadata_scan1191.csv`. Must be all-PASS.
3. **Transfer to the secure server**:
   - All `scripts/*.R` to `H:\Dokumenter\ai_norway_indiv\scripts\`
   - `data/ai_exposure/styrk08_eloundou_beta_mapping.csv` to `F:\1191\<user>\ai_norway_indiv\data\`
   - `data/macro/ssb_population_by_age_quarterly.csv` to `F:\1191\<user>\ai_norway_indiv\data\`
   - `analysis-indiv/occupations_7digits_4digits.csv` (7-digit STYRK → 4-digit
     STYRK-08 crosswalk) to `F:\1191\<user>\ai_norway_indiv\data\`
   - `data/ai_exposure/styrk08_handa_mapping.csv` to
     `F:\1191\<user>\ai_norway_indiv\data\` — **only needed for the BCC
     appendix** (Fig 3 automation/augmentation; script A1).
   - Raw data is already on the server: ameld at `W:\1191\atid\`,
     faste_oppl at `W:\1191\demo\`.
4. **Edit `scripts/0_settings.R`** on the server if your username differs from
   `oysteimh` (the `F:/1191/...` path) or to extend `PERIOD_END_*` when a new
   delivery arrives.
5. **Run the pipeline** — three equivalent modes:
   - **Interactively (RStudio/R GUI on the server, the everyday mode):** open
     `99_master.R`, run the SETUP block once (everything above the
     `KJØRELISTE` banner), then mark and run the individual `run_script()`
     lines you want — one, a few, or all. Each call still invalidates that
     script's stale outputs and updates the run manifest.
   - **Batch:**
     ```
     cd H:\Dokumenter\ai_norway_indiv\scripts
     Rscript 99_master.R              # everything: prep + estimation + heavy
     Rscript 99_master.R prep         # data prep only (scripts 1-5d)
     Rscript 99_master.R est          # estimation only (6-8, excl. 6e/7c)
     Rscript 99_master.R heavy        # compute-heavy CA scripts (6e, 7c)
     Rscript 99_master.R 7b 7d        # substring selectors
     Rscript 99_master.R 6e fe=occ    # key=value args pass through to sub-scripts
     ```
   - **One script directly:** `Rscript 7b_did_byage_fepois.R` (self-contained
     given its inputs; skips the manifest/invalidation bookkeeping).

   A prep-script failure halts everything downstream (fail loudly);
   estimation scripts continue on error with a status summary. Output is
   written into
   `$OUTPUT = H:\Dokumenter\ai_norway_indiv\from_secure_server\`, which mirrors
   the local `from_secure_server/` tree:
   - `SECURE_SERVER_RESULTS.md` (prep sections §1-§6: run metadata, exposure,
     cohort, monthly filter funnel, cell panel, restriction counts)
   - `coefficients/coef_*.csv` (all estimation deliverables)
   - `diagnostics/sample_size_diagnostic.csv`
   - `log_master_R.txt` + per-script `log_*.txt` (replaces Stata's
     `run_log.txt` — inspect these when results look off)
   - `_md_fragments/` — internal scratch; don't transfer.
6. **Transfer the whole `from_secure_server/` folder out** as a single unit and
   replace the local copy (skip `_md_fragments/`).
7. **Check the 7b/7d identical-sample guard**: `sum_count_all` per age_bin must
   be equal in `coef_did_byage_fepois.csv` (firm spec) and the `restricted`
   rows of `coef_did_byage_cellspec.csv` (cell spec). See DESIGN_CHOICES.md §22.
8. **Optional: build figures/manuscript inputs** locally
   (`code/plot_secure_server_results.py`,
   `code/build_manuscript_inputs_indiv.py`).

## Partial reruns

Each prep script writes its section to `$OUTPUT\_md_fragments\section_NN.md`
and calls `rebuild_results_md()` (in `0_settings.R`), which concatenates all
currently-existing fragments into `SECURE_SERVER_RESULTS.md`. Re-running one
script refreshes only its fragment; the master .md is rebuilt cleanly. The §1
timestamp says when each section was last produced. Estimation scripts are
independently re-runnable given `cells_flagged.rds` (`Rscript 7b_did_byage_fepois.R`).

To force a clean rebuild, delete `$OUTPUT\_md_fragments\` and rerun prep.

## What is in the pipeline

- **Headline outcome:** employment count at foretak × age-bin × ai-quintile ×
  month, fit by Poisson (`fixest::fepois`); `log(count + 1)` OLS is
  intentionally avoided (Chen-Roth 2024).
- **Outcomes:** employment, new hires (`count_new` from `arb_start`), log
  monthly wage; alt outcomes (position pct, base hours, overtime) in script 8.
- **Per-age DiD (7b):** firm × quintile + firm × month FE, cluster foretak,
  per decade age group (21-30, 31-40, 41-50, 51-60). Q3 reference.
- **Cell-spec comparison (7d):** the `microdata_did_cell.R` specification
  (yrke4 + month FE, cluster yrke4) on the SAME secure data — variants
  `restricted` (= 7b's sample) and `unrestricted_priv` (bridge to
  microdata.no). DESIGN_CHOICES.md §22.
- **Event studies (6, 6c, 6d)** and **triple-diff (7)**, full window
  k ∈ [KMIN, KMAX] derived from the panel (2021m1-2026m2).
- **Cell-spec event study (6f)** — the dynamic γ_{q,k} counterpart to the 7d
  per-age DiD (yrke4 + month FE, restricted + unrestricted_priv), so the
  7b/7d/cell comparison (DESIGN_CHOICES.md §22) has matching event-study paths.
- **BCC-replication appendix (`A1`–`A3`, group `bcc`)** — full-time private,
  BCC's six age bins (22-25…50-55), re-aggregated from the cached `ameld_filt`
  (no script-3 re-run): A1 descriptive inputs for Figs 1/2/3/5, A2 the
  BCC-binned `in_bcc_full` balanced panel, A3 the Fig-4 Poisson firm-FE event
  study. Plotted by `code/plot_bcc_appendix.py`. Run: `Rscript 99_master.R bcc`.
- **Comparative-advantage replication (6e, 7c)**, compute-heavy, in the
  `heavy` group.
- **Reference month:** October 2022 (event time k = −1); quintile reference
  Q3 (median exposure) everywhere.
- **Sample (main run):** private-sector foretak (sekt = 3), all FT/PT
  (`in_headline_priv`). Flags `in_ft`, `in_ft_priv`, `in_bcc_full` are defined
  in `cells_flagged.rds` for robustness reruns.

## What is *not* in the pipeline

- `log(count + 1)` — replaced by Poisson on the count.
- Virksomhet fixed effects — foretak only (run as robustness if needed).
- Sun-Abraham / Borusyak-Jaravel-Spiess heterogeneous-effects estimators.
- Stata — the `.do` pipeline is frozen in `scripts/stata_archive/` (1183
  provenance only).
