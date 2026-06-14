# =============================================================================
# _check_smoke_test.R : assertions on the synthetic smoke-test output
# =============================================================================
# LOCAL ONLY. Run after `99_master.R` has completed under AI_NORWAY_TEST_ROOT
# (see _make_synthetic_test_data.R). Verifies:
#   1. Identical-sample guard: sum_count_all per age_bin equal in 7b (firm
#      spec) and 7d restricted (cell spec).
#   2. The planted effect (-30% of Q5 x age 21-30 worker-months post Nov 2022)
#      is recovered as a clearly negative Q5 employment coefficient for
#      age_bin 1 -- by 7b, 7d restricted AND 7d unrestricted -- while
#      age_bin 3 (no planted effect) stays near zero.
# =============================================================================

suppressMessages(library(data.table))

test_root <- Sys.getenv("AI_NORWAY_TEST_ROOT", unset = "")
if (!nzchar(test_root)) stop("Set AI_NORWAY_TEST_ROOT (the smoke-test world).")
outdir <- file.path(test_root, "project", "from_secure_server")
coefs  <- file.path(outdir, "coefficients")
diagd  <- file.path(outdir, "diagnostics")
datad  <- file.path(test_root, "data")

# --- 0. Run manifest + expected diagnostics files exist -----------------------
mani <- fread(file.path(diagd, "run_manifest.csv"))
stopifnot(all(mani$status == "ok"))
cat(sprintf("MANIFEST: %d scripts, all status ok\n", nrow(mani)))
expected <- c("settings_selftest.txt", "monthly_filter_funnel.csv",
              "aggregate_cell_counts.csv", "restriction_funnel.csv",
              "sample_diag_7b.csv", "sample_diag_7d_restricted.csv",
              "7b_7d_sample_comparison.csv", "sample_size_diagnostic.csv",
              "fixest_diag_6_event_study_fepois.csv",
              "fixest_diag_6c_event_study_share_feols.csv",
              "fixest_diag_6d_event_study_continuous_share.csv",
              "fixest_diag_7_triplediff_fepois.csv",
              "fixest_diag_7b_did_byage_fepois.csv",
              "fixest_diag_7d_did_byage_cellspec.csv",
              "fixest_diag_8_alt_outcomes_feols.csv",
              "fixest_diag_6e_ca_es_firmfe.csv",
              "fixest_diag_7c_ca_did_firmfe.csv")
miss <- expected[!file.exists(file.path(diagd, expected))]
stopifnot(length(miss) == 0)
cat("DIAGNOSTICS FILES: all present\n")

# --- 0b. Granular sample comparison all-equal + fixest convergence ------------
cmp <- fread(file.path(diagd, "7b_7d_sample_comparison.csv"))
stopifnot(nrow(cmp) > 0, all(cmp$equal))
cat(sprintf("GRANULAR 7b/7d COMPARISON: %d diagnostic rows, all equal\n", nrow(cmp)))
fd <- rbind(fread(file.path(diagd, "fixest_diag_7b_did_byage_fepois.csv")),
            fread(file.path(diagd, "fixest_diag_7d_did_byage_cellspec.csv")))
stopifnot(all(fd$convergence != "fit_failed"))
cat(sprintf("FIXEST DIAG: %d fits, none failed; dropped obs range %d-%d\n",
            nrow(fd), min(fd$n_dropped_obs), max(fd$n_dropped_obs)))

# --- 0c. Cleaning rules survived the pipeline (planted edge cases) ------------
filt <- list.files(datad, pattern = "^ameld_filt_.*[.]rds$", full.names = TRUE)
af <- rbindlist(lapply(filt, readRDS))
stopifnot(max(af$lonn_overtid_timer, na.rm = TRUE) <= 80)        # cap at 80
stopifnot(max(af$arb_stillingspst,  na.rm = TRUE) <= 200)        # cap at 200
stopifnot(all(nchar(af$yrke4) == 4))
stopifnot("0310" %in% af$yrke4)   # military 0111101 -> 0310 via crosswalk
cat("CLEANING RULES: overtime <= 80, position <= 200, military 0111101 -> 0310\n")

# --- 0d. Balanced panel: zero-filled counts, NA means on synthetic rows -------
cf <- readRDS(file.path(datad, "cells_flagged.rds"))
setDT(cf)
synth <- cf[count_all == 0]
stopifnot(nrow(synth) > 0)                       # balancing produced zeros
stopifnot(all(synth$count_new == 0), all(synth$count_ft == 0))
stopifnot(all(is.na(synth$m_wage_all)))          # means stay NA on synthetic rows
cat(sprintf("BALANCED PANEL: %d synthetic zero rows, counts 0, means NA\n",
            nrow(synth)))

a <- fread(file.path(coefs, "coef_did_byage_fepois.csv"))
b <- fread(file.path(coefs, "coef_did_byage_cellspec.csv"))

cat("--- sum_count_all: 7b vs 7d (restricted) per age_bin ---\n")
chk <- merge(unique(a[, .(age_bin, firm_7b = sum_count_all)]),
             unique(b[variant == "restricted", .(age_bin, cell_7d = sum_count_all)]),
             by = "age_bin")
print(chk)
stopifnot(nrow(chk) == 4L, all(chk$firm_7b == chk$cell_7d))
cat("IDENTICAL-SAMPLE CHECK: PASS\n\n")

cat("--- Q5 employment coefs: age_bin 1 (planted) vs age_bin 3 (placebo) ---\n")
res <- rbind(
    a[outcome == "employment" & ai_q == 5 & age_bin %in% c(1, 3),
      .(source = "7b firm spec", age_bin, coef, se)],
    b[outcome == "employment" & ai_q == 5 & age_bin %in% c(1, 3) &
      variant == "restricted",
      .(source = "7d cell restricted", age_bin, coef, se)],
    b[outcome == "employment" & ai_q == 5 & age_bin %in% c(1, 3) &
      variant == "unrestricted_priv",
      .(source = "7d cell unrestricted", age_bin, coef, se)])
setorder(res, age_bin, source)
print(res)
stopifnot(res[age_bin == 1, .N] == 3L)
stopifnot(res[age_bin == 1, all(coef < -0.15)])   # planted -30% -> ~log(0.7)
stopifnot(res[age_bin == 3, all(abs(coef) < 0.10)])
cat("\nPLANTED-EFFECT CHECK: PASS (Q5 x young strongly negative in all three runs; older ~0)\n")
