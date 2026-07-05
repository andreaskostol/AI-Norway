# =============================================================================
# microdata_did_cell.R : Cell-level difference-in-differences on the
#                        microdata.no decade-age x sector aggregates
# =============================================================================
# Collapsed counterpart to microdata_poisson_es.R: instead of an event-study
# path gamma_{q,k}, one post-October-2022 dummy interacted with the Eloundou
# quintile, estimated separately per sector and decade age group, for three
# outcomes.
#
# Spec (per sector s, age group a, outcome y):
#   employment / new hires (Poisson):
#     log E[y_{j,t}] = alpha_j + beta_t + sum_{q in 2..5} delta_q * post_t * 1{ai_q(j)=q}
#   log wage (OLS, weighted by headcount):
#     log wage_{j,t} = alpha_j + beta_t + sum_{q in 2..5} delta_q * post_t * 1{ai_q(j)=q}
#   j = 4-digit STYRK-08 occupation; t = month. Time reference is the baseline
#   month k = -1 (Oct 2022): each pre-month enters as its own event-time level
#   (kk) and all post months collapse to "POST", so POST x quintile is the
#   average post effect vs Oct 2022 -- NOT vs the pooled pre-period. Quintile
#   reference: ai_q = 1 (lowest exposure -- BCC convention; the winter-
#   construction seasonality in Q1 is absorbed by the month FE and the k = -1
#   baseline). Cluster at occupation.
#
# Treatment contrasts: Q2, Q3, Q4, Q5 each vs Q1 -> four coefficients per cell.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_did_cell.csv
#         (schema: sector, age_group, outcome, ai_q, coef, se, p_value, n_obs, n_occ)
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
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",   # occupation -> Eloundou quintile
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",   # coefficient output
                       "coef_microdata_did_cell.csv")

stopifnot(file.exists(DATA_FILE), file.exists(EXP_FILE))   # fail early if inputs missing

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
ALDER_KEEP  <- c("1", "2", "3", "4")        # decade age groups kept: 0 = <21/missing, 5 = 61+ : dropped
AGE_LABELS  <- c("1" = "Early career (21-30)", "2" = "31-40",   # human-readable labels for the console
                 "3" = "41-50", "4" = "Senior (51-60)")
REF_YM_INT  <- 2022L * 12L + 10L            # October 2022 = last pre-period (year*12+month index)
CUTOFF_DATE <- as.IDate("2026-04-16")       # full window through 2026m4 (data
                                            # edge; the 2025m4 pre-agentic cutoff
                                            # was dropped together with the
                                            # secure-zone 7b/7d runs -- see
                                            # analysis-indiv/DESIGN_CHOICES.md s.23)
SECTORS     <- c("2" = 2L, "1" = 1L)        # 2 = private (main), 1 = public (appendix)

# -----------------------------------------------------------------------------
# Load + reshape (long -> wide on `variable`)
# -----------------------------------------------------------------------------
cat("Loading", DATA_FILE, "\n")             # progress message
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",   # read parsed aggregates
                                     sekt = "integer", variable = "character",      # with explicit column types
                                     value = "numeric"))
d[, date := as.IDate(date)]                 # parse the status date (the 16th of each month)
d <- d[date <= CUTOFF_DATE]                 # keep only months up to the data-edge cutoff
d <- d[alder_gr %in% ALDER_KEEP]            # keep only the four decade age groups 21-60

w <- dcast(d, date + yrke4 + alder_gr + sekt ~ variable, value.var = "value")   # long -> wide: one column per variable
w[, ym_int := year(date) * 12L + month(date)]   # integer month index (year*12 + month)
# kk = event-time level: each pre-month its own value, all post months -> "POST",
# ref = k = -1 (Oct 2022). Baseline-month reference, not pooled pre-period.
w[, kk := fifelse(ym_int > REF_YM_INT, "POST",                  # post months collapse to "POST"
                  as.character(ym_int - REF_YM_INT - 1L))]      # pre months keep own event time (k = -1 at Oct 2022)

# -----------------------------------------------------------------------------
# Merge exposure quintile (same convention as microdata_poisson_es.R)
# -----------------------------------------------------------------------------
cat("Loading exposure mapping\n")           # progress message
exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))   # read occupation -> quintile mapping
exp[, yrke4 := sprintf("%04s", styrk08)]    # zero-pad STYRK code to 4 digits to match the panel key
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]   # keep mapped occupations only

w <- merge(w, exp, by = "yrke4")            # inner join: drops 0000 / unmapped

# New-hire integer count: ny_jobb is a cell mean (share of workers who are
# new hires); count is the headcount. Their product (rounded) recovers the
# number of new hires. See generate_09_age_decades.py.
w[, ny_count := as.integer(round(ny_jobb * count))]   # reconstruct integer new-hire count per cell

cat(sprintf("Panel: %d cells, %d occupations, %d months (%s..%s)\n",   # report panel dimensions
            nrow(w), uniqueN(w$yrke4), uniqueN(w$ym_int),
            format(min(w$date)), format(max(w$date))))

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
# Coefficient harvesting
# -----------------------------------------------------------------------------
parse_did <- function(fit, sector, age, outcome, n_obs, n_occ) {   # pull POST x quintile coefs out of a fit
    if (is.null(fit)) return(NULL)          # skip cells whose estimation failed
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)   # coefficient table with names as a column
    m  <- regmatches(ct$name, regexec("kk::POST:ai_q::([0-9]+)", ct$name))   # match the POST x quintile terms
    q  <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,   # extract the quintile number
                 integer(1))
    keep <- !is.na(q)                       # rows that are POST x quintile coefficients
    if (!any(keep)) return(NULL)            # nothing to harvest -> skip
    data.table(
        sector = sector, age_group = age, outcome = outcome, ai_q = q[keep],   # identifiers + quintile (2..5)
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
# Estimate: sector x age group x outcome
# -----------------------------------------------------------------------------
coef_rows <- list()                         # collect harvested coefficient tables
for (sec in SECTORS) {                      # loop over sectors (private then public)
    for (a in ALDER_KEEP) {                 # loop over the four decade age groups
        slice <- w[sekt == sec & alder_gr == a]   # the (sector, age) subsample
        cat(sprintf("\n=== sector %d, age group %s (%s) ===\n",   # progress header for this cell
                    sec, a, AGE_LABELS[[a]]))

        # --- Employment (Poisson) ---
        bc <- balance_counts(slice, "count")   # balanced occ x month headcount panel
        fit_emp <- fit_pois(bc)             # Poisson event study on employment
        coef_rows[[length(coef_rows) + 1L]] <-   # store the employment POST x quintile coefs
            parse_did(fit_emp, sec, a, "employment", nrow(bc), uniqueN(bc$yrke4))

        # --- New hires (Poisson on integer hire count) ---
        bn <- balance_counts(slice, "ny_count")   # balanced occ x month new-hire-count panel
        fit_nh <- fit_pois(bn)              # Poisson event study on new hires
        coef_rows[[length(coef_rows) + 1L]] <-   # store the new-hires POST x quintile coefs
            parse_did(fit_nh, sec, a, "new_hires", nrow(bn), uniqueN(bn$yrke4))

        # --- Log monthly wage (weighted OLS, unbalanced) ---
        ws <- slice[!is.na(kontantlonn) & kontantlonn > 0 & !is.na(count) & count > 0]   # cells with positive wage and headcount
        ws[, ai_q := factor(ai_q, levels = 1:5)]   # quintile as a 5-level factor (Q1 base)
        ws[, lwage := log(kontantlonn)]     # dependent variable = log monthly cash wage
        fit_wage <- tryCatch(
            feols(lwage ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,   # DV=log wage; POST x (Q vs Q1); FE: occ + month
                  data = ws, weights = ~count, cluster = ~yrke4),   # weighted by headcount; clustered at occupation
            error = function(e) { cat("  feols failed:", conditionMessage(e), "\n"); NULL })   # NULL on failure
        coef_rows[[length(coef_rows) + 1L]] <-   # store the wage POST x quintile coefs
            parse_did(fit_wage, sec, a, "log_wage", nrow(ws), uniqueN(ws$yrke4))

        cat(sprintf("  emp n=%d, new_hires n=%d, wage n=%d\n",   # report sample sizes per outcome
                    nrow(bc), nrow(bn), nrow(ws)))
    }
}

out <- rbindlist(Filter(Negate(is.null), coef_rows))   # stack all harvested coefficient tables
setorder(out, sector, age_group, outcome, ai_q)        # tidy row order

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)   # ensure output dir exists
fwrite(out, OUT_CSV)                        # write the coefficient CSV (feeds Table 5 / Figure grid)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))   # progress message
