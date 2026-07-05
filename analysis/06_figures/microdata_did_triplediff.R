# =============================================================================
# microdata_did_triplediff.R : Stacked cell-level triple difference,
#                              young (21-30) vs older (31-60), private sector
# =============================================================================
# Formal test of the "canary" age gradient: does the post-ChatGPT Q5-vs-Q1
# employment gap for young workers differ from the same gap for older workers?
# The per-age-group regressions in microdata_did_cell.R share occupations, so
# their coefficients cannot validly be differenced by the reader; this script
# estimates the difference jointly with clustered inference.
#
# Design: stack two groups, young = decade age group 21-30 and older = the
# summed 31-40, 41-50, and 51-60 groups (one pooled 31-60 count per
# occupation x month). Poisson:
#
#   log E[y_{j,g,t}] = alpha_{j,g} + beta_{t,g}
#                      + sum_{q>=2,k} gamma_{q,k} 1{q(j)=q, k(t)=k}
#                      + sum_{q>=2,k} delta_{q,k} 1{q(j)=q, k(t)=k} x young_g
#
# with occupation-by-group and month-by-group fixed effects. As in
# microdata_did_cell.R, each pre-month keeps its own event-time level and all
# post months collapse to "POST", with k = -1 (October 2022) and Q1 as the
# references. delta_{q,POST} is the triple difference: the young Q-vs-Q1 post
# gap minus the older one. The canary hypothesis predicts delta_{5,POST} < 0.
# Standard errors clustered at occupation (an occupation appears in both
# groups, so this also handles the cross-group correlation).
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m04_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_did_triplediff.csv
#         (schema: outcome, term, ai_q, coef, se, p_value, n_obs, n_occ;
#          term = "older_base" for gamma_{q,POST}, "young_diff" for
#          delta_{q,POST}, plus one "joint_wald" row for delta_{2..5,POST})
# =============================================================================

suppressMessages({                          # quiet package banners
    library(data.table)                     # fast in-memory data wrangling
    library(fixest)                         # fepois: fixed-effect Poisson
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
                       "coef_microdata_did_triplediff.csv")

stopifnot(file.exists(DATA_FILE), file.exists(EXP_FILE))   # fail early if inputs missing

# -----------------------------------------------------------------------------
# Constants (same conventions as microdata_did_cell.R)
# -----------------------------------------------------------------------------
YOUNG_GROUP <- "1"                          # decade age group 1 = ages 21-30
OLDER_GROUPS <- c("2", "3", "4")            # groups 2-4 = ages 31-60, pooled
REF_YM_INT  <- 2022L * 12L + 10L            # October 2022 (year*12+month index)
CUTOFF_DATE <- as.IDate("2026-04-16")       # full window through 2026m4
PRIVATE     <- 2L                           # sector code 2 = private

# -----------------------------------------------------------------------------
# Load, restrict, and pool the older groups
# -----------------------------------------------------------------------------
cat("Loading", DATA_FILE, "\n")             # progress message
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character", alder_gr = "character",   # read parsed aggregates
                                     sekt = "integer", variable = "character",
                                     value = "numeric"))
d[, date := as.IDate(date)]                 # parse the status date (the 16th)
d <- d[date <= CUTOFF_DATE]                 # keep months up to the data edge
d <- d[sekt == PRIVATE]                     # private sector only
d <- d[alder_gr %in% c(YOUNG_GROUP, OLDER_GROUPS)]   # ages 21-60 only

w <- dcast(d, date + yrke4 + alder_gr ~ variable, value.var = "value")   # long -> wide per variable
w[, ym_int := year(date) * 12L + month(date)]   # integer month index
# New-hire integer count: ny_jobb is the cell mean share of new hires; its
# product with headcount (rounded) recovers the count (see microdata_did_cell.R).
w[, ny_count := as.integer(round(fifelse(is.na(ny_jobb), 0, ny_jobb) * count))]

# Pool the three older decade groups into one 31-60 group by summing counts
# per occupation x month; the young group passes through unchanged.
w[, grp := fifelse(alder_gr == YOUNG_GROUP, "young", "older")]   # stack label
s <- w[, .(count = sum(count, na.rm = TRUE),          # pooled headcount
           ny_count = sum(ny_count, na.rm = TRUE)),   # pooled new-hire count
       by = .(yrke4, ym_int, grp)]

# Event-time level: each pre-month its own value, all post months -> "POST",
# reference k = -1 (October 2022). Same rule as microdata_did_cell.R.
s[, kk := fifelse(ym_int > REF_YM_INT, "POST",
                  as.character(ym_int - REF_YM_INT - 1L))]

# -----------------------------------------------------------------------------
# Merge exposure quintile
# -----------------------------------------------------------------------------
cat("Loading exposure mapping\n")           # progress message
exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))   # occupation -> quintile
exp[, yrke4 := sprintf("%04s", styrk08)]    # zero-pad to 4 digits to match the panel key
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]   # mapped occupations only
s <- merge(s, exp, by = "yrke4")            # inner join: drops 0000 / unmapped

cat(sprintf("Stacked panel: %d cells, %d occupations, %d months\n",
            nrow(s), uniqueN(s$yrke4), uniqueN(s$ym_int)))

# -----------------------------------------------------------------------------
# Balance the count panel within each group: every (yrke4 x ym_int) cell
# present, missing -> 0, as in microdata_did_cell.R.
# -----------------------------------------------------------------------------
balance_counts <- function(sub, value_col) {   # sub = one group slice
    yrke4s <- unique(sub$yrke4)             # occupations present in this group
    yms    <- sort(unique(sub$ym_int))      # months present
    grid   <- CJ(yrke4 = yrke4s, ym_int = yms)   # full occupation x month grid
    grid   <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4", all.x = TRUE)
    grid[, kk := fifelse(ym_int > REF_YM_INT, "POST",
                         as.character(ym_int - REF_YM_INT - 1L))]
    src    <- sub[, .(val = get(value_col)), by = .(yrke4, ym_int)]
    out    <- merge(grid, src, by = c("yrke4", "ym_int"), all.x = TRUE)
    out[is.na(val), val := 0L]              # absent cell -> zero count
    out                                     # balanced panel for this group
}

# -----------------------------------------------------------------------------
# Estimate the stacked triple difference per outcome
# -----------------------------------------------------------------------------
run_outcome <- function(value_col, outcome_label) {
    yb <- balance_counts(s[grp == "young"], value_col)[, grp := "young"]   # balanced young panel
    ob <- balance_counts(s[grp == "older"], value_col)[, grp := "older"]   # balanced older panel
    st <- rbindlist(list(yb, ob))           # stacked two-group panel
    st[, ai_q := factor(ai_q, levels = 1:5)]        # quintile factor, Q1 base
    # yq = quintile for young cells in Q2-Q5, "0" otherwise; interacting kk
    # with yq (ref2 = "0") yields exactly the delta_{q,k} young-differential
    # terms, with young Q1 as the within-young reference path.
    st[, yq := factor(fifelse(grp == "young" & as.integer(as.character(ai_q)) >= 2L,
                              as.character(ai_q), "0"),
                      levels = c("0", "2", "3", "4", "5"))]

    fit <- tryCatch(
        fepois(val ~ i(kk, ai_q, ref = "-1", ref2 = "1") +      # gamma_{q,k}: older-anchored base terms
                     i(kk, yq, ref = "-1", ref2 = "0") |         # delta_{q,k}: young differential
                     yrke4^grp + ym_int^grp,                     # occupation-by-group and month-by-group FE
               data = st, cluster = ~yrke4),                     # clustered at occupation
        error = function(e) { cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit)) return(NULL)

    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)   # coefficient table
    rows <- list()
    harvest <- function(pattern, term_label) {                  # pull POST x quintile terms
        m <- regmatches(ct$name, regexec(pattern, ct$name))
        q <- vapply(m, function(x) if (length(x) == 2L) as.integer(x[2]) else NA_integer_,
                    integer(1))
        keep <- !is.na(q)
        if (!any(keep)) return(NULL)
        data.table(outcome = outcome_label, term = term_label, ai_q = q[keep],
                   coef = ct[keep, "Estimate"], se = ct[keep, "Std. Error"],
                   p_value = ct[keep, ncol(coeftable(fit))],
                   n_obs = nrow(st), n_occ = uniqueN(st$yrke4))
    }
    rows[["base"]]  <- harvest("^kk::POST:ai_q::([0-9]+)$", "older_base")   # gamma_{q,POST}
    rows[["young"]] <- harvest("^kk::POST:yq::([0-9]+)$",  "young_diff")    # delta_{q,POST}

    # Joint Wald test that all four young POST differentials are zero.
    wnames <- grep("^kk::POST:yq::", names(coef(fit)), value = TRUE)
    wt <- tryCatch(wald(fit, keep = "^kk::POST:yq::", print = FALSE),
                   error = function(e) NULL)
    if (!is.null(wt)) {
        rows[["wald"]] <- data.table(outcome = outcome_label, term = "joint_wald",
                                     ai_q = NA_integer_, coef = wt$stat, se = NA_real_,
                                     p_value = wt$p, n_obs = nrow(st),
                                     n_occ = uniqueN(st$yrke4))
    }
    cat(sprintf("\n--- %s: POST x quintile terms ---\n", outcome_label))
    print(ct[grepl("^kk::POST:", ct$name), c("name", "Estimate", "Std. Error", "Pr(>|z|)")],
          row.names = FALSE)
    if (!is.null(wt)) cat(sprintf("Joint Wald (young_diff Q2-Q5): stat=%.3f, p=%.4f\n",
                                  wt$stat, wt$p))
    rbindlist(Filter(Negate(is.null), rows))
}

out <- rbindlist(list(run_outcome("count", "employment"),
                      run_outcome("ny_count", "new_hires")))

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)   # ensure output dir
fwrite(out, OUT_CSV)                        # write the coefficient CSV
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
