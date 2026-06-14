# =============================================================================
# 3_monthly_filtered.R : month-by-month filter of A-ordningen to ages 21-60
# =============================================================================
# For each month of the panel, load minimal columns from the raw ameld file,
# filter to relevant persons + age 21-60 + positive earnings + valid 4-digit
# STYRK-08, save a small monthly file. Aggregation happens in
# 4_aggregate_cells.R.
#
# Inputs:  ameld_path(y, m)              (W:\1191\atid\ameld_statdata_*.dta)
#          $DATA/relevant_ids.rds        (from script 2)
#          $DATA/styrk7_to_styrk4.rds    (from script 1b)
# Outputs: $DATA/ameld_filt_{y}_m{m}.rds (one per month)
#          $OUTPUT/ameld_varlist.txt     (variable list of one ameld file)
#          fragment section_04 + rebuilt SECURE_SERVER_RESULTS.md
#          log_3_monthly_filtered.txt
#
# Memory: one month at a time (~5.9M raw rows -> ~2.5M kept), rm() + gc()
# between months. A missing month file or column STOPS the run (the panel
# must be complete; coverage is pre-verified by _dryrun_validate.R) -- this
# replaces the Stata script's skip-with-zeros behavior.
#
# Design rationale: DESIGN_CHOICES.md sections 5 (foretak vs virksomhet),
# 12 (age binning), 17 (wage rate cleaning), 18 (drop lonn_kontant <= 0).
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}
req("haven"); req("data.table")

open_log("3_monthly_filtered")
cat("== 3_monthly_filtered.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Section 1: Inputs shared across months
# -----------------------------------------------------------------------------

rel <- readRDS(file.path(DATA, "relevant_ids.rds"))
setDT(rel)
rel <- rel[, .(lopenr_person, fm, kvinne, foedselsaar)]
setkey(rel, lopenr_person)
cat(sprintf("relevant_ids: %s persons\n", fmt_int(nrow(rel))))

cw_path <- file.path(DATA, "styrk7_to_styrk4.rds")
if (!file.exists(cw_path))
    stop("styrk7_to_styrk4.rds not found; run 1b_load_styrk7_crosswalk.R first.")
cw <- readRDS(cw_path)
setDT(cw)
setkey(cw, yrke7)

mg <- month_grid()

# Dump the variable list of the first ameld file (markdown reference).
probe_names <- names(read_dta_retry(ameld_path(mg$y[1], mg$m[1]), n_max = 1))
writeLines(c(sprintf("Variable list of %s", ameld_path(mg$y[1], mg$m[1])), "",
             paste0("  ", probe_names)),
           file.path(OUTPUT, "ameld_varlist.txt"))
cat("Variable list saved to ameld_varlist.txt\n")

# -----------------------------------------------------------------------------
# Section 2: Per-month build loop
# -----------------------------------------------------------------------------

diag_rows <- vector("list", nrow(mg))

for (i in seq_len(nrow(mg))) {
    y <- mg$y[i]; m <- mg$m[i]; ym_i <- mg$ym[i]
    rawfile <- ameld_path(y, m)
    outfile <- file.path(DATA, sprintf("ameld_filt_%d_m%d.rds", y, m))

    cat(sprintf("\n=== Processing %d m%d ===\n", y, m))

    # arb_yrke_styrk08 exists from 2023 on; read it where present, purely as a
    # logged cross-check of the yrke7 crosswalk (NOT a mapping source -- it is
    # absent 2021-2022).
    have_s08 <- "arb_yrke_styrk08" %in% names(read_dta_retry(rawfile, n_max = 1))
    cols <- if (have_s08) c(AMELD_COLS, "arb_yrke_styrk08") else AMELD_COLS

    d <- read_dta_cols(rawfile, cols)   # stops on missing file/columns
    n_raw <- nrow(d)

    # --- Restrict to relevant persons (drops most rows immediately) ---
    d <- d[rel, on = "lopenr_person", nomatch = NULL]
    n_after_id <- nrow(d)

    # --- Exact age in years; filter to [AGE_MIN, AGE_MAX] ---
    # am = months since birth; %/% rounds toward -Inf like Stata's floor().
    d[, a_year := (ym_i - fm) %/% 12L]
    d <- d[a_year >= AGE_MIN & a_year <= AGE_MAX]
    n_after_age <- nrow(d)

    # --- Drop spells with missing/non-positive cash earnings ---
    d <- d[!is.na(lonn_kontant) & lonn_kontant > 0]

    # --- Clean position and contracted hours: cap or set missing, keep spell ---
    d[!is.na(arb_stillingspst) & arb_stillingspst > 200, arb_stillingspst := 200]
    d[!is.na(arb_stillingspst) & arb_stillingspst <= 0,  arb_stillingspst := NA_real_]
    d[!is.na(arb_arbeidstid)   & arb_arbeidstid   <= 0,  arb_arbeidstid   := NA_real_]

    # --- Clean wage and hour components ---
    # Hour counts: missing or negative -> 0 (no hours of this type that month);
    # implausibly large lonn_time_antall (> 300) -> missing; overtime capped at 80.
    d[is.na(lonn_time_antall)   | lonn_time_antall   < 0, lonn_time_antall   := 0]
    d[is.na(lonn_overtid_timer) | lonn_overtid_timer < 0, lonn_overtid_timer := 0]
    d[lonn_time_antall   > 300, lonn_time_antall   := NA_real_]
    d[lonn_overtid_timer > 80,  lonn_overtid_timer := 80]
    # Wage rates: keep missing as missing (no hourly arrangement); negative ->
    # missing. No one has a true zero hourly rate, so zero-imputation is wrong.
    d[!is.na(lonn_time) & lonn_time < 0, lonn_time := NA_real_]
    # Fixed pay component: missing or negative -> 0 (no fixed pay reported).
    d[is.na(lonn_fast) | lonn_fast < 0, lonn_fast := 0]

    # --- Map 7-digit STYRK to 4-digit STYRK-08 via crosswalk ---
    # substr(yrke7, 1, 4) is WRONG where the Norwegian 7-digit hierarchy does
    # not line up with STYRK-08 unit groups (military "0111101" -> "0310").
    if (is.numeric(d$arb_yrke)) {
        # Defensive: some vintage delivering the code as numeric would lose
        # leading zeros; restore them before the join.
        d[, arb_yrke := sprintf("%07.0f", arb_yrke)]
    }
    setnames(d, "arb_yrke", "yrke7")
    d[, yrke7 := trimws(yrke7)]
    # Left-pad non-empty codes to 7 chars; empty stays empty (-> unmapped).
    d[nzchar(yrke7), yrke7 := pad0(yrke7, 7)]

    d[cw, on = "yrke7", yrke4 := i.yrke4]
    n_unmapped <- d[is.na(yrke4), .N]
    d <- d[!is.na(yrke4) & nchar(yrke4) == 4]
    cat(sprintf("  yrke7 -> yrke4 crosswalk: dropped %s spells with unmapped yrke7\n",
                fmt_int(n_unmapped)))

    # --- Cross-check crosswalk against SSB's own STYRK-08 recode (2023+) ---
    if (have_s08) {
        chk <- d[nzchar(trimws(arb_yrke_styrk08))]
        if (nrow(chk) > 0) {
            mism <- chk[pad0(arb_yrke_styrk08, 4) != yrke4, .N]
            cat(sprintf("  arb_yrke_styrk08 cross-check: %.2f%% of %s spells differ from crosswalk yrke4\n",
                        100 * mism / nrow(chk), fmt_int(nrow(chk))))
        }
        d[, arb_yrke_styrk08 := NULL]
    }

    # --- Drop spells with missing foretak ID (haven gives "" for str missing) ---
    d <- d[!is.na(lopenr_foretak) & nzchar(lopenr_foretak)]

    # --- Winsorize lonn_kontant upper tail (DESIGN_CHOICES.md section 18) ---
    # A handful of records carry absurd cash earnings (a ~3e9 kr value in yrke4
    # 9112, 2023m7 -- see A1b_wage_spike_diag.R) that would inflate every wage
    # outcome (m_wage_all -> 7b/7d/8/7c). Cap at WINSOR_HI within (yrke4) this
    # month where the occupation has >= WINSOR_MINN spells (so the percentile is
    # below a lone giant), else at the pooled per-month cap. Caps in place; the
    # lower tail (<= 0) was already dropped above.
    if (nrow(d) > 0) {
        pool_cap <- as.numeric(quantile(d$lonn_kontant, WINSOR_HI, names = FALSE))
        caps <- d[, .(n_om = .N,
                      q = as.numeric(quantile(lonn_kontant, WINSOR_HI, names = FALSE))),
                  by = yrke4]
        caps[, cap := fifelse(n_om >= WINSOR_MINN, q, pool_cap)]
        d[caps, on = "yrke4", wcap := i.cap]
        n_wins <- d[lonn_kontant > wcap, .N]
        d[lonn_kontant > wcap, lonn_kontant := wcap]
        d[, wcap := NULL]
        cat(sprintf("  winsorized lonn_kontant: %s spells capped (pooled cap %.0f)\n",
                    fmt_int(n_wins), pool_cap))
    }

    # --- Sector classification (1/2/3 = stat / kommune / private) ---
    d[, frtk_sektor_2014 := trimws(frtk_sektor_2014)]
    d[, sekt := 3L]
    d[frtk_sektor_2014 %chin% c("1110", "1120", "6100"), sekt := 1L]
    d[frtk_sektor_2014 %chin% c("1510", "1520", "6500"), sekt := 2L]

    # --- Full-time flag (>= 100% position) ---
    d[, ft := as.integer(!is.na(arb_stillingspst) & arb_stillingspst >= 100)]

    # --- Base hours = contracted weekly * 4.33 if available, else lonn_time_antall ---
    d[, basehours := fifelse(!is.na(arb_arbeidstid), arb_arbeidstid * 4.33,
                             lonn_time_antall)]
    d[, basepay := lonn_fast + lonn_time]   # NA when lonn_time is NA, as in Stata

    # --- Decade age bins (DESIGN_CHOICES.md section 12) ---
    d[, age_bin := fcase(a_year >= 21 & a_year <= 30, 1L,
                         a_year >= 31 & a_year <= 40, 2L,
                         a_year >= 41 & a_year <= 50, 3L,
                         a_year >= 51 & a_year <= 60, 4L,
                         default = NA_integer_)]
    stopifnot(!anyNA(d$age_bin))

    # --- Triple-diff binary age cut ---
    d[, young := as.integer(a_year >= AGE_MIN & a_year <= YOUNG_MAX)]

    # --- New hire: employment relationship started this calendar month ---
    # arb_start is a daily Stata %d date; haven reads it as Date. A new hire
    # is a spell whose start month equals the status month (same definition
    # as the cell-level ny_jobb from microdata.no ARBLONN_ARB_START).
    stopifnot(inherits(d$arb_start, "Date"))
    d[, arb_start := as.IDate(arb_start)]
    d[, ny_jobb := as.integer(!is.na(arb_start) &
                              year(arb_start) == y & month(arb_start) == m)]
    n_missing_start <- d[is.na(arb_start), .N]

    # --- Keep only what 4_aggregate_cells.R needs ---
    d[, ym := ym_i]
    d <- d[, .(lopenr_person, lopenr_foretak, ym, yrke4, sekt, ft, young,
               age_bin, a_year, lonn_kontant, arb_stillingspst, basehours,
               basepay, lonn_overtid_timer, ny_jobb, kvinne)]

    n_kept <- nrow(d)
    atomic_saveRDS(d, outfile)

    cat(sprintf("  raw=%s  after-id=%s  after-age=%s  kept=%s  (missing arb_start: %s)\n",
                fmt_int(n_raw), fmt_int(n_after_id), fmt_int(n_after_age),
                fmt_int(n_kept), fmt_int(n_missing_start)))
    diag_rows[[i]] <- data.table(
        year = y, month = m, n_raw = n_raw, n_after_id = n_after_id,
        n_after_age = n_after_age, n_kept = n_kept,
        n_unmapped_yrke7 = n_unmapped, n_missing_arb_start = n_missing_start)

    rm(d); invisible(gc(verbose = FALSE))
}

diag <- rbindlist(diag_rows)
atomic_fwrite(diag, file.path(DIAG, "monthly_filter_funnel.csv"))
cat("\nWrote diagnostics/monthly_filter_funnel.csv\n")

# -----------------------------------------------------------------------------
# Section 3: Fragment §4
# -----------------------------------------------------------------------------

write_fragment("04", c(
    "## §4: Monthly filter",
    "",
    sprintf(paste("Per-month row counts after filtering A-ordningen to ages",
                  "%d--%d with positive lonn_kontant, valid 4-digit STYRK-08,",
                  "and non-missing lopenr_foretak. Unmapped = spells dropped at",
                  "the yrke7 crosswalk; missing arb_start inflates nothing but",
                  "undercounts new hires. Full ameld variable list in",
                  "output/ameld_varlist.txt."), AGE_MIN, AGE_MAX),
    "",
    "| Month | Raw rows | After ID filter | After age filter | Kept | Unmapped yrke7 | Missing arb_start |",
    "|---|---:|---:|---:|---:|---:|---:|",
    sprintf("| %dm%d | %s | %s | %s | %s | %s | %s |",
            diag$year, diag$month, fmt_int(diag$n_raw), fmt_int(diag$n_after_id),
            fmt_int(diag$n_after_age), fmt_int(diag$n_kept),
            fmt_int(diag$n_unmapped_yrke7), fmt_int(diag$n_missing_arb_start)),
    "",
    "---",
    ""
))
rebuild_results_md()

cat("\nScript 3 complete. Per-month files saved; section_04 fragment +",
    RESULTS_MD, "rebuilt.\n")
cat("== 3_monthly_filtered.R done ", format(Sys.time()), " ==\n")
close_log()
