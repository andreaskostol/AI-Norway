# =============================================================================
# microdata_es_decade_q3_hourly_wage_pathA.R : Q3-referenced event-study on
#                                              derived hourly wage from
#                                              EXISTING cell-level data.
# =============================================================================
# Path A (quick/descriptive): build hourly wage from the cell-level means we
# already have:
#   hourly_wage_cell = mean(kontantlonn) / (mean(stillingspst)/100) / 162.5
# This is the *ratio of cell means*, not the *cell mean of ratios*; Jensen's
# inequality gives a small level bias that mostly cancels in event-study
# coefficients (where we look at changes, not levels). Path B (a parallel
# microdata.no script, see microdata-scripts/monthly/09g_hourly_wage_*.mdata)
# computes the worker-level ratio first then averages -- run that and rerun
# microdata_es_decade_q3_hourly_wage.R when the new data is in.
#
# Spec (per decade age group a):
#   log(hourly_wage_cell_{j,t}) = alpha_j + beta_t
#                              + sum_{q != 3, k != -1} gamma_{q,k}
#                                * 1{ai_q(j)=q} * 1{k(t)=k}
#   k = months since Oct 2022 (Oct 2022 = -1). Reference: q=3.
#   Weights: cell headcount (count). Cluster SE at occupation.
#   Sample: private sector, count >= 10, stillingspst > 0, through 2025m4.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q3_hourly_wage_pathA.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_q3_hourly_wage_pathA.csv")

REF_YM_INT  <- 2022L * 12L + 10L
CUTOFF_DATE <- as.IDate("2025-04-16")
ALDER_KEEP  <- c("1", "2", "3", "4")
MIN_COUNT   <- 10L
FT_HOURS    <- 162.5   # Norwegian full-time hours per month (37.5/uke * 52/12)

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[sekt == 2L & alder_gr %in% ALDER_KEEP
       & variable %in% c("count", "kontantlonn", "stillingspst")]
dw <- dcast(d, date + yrke4 + alder_gr ~ variable, value.var = "value")
dw[, date := as.IDate(date)]
dw <- dw[date <= CUTOFF_DATE]
dw[, ym_int := year(date) * 12L + month(date)]
dw[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
dw <- dw[!is.na(count) & count >= MIN_COUNT
         & !is.na(kontantlonn) & kontantlonn > 0
         & !is.na(stillingspst) & stillingspst > 0]
dw[, hourly_wage := kontantlonn / (stillingspst / 100) / FT_HOURS]

cat(sprintf("k range: %d..%d, n_cells after filter: %d\n",
            min(dw$k), max(dw$k), nrow(dw)))
cat(sprintf("hourly_wage (NOK/h): p10=%.1f  p50=%.1f  p90=%.1f  wmean=%.1f\n",
            quantile(dw$hourly_wage, 0.1),
            quantile(dw$hourly_wage, 0.5),
            quantile(dw$hourly_wage, 0.9),
            weighted.mean(dw$hourly_wage, dw$count)))

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
dw <- merge(dw, exp, by = "yrke4")
dw[, ai_q := factor(ai_q, levels = 1:5)]

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- dw[alder_gr == a]
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d ---\n",
                a, n_obs, n_occ))
    fit <- tryCatch(
        feols(log(hourly_wage) ~ i(k, ai_q, ref = -1, ref2 = "3")
              | yrke4 + k,
              data = sub, weights = ~ count, cluster = ~ yrke4),
        error = function(e) {
            cat("  feols failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit)) next
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m <- regmatches(ct$name,
                    regexec("k::(-?[0-9]+):ai_q::([0-9]+)", ct$name))
    parsed <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else c(NA, NA)))
    ct$k <- parsed[, 1]; ct$ai_q <- parsed[, 2]
    ct <- ct[!is.na(ct$k), ]
    cr <- data.table(age_group = as.integer(a), ai_q = ct$ai_q, k = ct$k,
                     coef = ct[, "Estimate"], se = ct[, "Std. Error"],
                     n_obs = n_obs, n_occ = n_occ)
    ref_rows <- data.table(age_group = as.integer(a),
                           ai_q = c(1L, 2L, 4L, 5L),
                           k = -1L, coef = 0, se = 0,
                           n_obs = n_obs, n_occ = n_occ)
    coef_rows[[a]] <- rbindlist(list(cr, ref_rows))
    cat(sprintf("  harvested %d coefs\n", nrow(cr)))
}

out <- rbindlist(coef_rows)
setorder(out, age_group, ai_q, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
