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
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_did_cell.csv
#         (schema: sector, age_group, outcome, ai_q, coef, se, p_value, n_obs, n_occ)
# =============================================================================

suppressMessages({
    library(data.table)
    library(fixest)
})

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_did_cell.csv")

stopifnot(file.exists(DATA_FILE), file.exists(EXP_FILE))

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
ALDER_KEEP  <- c("1", "2", "3", "4")        # 0 = <21/missing, 5 = 61+ : dropped
AGE_LABELS  <- c("1" = "Early career (21-30)", "2" = "31-40",
                 "3" = "41-50", "4" = "Senior (51-60)")
REF_YM_INT  <- 2022L * 12L + 10L            # October 2022 = last pre-period
CUTOFF_DATE <- as.IDate("2026-02-16")       # full window through 2026m2 (data
                                            # edge; the 2025m4 pre-agentic cutoff
                                            # was dropped together with the
                                            # secure-zone 7b/7d runs -- see
                                            # analysis-indiv/DESIGN_CHOICES.md s.23)
SECTORS     <- c("2" = 2L, "1" = 1L)        # 2 = private (main), 1 = public (appendix)

# -----------------------------------------------------------------------------
# Load + reshape (long -> wide on `variable`)
# -----------------------------------------------------------------------------
cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d[, date := as.IDate(date)]
d <- d[date <= CUTOFF_DATE]
d <- d[alder_gr %in% ALDER_KEEP]

w <- dcast(d, date + yrke4 + alder_gr + sekt ~ variable, value.var = "value")
w[, ym_int := year(date) * 12L + month(date)]
# kk = event-time level: each pre-month its own value, all post months -> "POST",
# ref = k = -1 (Oct 2022). Baseline-month reference, not pooled pre-period.
w[, kk := fifelse(ym_int > REF_YM_INT, "POST",
                  as.character(ym_int - REF_YM_INT - 1L))]

# -----------------------------------------------------------------------------
# Merge exposure quintile (same convention as microdata_poisson_es.R)
# -----------------------------------------------------------------------------
cat("Loading exposure mapping\n")
exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]

w <- merge(w, exp, by = "yrke4")            # inner join: drops 0000 / unmapped

# New-hire integer count: ny_jobb is a cell mean (share of workers who are
# new hires); count is the headcount. Their product (rounded) recovers the
# number of new hires. See generate_09_age_decades.py.
w[, ny_count := as.integer(round(ny_jobb * count))]

cat(sprintf("Panel: %d cells, %d occupations, %d months (%s..%s)\n",
            nrow(w), uniqueN(w$yrke4), uniqueN(w$ym_int),
            format(min(w$date)), format(max(w$date))))

# -----------------------------------------------------------------------------
# Balance helper for the count outcomes: every (yrke4 x ym_int) cell present
# within a (sector, age group) slice; missing -> 0. NOT used for the wage OLS.
# -----------------------------------------------------------------------------
balance_counts <- function(sub, value_col) {
    yrke4s <- unique(sub$yrke4)
    yms    <- sort(unique(sub$ym_int))
    grid   <- CJ(yrke4 = yrke4s, ym_int = yms)
    grid   <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    grid[, kk := fifelse(ym_int > REF_YM_INT, "POST",
                         as.character(ym_int - REF_YM_INT - 1L))]
    src    <- sub[, .(val = get(value_col)), by = .(yrke4, ym_int)]
    out    <- merge(grid, src, by = c("yrke4", "ym_int"), all.x = TRUE)
    out[is.na(val), val := 0L]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

# -----------------------------------------------------------------------------
# Coefficient harvesting
# -----------------------------------------------------------------------------
parse_did <- function(fit, sector, age, outcome, n_obs, n_occ) {
    if (is.null(fit)) return(NULL)
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m  <- regmatches(ct$name, regexec("kk::POST:ai_q::([0-9]+)", ct$name))
    q  <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,
                 integer(1))
    keep <- !is.na(q)
    if (!any(keep)) return(NULL)
    data.table(
        sector = sector, age_group = age, outcome = outcome, ai_q = q[keep],
        coef = ct[keep, "Estimate"], se = ct[keep, "Std. Error"],
        p_value = ct[keep, ncol(coeftable(fit))],   # last col = Pr(>|t|)
        n_obs = n_obs, n_occ = n_occ
    )
}

fit_pois <- function(dt) {
    tryCatch(
        fepois(val ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,
               data = dt, cluster = ~yrke4),
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
}

# -----------------------------------------------------------------------------
# Estimate: sector x age group x outcome
# -----------------------------------------------------------------------------
coef_rows <- list()
for (sec in SECTORS) {
    for (a in ALDER_KEEP) {
        slice <- w[sekt == sec & alder_gr == a]
        cat(sprintf("\n=== sector %d, age group %s (%s) ===\n",
                    sec, a, AGE_LABELS[[a]]))

        # --- Employment (Poisson) ---
        bc <- balance_counts(slice, "count")
        fit_emp <- fit_pois(bc)
        coef_rows[[length(coef_rows) + 1L]] <-
            parse_did(fit_emp, sec, a, "employment", nrow(bc), uniqueN(bc$yrke4))

        # --- New hires (Poisson on integer hire count) ---
        bn <- balance_counts(slice, "ny_count")
        fit_nh <- fit_pois(bn)
        coef_rows[[length(coef_rows) + 1L]] <-
            parse_did(fit_nh, sec, a, "new_hires", nrow(bn), uniqueN(bn$yrke4))

        # --- Log monthly wage (weighted OLS, unbalanced) ---
        ws <- slice[!is.na(kontantlonn) & kontantlonn > 0 & !is.na(count) & count > 0]
        ws[, ai_q := factor(ai_q, levels = 1:5)]
        ws[, lwage := log(kontantlonn)]
        fit_wage <- tryCatch(
            feols(lwage ~ i(kk, ai_q, ref = "-1", ref2 = "1") | yrke4 + ym_int,
                  data = ws, weights = ~count, cluster = ~yrke4),
            error = function(e) { cat("  feols failed:", conditionMessage(e), "\n"); NULL })
        coef_rows[[length(coef_rows) + 1L]] <-
            parse_did(fit_wage, sec, a, "log_wage", nrow(ws), uniqueN(ws$yrke4))

        cat(sprintf("  emp n=%d, new_hires n=%d, wage n=%d\n",
                    nrow(bc), nrow(bn), nrow(ws)))
    }
}

out <- rbindlist(Filter(Negate(is.null), coef_rows))
setorder(out, sector, age_group, outcome, ai_q)

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
