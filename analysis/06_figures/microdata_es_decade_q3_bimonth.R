# =============================================================================
# microdata_es_decade_q3_bimonth.R : Q3-referenced Poisson event-study with
#                                    quintile x bimonth seasonal FE.
# =============================================================================
# Parallel to microdata_es_decade_q3.R, but adds a quintile-by-bimonth fixed
# effect to absorb differential seasonality across exposure quintiles.
#
# Motivation: month FE beta_t absorb only the *common* time path. Q1
# (carpenters etc.) has strong winter->summer swings while Q5 (developers
# etc.) is seasonally flat, so gamma_{q,k} oscillates with calendar month.
# Bimonth bins (Jan-Feb, Mar-Apr, May-Jun, Jul-Aug, Sep-Oct, Nov-Dec) coarse
# enough that the model retains some dof; finer than quarterly so the
# May-Jun summer-hire spike isn't blended with Mar-Apr.
#
# Spec (per decade age group a):
#   log E[count_{j,t}] = alpha_j + beta_t + delta_{q,m_bm(t)}
#                     + sum_{q in {1,2,4,5}, k != -1} gamma_{q,k}
#                       * 1{ai_q(j)=q} * 1{k(t)=k}
#   k = months since October 2022 (Oct 2022 = -1). Reference: q=3.
#   m_bm in 1..6 (Jan-Feb=1, ..., Nov-Dec=6). Q3 still reference for quintile.
#   Cluster SE at occupation. Private sector, through 2025m4.
#
# Note on identification: with monthly delta_{q,m} + monthly gamma_{q,k},
# the (delta, gamma) subsystem is underidentified by ~10 dof per quintile.
# With bimonth delta the deficit drops to ~4 per quintile -- fixest will
# drop collinear columns automatically; affected coefs report NA. Pair with
# microdata_es_decade_q3_bimonth_preperiod.R (TODO if needed) for a fully
# identified spec that pools pre-period gamma.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q3_bimonth.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_q3_bimonth.csv")

REF_YM_INT  <- 2022L * 12L + 10L          # October 2022
CUTOFF_DATE <- as.IDate("2025-04-16")     # through 2025m4
ALDER_KEEP  <- c("1", "2", "3", "4")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% ALDER_KEEP]
d[, date := as.IDate(date)]
d <- d[date <= CUTOFF_DATE]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, cal_month := month(date)]
d[, bimonth := (cal_month - 1L) %/% 2L + 1L]
d <- d[, .(count = value, yrke4, alder_gr, k, bimonth)]

cat(sprintf("k range: %d..%d\n", min(d$k), max(d$k)))
cat(sprintf("bimonth levels: %s\n",
            paste(sort(unique(d$bimonth)), collapse = ",")))

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

# Mapping k -> bimonth, used to fill bimonth in the balanced grid.
k_to_bimonth <- unique(d[, .(k, bimonth)])

balance <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]),
                  by = "yrke4", all.x = TRUE)
    grid <- merge(grid, k_to_bimonth, by = "k", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, count)],
                 by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out[, bimonth := factor(bimonth, levels = 1:6)]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(d[alder_gr == a])
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d ---\n",
                a, n_obs, n_occ))
    fit <- tryCatch(
        fepois(count ~ i(k, ai_q, ref = -1, ref2 = "3")
                       | yrke4 + k + ai_q^bimonth,
               data = sub, cluster = ~yrke4),
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

    # Diagnostic: median SE per quintile, base vs. with-bimonth (this run only)
    se_by_q <- cr[, .(med_se = median(se), n_coefs = .N), by = ai_q]
    print(se_by_q)

    # Joint pre-trend Wald per quintile (Q3 is reference)
    for (q in c(1, 2, 4, 5)) {
        pre_names <- grep(sprintf("k::-?[0-9]+:ai_q::%d", q),
                          names(coef(fit)), value = TRUE)
        pre_names <- pre_names[
            as.integer(sub(".*k::(-?[0-9]+):.*", "\\1", pre_names)) < -1]
        if (length(pre_names) == 0) next
        b <- coef(fit)[pre_names]
        V <- vcov(fit)[pre_names, pre_names, drop = FALSE]
        chi2 <- tryCatch(as.numeric(t(b) %*% solve(V) %*% b),
                         error = function(e) NA_real_)
        p <- if (is.finite(chi2)) pchisq(chi2, df = length(b),
                                          lower.tail = FALSE) else NA
        cat(sprintf("  Q%d pre-trend Wald: chi2=%.2f, df=%d, p=%.4f\n",
                    q, chi2, length(b), p))
    }
}

out <- rbindlist(coef_rows)
setorder(out, age_group, ai_q, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
