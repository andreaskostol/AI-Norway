# =============================================================================
# microdata_es_decade_q3_nyjobb.R : Q3-referenced Poisson event-study on the
#                                   count of new hires per cell-month.
# =============================================================================
# Parallel to microdata_es_decade_q3.R, but the outcome is the count of new
# starts: hires_{j,t} = round(count_{j,t} * ny_jobb_share_{j,t}).
#
# ny_jobb in the parsed file is a cell-level mean of a 0/1 worker indicator
# (1 if startdato is within ~30 days of the 16th-of-month snapshot, so the
# worker has just started). Multiplying by headcount and rounding gives the
# cell-month flow of hires; running fepois on that count is the natural
# Poisson analog of the BCC hires event-study.
#
# Spec (per decade age group a):
#   log E[hires_{j,t}] = alpha_j + beta_t
#                     + sum_{q != 3, k != -1} gamma_{q,k}
#                       * 1{ai_q(j)=q} * 1{k(t)=k}
#   k = months since Oct 2022 (Oct 2022 = -1). Reference: q=3.
#   Cluster SE at occupation. Sample: private sector, count >= 10,
#   through 2025m4.
#
# Note: ny_jobb is only collected from 2022m05 onward (see
# 09a_count_nyjobb_2022m05_2026m02.mdata). The pre-period for this regression
# is therefore short (May 2022 - Sep 2022 = 5 months, plus Oct 2022 = k=-1
# reference); k range is approx -5..29 instead of -22..29.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q3_nyjobb.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_q3_nyjobb.csv")

REF_YM_INT  <- 2022L * 12L + 10L
CUTOFF_DATE <- as.IDate("2025-04-16")
ALDER_KEEP  <- c("1", "2", "3", "4")
MIN_COUNT   <- 10L

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[sekt == 2L & alder_gr %in% ALDER_KEEP
       & variable %in% c("count", "ny_jobb")]
dw <- dcast(d, date + yrke4 + alder_gr ~ variable, value.var = "value")
dw[, date := as.IDate(date)]
dw <- dw[date <= CUTOFF_DATE]
dw[, ym_int := year(date) * 12L + month(date)]
dw[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
# Require count >= 10 and ny_jobb available; derive hires count.
dw <- dw[!is.na(count) & count >= MIN_COUNT & !is.na(ny_jobb)]
dw[, hires := as.integer(round(count * ny_jobb))]

cat(sprintf("k range: %d..%d, n_cells after filter: %d\n",
            min(dw$k), max(dw$k), nrow(dw)))
cat(sprintf("hires distribution: 0s=%d, mean=%.2f, median=%d, max=%d\n",
            sum(dw$hires == 0), mean(dw$hires), median(dw$hires),
            max(dw$hires)))

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
dw <- merge(dw, exp, by = "yrke4")
dw[, ai_q := factor(ai_q, levels = 1:5)]

# Balance the (yrke4, k) panel within each age group; fill missing hires
# with 0 (no observed starts).
balance <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]),
                  by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, hires)],
                 by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(hires), hires := 0]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(dw[alder_gr == a])
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d ---\n",
                a, n_obs, n_occ))
    fit <- tryCatch(
        fepois(hires ~ i(k, ai_q, ref = -1, ref2 = "3") | yrke4 + k,
               data = sub, cluster = ~ yrke4),
        error = function(e) {
            cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
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
