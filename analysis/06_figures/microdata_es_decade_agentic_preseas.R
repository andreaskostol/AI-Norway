# =============================================================================
# microdata_es_decade_agentic_preseas.R : Agentic Poisson event-study with
#                                         PRE-PERIOD QUINTILE x CAL_MONTH
#                                         seasonal adjustment (offset).
# =============================================================================
# 2-stegs:
#   Steg 1: estimer kvintil-spesifikt sesongmoenster fra HELE pre-perioden
#           (2021m1 .. Apr 2025 = 52 mnd). Q3 ref ligger inn i FE-strukturen
#           ved at vi sentrerer seas_fe etterpaa.
#   Steg 2: event-study paa BCC 22-mnd vindu (2023m7+) med sesong som offset.
#
# Spec (per decade age group a):
#   log E[count_{j,t}] = seas_{q(j), m(t)}^{pre}
#                     + alpha_j + beta_t
#                     + sum_{q in {1,2,4,5}, k != -1} gamma_{q,k}
#                       * 1{ai_q(j)=q} * 1{k(t)=k}
#   Reference: q = 3, k = -1.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_agentic_preseas.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_agentic_preseas.csv")

REF_YM_INT  <- 2025L * 12L + 4L            # April 2025 = k = -1
WINDOW_FROM <- as.IDate("2023-07-16")      # BCC 22-mo pre-window for STEP 2
SEAS_FROM   <- as.IDate("2021-01-16")      # full pre-treatment for STEP 1
SEAS_TO     <- as.IDate("2025-04-16")      # last pre-agentic month
ALDER_KEEP  <- c("1", "2", "3", "4")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% ALDER_KEEP]
d[, date := as.IDate(date)]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, cal_month := month(date)]
d <- d[, .(count = value, date, yrke4, alder_gr, k, cal_month)]

cat(sprintf("full k range: %d..%d\n", min(d$k), max(d$k)))

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

k_to_calm <- unique(d[, .(k, cal_month)])

balance <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]),
                  by = "yrke4", all.x = TRUE)
    grid <- merge(grid, k_to_calm, by = "k", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, count)],
                 by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, q_m_key := paste0(ai_q, "_", cal_month)]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    # Step 1: q x cal_month seasonal pattern from full pre-treatment.
    d_seas <- d[alder_gr == a & date >= SEAS_FROM & date <= SEAS_TO]
    sub_seas <- balance(d_seas)
    fit_pre <- tryCatch(
        fepois(count ~ 1 | yrke4 + q_m_key, data = sub_seas),
        error = function(e) {
            cat("  step1 fepois failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit_pre)) next

    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_fe <- seas_fe - mean(seas_fe)
    cat(sprintf("\n--- age group %s ---\n", a))
    cat(sprintf(paste0("  step1: %d (q, cal_month) levels from %d obs ",
                       "(range %.3f..%.3f)\n"),
                length(seas_fe), nrow(sub_seas),
                min(seas_fe), max(seas_fe)))

    # Step 2: event-study on BCC 22-mo pre-window + post-period.
    d_es <- d[alder_gr == a & date >= WINDOW_FROM]
    sub <- balance(d_es)
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("  step2: ES sample n=%d, n_occ=%d, k range %d..%d\n",
                n_obs, n_occ, min(sub$k), max(sub$k)))

    sub[, seas_offset := seas_fe[q_m_key]]
    sub[is.na(seas_offset), seas_offset := 0]

    fit <- tryCatch(
        fepois(count ~ i(k, ai_q, ref = -1, ref2 = "3") | yrke4 + k,
               data = sub, offset = ~seas_offset, cluster = ~yrke4),
        error = function(e) {
            cat("  step2 fepois failed:", conditionMessage(e), "\n"); NULL })
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
    cat(sprintf("  step2: harvested %d (k, q) coefs\n", nrow(cr)))

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
