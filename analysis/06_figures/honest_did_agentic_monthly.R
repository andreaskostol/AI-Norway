# =============================================================================
# honest_did_agentic_monthly.R : Rambachan-Roth honest DiD paa MAANEDLIGE
#                                koeffisienter, agentic-designet (re-anket
#                                april 2025), Q5 vs Q3.
# =============================================================================
# Validering av kvartalsaggregeringen i honest_did_full_preseas.R: samme
# design, men uten aggregering. Pre = juli 2023..mars 2025 (21 mnd),
# ref = april 2025, post = mai 2025..februar 2026 (10 mnd).
# Target: snitt av post-maaned 3..10 (juli 2025..februar 2026, tilsvarer
# omtrent kvartalstargetet 2025q3..2026q1).
#
# CLI args: args[1] = age_group (1..4, default alle)
# Output: analysis/output/coefficients/coef_honest_did_agentic_monthly.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest); library(HonestDiD) })

args <- commandArgs(trailingOnly = TRUE)
ALDER_KEEP <- if (length(args) >= 1) args[1] else c("1", "2", "3", "4")

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_honest_did_agentic_monthly.csv")

REF_YM_INT <- 2022L * 12L + 10L
SEAS_FROM  <- as.IDate("2021-01-16")
SEAS_TO    <- as.IDate("2024-12-16")
MBARVEC    <- c(0, 0.5, 1)

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% c("1","2","3","4")]
d[, date := as.IDate(date)]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, t := as.integer(ym_int - REF_YM_INT)]
d[, cal_month := month(date)]
d <- d[, .(count = value, date, yrke4, alder_gr, k, t, cal_month)]

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
stopifnot(all(nchar(exp$styrk08) == 4L))
exp <- exp[!is.na(quintile), .(yrke4 = styrk08, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

t_to_calm <- unique(d[, .(t, k, cal_month, date)])

balance <- function(sub) {
    grid <- CJ(yrke4 = unique(sub$yrke4), t = sort(unique(sub$t)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4")
    grid <- merge(grid, t_to_calm, by = "t")
    out <- merge(grid, sub[, .(yrke4, t, count)],
                 by = c("yrke4", "t"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, q_m_key := paste0(ai_q, "_", cal_month)]
    out[, ai_q_f := factor(ai_q, levels = 1:5)]
    out
}

# Agentic monthly: k = 8..29 er pre (jul 2023..mar 2025, 21 mnd; k=29 =
# apr 2025 er ref og utelates), k = 30..39 er post (mai 2025..feb 2026).
kvec <- c(-22:-2, 0:39)
K_PRE  <- 8:28
K_POST <- 30:39

rows <- list()
for (a in ALDER_KEEP) {
    cat(sprintf("\n=== age group %s ===\n", a))
    sub_seas <- balance(d[alder_gr == a & date >= SEAS_FROM & date <= SEAS_TO])
    fit_pre <- fepois(count ~ i(ai_q_f, t, ref = "3") | yrke4 + t + q_m_key,
                      data = sub_seas, warn = FALSE, notes = FALSE)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_dt <- data.table(q_m_key = names(seas_fe), seas = as.numeric(seas_fe))
    seas_dt[, q := sub("_.*", "", q_m_key)]
    seas_dt[, seas := seas - mean(seas), by = q]

    sub <- balance(d[alder_gr == a])
    sub <- merge(sub, seas_dt[, .(q_m_key, seas)], by = "q_m_key",
                 all.x = TRUE, sort = FALSE)
    fit <- fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "3") | yrke4 + k,
                  data = sub, offset = ~seas, cluster = ~yrke4,
                  warn = FALSE, notes = FALSE)

    nm_all <- sprintf("k::%d:ai_q_f::5", kvec)
    beta_m  <- coef(fit)[nm_all]
    sigma_m <- vcov(fit)[nm_all, nm_all]

    # Re-anking til april 2025 (k=29) og restriksjon til agentic-vinduet.
    keep <- sprintf("k::%d:ai_q_f::5", c(K_PRE, K_POST))
    L <- matrix(0, nrow = length(keep), ncol = length(nm_all),
                dimnames = list(keep, nm_all))
    for (i in seq_along(keep)) L[i, keep[i]] <- 1
    L[, "k::29:ai_q_f::5"] <- L[, "k::29:ai_q_f::5"] - 1
    betahat <- as.numeric(L %*% beta_m)
    sigma   <- L %*% sigma_m %*% t(L)
    sigma   <- (sigma + t(sigma)) / 2

    n_pre <- length(K_PRE); n_post <- length(K_POST)
    l_vec <- rep(0, n_post); l_vec[3:10] <- 1/8   # jul 2025..feb 2026

    orig <- HonestDiD::constructOriginalCS(
        betahat = betahat, sigma = sigma,
        numPrePeriods = n_pre, numPostPeriods = n_post, l_vec = l_vec)
    rows[[paste(a, "orig")]] <- data.table(
        age_group = as.integer(a), delta = "original", Mbar = NA_real_,
        lb = as.numeric(orig$lb), ub = as.numeric(orig$ub))
    cat(sprintf("  original CI: [%+.4f, %+.4f]\n", orig$lb, orig$ub))

    t0 <- Sys.time()
    res <- tryCatch(
        HonestDiD::createSensitivityResults_relativeMagnitudes(
            betahat = betahat, sigma = sigma,
            numPrePeriods = n_pre, numPostPeriods = n_post,
            bound = "deviation from linear trend",
            Mbarvec = MBARVEC, l_vec = l_vec,
            gridPoints = 200L, grid.lb = -0.75, grid.ub = 0.75),
        error = function(e) {
            cat("  SDRM failed:", conditionMessage(e), "\n"); NULL })
    cat(sprintf("  SDRM runtime: %.1f min\n",
                as.numeric(difftime(Sys.time(), t0, units = "mins"))))
    if (is.null(res)) next
    res <- as.data.table(res)
    rows[[paste(a, "SDRM")]] <- data.table(
        age_group = as.integer(a), delta = "SDRM",
        Mbar = as.numeric(res$Mbar),
        lb = as.numeric(res$lb), ub = as.numeric(res$ub))
    for (i in seq_len(nrow(res)))
        cat(sprintf("  SDRM Mbar=%.1f: [%+.4f, %+.4f]\n",
                    res$Mbar[i], res$lb[i], res$ub[i]))
}

out <- rbindlist(rows, fill = TRUE)
setorder(out, age_group, delta, Mbar, na.last = FALSE)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
