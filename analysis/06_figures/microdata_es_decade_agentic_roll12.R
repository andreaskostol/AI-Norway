# =============================================================================
# microdata_es_decade_agentic_roll12.R : Agentic Poisson event-study with
#                                        ROLLING 12-MONTH BASELINE OFFSET.
# =============================================================================
# Erstatter 2-stegs preseas-tilnaerming med en deterministisk transformasjon:
# for hver (yrke, t) beregner vi gjennomsnittet av count over de 12 foregaaende
# maanedene. Dette log-offset-er event-study-modellen direkte, slik at
# i(k, ai_q) maaler avvik fra HVERT YRKES eget rullende baseline-niva.
#
# Fordeler vs yrke x cal_month FE:
# - Ingen singletons: 12-mnd vindu dekker alle cal_months for hver t
# - Fanger baade sesong OG lokal trend (siden vinduet glir)
# - EN regresjon (ingen step-1 / step-2 -- bootstrap er rett-fram cluster boot)
# - Hver yrke faar sin egen tidsspesifikke baseline
#
# Ulemper:
# - Mister 12 mnd ved start (forste gyldige obs er 13 mnd inn i serien)
# - Hvis behandlingseffekten er gradvis akkumulerende, vil rullende baseline
#   ETTER hvert "spore" effekten -- post-treatment-koeffisientene blir mer
#   konservative (vi maaler avvik fra et baseline som ogsaa har den
#   akkumulerte effekten i seg).
#   Mitigerings: bruk LAG-baseline (eks. t-12..t-1, ikke t-11..t), saa
#   current m\anned er aldri i baseline.
#
# Spec (per decade age group a):
#   log E[count_{j,t}] = log(baseline_{j,t}) + alpha_j + beta_t
#                     + sum_{q in {1,2,4,5}, k != -1} gamma_{q,k}
#                       * 1{ai_q(j)=q} * 1{k(t)=k}
#   baseline_{j,t} = mean over k in [t-12, t-1] of count_{j, k}
#   Reference: q = 3, k = -1.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_agentic_roll12.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_agentic_roll12.csv")

REF_YM_INT  <- 2025L * 12L + 4L            # April 2025 = k = -1
ALDER_KEEP  <- c("1", "2", "3", "4")
ROLL_N      <- 12L                          # 12-mnd rullende vindu

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
d <- d[, .(count = value, yrke4, alder_gr, k)]

cat(sprintf("full k range: %d..%d\n", min(d$k), max(d$k)))

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04s", styrk08)]
exp <- exp[!is.na(quintile), .(yrke4, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

# Balanced grid per age, then compute rolling baseline per yrke.
balance_and_roll <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]),
                  by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, count)],
                 by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    setorder(out, yrke4, k)
    # Rolling baseline: mean of count over [t-12, t-1] (LAG mean, ekskl. t).
    # frollmean over the lagged series gives this.
    out[, count_lag := shift(count, 1L, type = "lag"), by = yrke4]
    out[, baseline := frollmean(count_lag, n = ROLL_N, align = "right"),
        by = yrke4]
    out[, count_lag := NULL]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance_and_roll(d[alder_gr == a])
    # Drop obs without valid baseline (first 12 mo of each yrke).
    # Also drop baseline <= 0 since log undefined.
    sub <- sub[!is.na(baseline) & baseline > 0]
    sub[, log_baseline := log(baseline)]

    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d, k range %d..%d ---\n",
                a, n_obs, n_occ, min(sub$k), max(sub$k)))

    fit <- tryCatch(
        fepois(count ~ i(k, ai_q, ref = -1, ref2 = "3") | yrke4 + k,
               data = sub, offset = ~log_baseline, cluster = ~yrke4),
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
    cat(sprintf("  harvested %d (k, q) coefs\n", nrow(cr)))

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
