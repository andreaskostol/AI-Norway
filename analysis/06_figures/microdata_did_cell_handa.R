# =============================================================================
# microdata_did_cell_handa.R : Cell-level difference-in-differences on the
#                              microdata.no decade-age x sector aggregates, for
#                              the Handa et al. (2025) automation and
#                              augmentation exposure measures.
# =============================================================================
# Appendix counterpart to microdata_did_cell.R. Identical specification and
# panel construction; the only change is the exposure mapping: instead of the
# Eloundou GPT-4 quintile, occupations are ranked by the Handa automation share
# (q_automation_share) and, separately, the Handa augmentation share
# (q_augmentation_share). The script loops over both measures and tags every
# coefficient with a `measure` column so a single artifact feeds the appendix
# table.
#
# Spec (per measure m, sector s, age group a, outcome y):
#   employment / new hires (Poisson):
#     log E[y_{j,t}] = alpha_j + beta_t + sum_{q in 2..5} delta_q * post_t * 1{ai_q(j)=q}
#   log wage (OLS, weighted by headcount): analogous.
#   j = 4-digit STYRK-08 occupation; t = month. Time reference is the baseline
#   month k = -1 (Oct 2022); all post months collapse to "POST", so POST x
#   quintile is the average post effect vs Oct 2022. Quintile reference:
#   ai_q = 1 (lowest exposure). Cluster at occupation.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv
#         data/ai_exposure/styrk08_handa_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_did_cell_handa.csv
#         (schema: measure, sector, age_group, outcome, ai_q, coef, se,
#          p_value, n_obs, n_occ)
# =============================================================================

suppressMessages({                          # quiet package banners
    library(data.table)                     # fast in-memory data wrangling
    library(fixest)                         # fepois/feols: fixed-effect Poisson/OLS
})

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE <- getwd()                             # run this script from the repo root
DATA_FILE <- file.path(BASE, "microdata-output",   # parsed cell aggregates
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",   # occupation -> Handa quintiles
                       "styrk08_handa_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",   # coefficient output
                       "coef_microdata_did_cell_handa.csv")

stopifnot(file.exists(DATA_FILE), file.exists(EXP_FILE))   # fail early if inputs missing

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
ALDER_KEEP  <- c("1", "2", "3", "4")        # decade age groups kept: 0 = <21/missing, 5 = 61+ : dropped
AGE_LABELS  <- c("1" = "Early career (21-30)", "2" = "31-40",   # human-readable labels for the console
                 "3" = "41-50", "4" = "Senior (51-60)")
REF_YM_INT  <- 2022L * 12L + 10L            # October 2022 = last pre-period (year*12+month index)
CUTOFF_DATE <- as.IDate("2026-04-16")       # full window through 2026m4 (data edge)
SECTORS     <- c("2" = 2L, "1" = 1L)        # 2 = private (main), 1 = public (appendix)
# Handa measure name -> quintile column in styrk08_handa_mapping.csv
MEASURES    <- c("automation" = "q_automation_share",
                 "augmentation" = "q_augmentation_share")

# -----------------------------------------------------------------------------
# Load + reshape once (shared across both measures)
# -----------------------------------------------------------------------------
cat("Loading", DATA_FILE, "\n")             # progress message
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",   # read parsed aggregates
                                     sekt = "integer", variable = "character",      # with explicit column types
                                     value = "numeric"))
d[, date := as.IDate(date)]                 # parse the status date (the 16th of each month)
d <- d[date <= CUTOFF_DATE]                 # keep only months up to the data-edge cutoff
d <- d[alder_gr %in% ALDER_KEEP]            # keep only the four decade age groups 21-60

w0 <- dcast(d, date + yrke4 + alder_gr + sekt ~ variable, value.var = "value")   # long -> wide: one column per variable
w0[, ym_int := year(date) * 12L + month(date)]   # integer month index (year*12 + month)
# kk = event-time level: each pre-month its own value, all post months -> "POST",
# ref = k = -1 (Oct 2022). Baseline-month reference, not pooled pre-period.
w0[, kk := fifelse(ym_int > REF_YM_INT, "POST",                  # post months collapse to "POST"
                   as.character(ym_int - REF_YM_INT - 1L))]      # pre months keep own event time (k = -1 at Oct 2022)
# New-hire integer count: ny_jobb is a cell mean (share of workers who are new
# hires); count is the headcount. Their product (rounded) recovers the number of
# new hires. See generate_09_age_decades.py.
w0[, ny_count := as.integer(round(ny_jobb * count))]   # reconstruct integer new-hire count per cell

# -----------------------------------------------------------------------------
# Exposure mapping: both Handa quintile columns, keyed by zero-padded STYRK code
# -----------------------------------------------------------------------------
cat("Loading Handa exposure mapping\n")     # progress message
expall <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))   # read occupation -> Handa quintiles
expall[, yrke4 := sprintf("%04s", styrk08)] # zero-pad STYRK code to 4 digits to match the panel key

# -----------------------------------------------------------------------------
# Balance helper for the count outcomes: every (yrke4 x ym_int) cell present
# within a (sector, age group) slice; missing -> 0. NOT used for the wage OLS.
# -----------------------------------------------------------------------------
balance_counts <- function(sub, value_col) {   # sub = one (sector, age) slice; value_col = "count" or "ny_count"
    yrke4s <- unique(sub$yrke4)             # occupations present in this slice
    yms    <- sort(unique(sub$ym_int))      # months present in this slice
    grid   <- CJ(yrke4 = yrke4s, ym_int = yms)   # full occupation x month grid (every combination)
    grid   <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)   # re-attach quintile
    grid[, kk := fifelse(ym_int > REF_YM_INT, "POST",                  # event-time level on the grid
                         as.character(ym_int - REF_YM_INT - 1L))]       # (same rule as the main panel)
    src    <- sub[, .(val = get(value_col)), by = .(yrke4, ym_int)]    # the observed count per occ x month
    out    <- merge(grid, src, by = c("yrke4", "ym_int"), all.x = TRUE)   # left-join onto the full grid
    out[is.na(val), val := 0L]              # absent cell -> zero count (true zero employment/hires)
    out[, ai_q := factor(ai_q, levels = 1:5)]   # quintile as a 5-level factor (Q1 is the base)
    out                                     # balanced panel ready for fepois
}

# -----------------------------------------------------------------------------
# Coefficient harvesting (adds the measure tag vs the Eloundou version)
# -----------------------------------------------------------------------------
parse_did <- function(fit, measure, sector, age, outcome, n_obs, n_occ) {   # pull POST x quintile coefs out of a fit
    if (is.null(fit)) return(NULL)          # skip cells whose estimation failed
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)   # coefficient table with names as a column
    m  <- regmatches(ct$name, regexec("kk::POST:ai_q::([0-9]+)", ct$name))   # match the POST x quintile terms
    q  <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,   # extract the quintile number
                 integer(1))
    keep <- !is.na(q)                       # rows that are POST x quintile coefficients
    if (!any(keep)) return(NULL)            # nothing to harvest -> skip
    data.table(
        measure = measure, sector = sector, age_group = age, outcome = outcome,   # identifiers (incl. measure)
        ai_q = q[keep],                     # quintile (2..5)
        coef = ct[keep, "Estimate"], se = ct[keep, "Std. Error"],   # point estimate and clustered SE
        p_value = ct[keep, ncol(coeftable(fit))],   # last col = Pr(>|t|)
        n_obs = n_obs, n_occ = n_occ        # observation count and occupation count for this cell
    )
}

fit_pois <- function(dt) {                  # fixed-effect Poisson event study for a balanced count panel
    tryCatch(
        fepois(val ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,   # DV=count; POST x (Q vs Q1); FE: occ + month
               data = dt, cluster = ~yrke4),   # standard errors clustered at the occupation
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })   # return NULL on failure
}

# -----------------------------------------------------------------------------
# Estimate one measure: merge its quintile, then loop sector x age x outcome
# -----------------------------------------------------------------------------
run_measure <- function(measure, qcol) {    # measure = "automation"/"augmentation"; qcol = quintile column
    cat(sprintf("\n############ MEASURE: %s (%s) ############\n", measure, qcol))   # banner per measure
    exp <- expall[!is.na(get(qcol)), .(yrke4, ai_q = as.integer(get(qcol)))]   # keep mapped occupations only
    w <- merge(w0, exp, by = "yrke4")       # inner join: drops 0000 / unmapped
    cat(sprintf("Panel: %d cells, %d occupations, %d months (%s..%s)\n",   # report panel dimensions
                nrow(w), uniqueN(w$yrke4), uniqueN(w$ym_int),
                format(min(w$date)), format(max(w$date))))

    rows <- list()                          # collect harvested coefficient tables for this measure
    for (sec in SECTORS) {                   # loop over sectors (private then public)
        for (a in ALDER_KEEP) {              # loop over the four decade age groups
            slice <- w[sekt == sec & alder_gr == a]   # the (sector, age) subsample
            cat(sprintf("\n=== %s | sector %d, age group %s (%s) ===\n",   # progress header for this cell
                        measure, sec, a, AGE_LABELS[[a]]))

            # --- Employment (Poisson) ---
            bc <- balance_counts(slice, "count")   # balanced occ x month headcount panel
            fit_emp <- fit_pois(bc)         # Poisson event study on employment
            rows[[length(rows) + 1L]] <-    # store the employment POST x quintile coefs
                parse_did(fit_emp, measure, sec, a, "employment", nrow(bc), uniqueN(bc$yrke4))

            # --- New hires (Poisson on integer hire count) ---
            bn <- balance_counts(slice, "ny_count")   # balanced occ x month new-hire-count panel
            fit_nh <- fit_pois(bn)          # Poisson event study on new hires
            rows[[length(rows) + 1L]] <-    # store the new-hires POST x quintile coefs
                parse_did(fit_nh, measure, sec, a, "new_hires", nrow(bn), uniqueN(bn$yrke4))

            # --- Log monthly wage (weighted OLS, unbalanced) ---
            ws <- slice[!is.na(kontantlonn) & kontantlonn > 0 & !is.na(count) & count > 0]   # cells with positive wage and headcount
            ws[, ai_q := factor(ai_q, levels = 1:5)]   # quintile as a 5-level factor (Q1 base)
            ws[, lwage := log(kontantlonn)] # dependent variable = log monthly cash wage
            fit_wage <- tryCatch(
                feols(lwage ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,   # DV=log wage; POST x (Q vs Q1); FE: occ + month
                      data = ws, weights = ~count, cluster = ~yrke4),   # weighted by headcount; clustered at occupation
                error = function(e) { cat("  feols failed:", conditionMessage(e), "\n"); NULL })   # NULL on failure
            rows[[length(rows) + 1L]] <-    # store the wage POST x quintile coefs
                parse_did(fit_wage, measure, sec, a, "log_wage", nrow(ws), uniqueN(ws$yrke4))

            cat(sprintf("  emp n=%d, new_hires n=%d, wage n=%d\n",   # report sample sizes per outcome
                        nrow(bc), nrow(bn), nrow(ws)))
        }
    }
    rbindlist(Filter(Negate(is.null), rows))   # stack this measure's harvested coefficient tables
}

# -----------------------------------------------------------------------------
# Run both measures and write the combined artifact
# -----------------------------------------------------------------------------
all_rows <- list()                          # collect per-measure tables
for (mname in names(MEASURES)) {            # automation, then augmentation
    all_rows[[mname]] <- run_measure(mname, MEASURES[[mname]])   # estimate this measure
}
out <- rbindlist(all_rows)                  # stack both measures
setorder(out, measure, sector, age_group, outcome, ai_q)        # tidy row order

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)   # ensure output dir exists
fwrite(out, OUT_CSV)                        # write the coefficient CSV (feeds the appendix Handa table)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))   # progress message
