# =============================================================================
# trend_break_poisson.R : Stykkevis lineaer trendbrudd-modell (Poisson).
# =============================================================================
# Kvintilspesifikke lineaere trender med helningsendring ved november 2022
# (ChatGPT) og mai 2025 (agentic), Q3 som referansekvintil. Full datatilgang
# 2021m1 .. 2026m2, privat sektor, per decade age group.
#
# Spec (per age group a, q i {1,2,4,5}):
#   log E[count_{j,t}] = alpha_j + beta_t [+ delta_{q(j), m(t)}]
#                     + b1_q * 1{ai_q(j)=q} * t
#                     + b2_q * 1{ai_q(j)=q} * max(t - t_GPT, 0)
#                     + b3_q * 1{ai_q(j)=q} * max(t - t_AGE, 0)
#   t = maaneder siden oktober 2022 (okt 2022 = 0). Knekk: t_GPT = 0 (helning
#   endres f.o.m. nov 2022), t_AGE = 30 (helning endres f.o.m. mai 2025).
#   b1 = pre-helning, b1+b2 = mellomhelning, b1+b2+b3 = agentic-helning,
#   alle relativt til Q3. Cluster SE paa yrke.
#
# To sesongspesifikasjoner:
#   joint   : kvintil x kalendermaaned som FE estimert SIMULTANT. Mulig her
#             (i motsetning til i fri event-study) fordi trendene er
#             parametriske, saa delta_{q,m} er ikke kollinear med dem.
#   preseas : to-stegs offset, men med forbedret steg 1: HELE aar 2021-2024
#             (48 mnd, balansert kalender) og kvintilspesifikke trender +
#             maaned-FE i steg 1, slik at differensielle trender ikke
#             kontaminerer sesongfaktorene.
#
# Output: analysis/output/coefficients/coef_trend_break.csv
#   terms: slope_pre (b1), dslope_chatgpt (b2), dslope_agentic (b3),
#          slope_mid (b1+b2), slope_post (b1+b2+b3). Enhet: logpoeng/maaned.
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_trend_break.csv")

REF_YM_INT <- 2022L * 12L + 10L           # oktober 2022: t = 0
T_AGE      <- 30L                          # april 2025; helning endres fra t=31
SEAS_FROM  <- as.IDate("2021-01-16")       # steg 1: hele aar 2021-2024
SEAS_TO    <- as.IDate("2024-12-16")
ALDER_KEEP <- c("1", "2", "3", "4")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% ALDER_KEEP]
d[, date := as.IDate(date)]
d[, ym_int := year(date) * 12L + month(date)]
d[, t := as.integer(ym_int - REF_YM_INT)]
d[, cal_month := month(date)]
d <- d[, .(count = value, date, yrke4, alder_gr, t, cal_month)]

exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
stopifnot(all(nchar(exp$styrk08) == 4L))
exp <- exp[!is.na(quintile), .(yrke4 = styrk08, ai_q = as.integer(quintile))]
d <- merge(d, exp, by = "yrke4")

t_to_calm <- unique(d[, .(t, cal_month, date)])

balance <- function(sub) {
    grid <- CJ(yrke4 = unique(sub$yrke4), t = sort(unique(sub$t)))
    grid <- merge(grid, unique(sub[, .(yrke4, ai_q)]), by = "yrke4")
    grid <- merge(grid, t_to_calm, by = "t")
    out <- merge(grid, sub[, .(yrke4, t, count)],
                 by = c("yrke4", "t"), all.x = TRUE)
    out[is.na(count), count := 0]
    out[, h1 := pmax(t, 0L)]
    out[, h2 := pmax(t - T_AGE, 0L)]
    out[, q_m_key := paste0(ai_q, "_", cal_month)]
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

# Avledede segmenthelninger med SE via lineaerkombinasjoner av vcov.
derive_rows <- function(fit, a, spec, n_obs, n_occ) {
    b <- coef(fit); V <- vcov(fit)
    rows <- list()
    for (q in c(1L, 2L, 4L, 5L)) {
        nm <- c(sprintf("ai_q::%d:t", q),
                sprintf("ai_q::%d:h1", q),
                sprintf("ai_q::%d:h2", q))
        if (!all(nm %in% names(b))) next
        combos <- list(slope_pre      = c(1, 0, 0),
                       dslope_chatgpt = c(0, 1, 0),
                       dslope_agentic = c(0, 0, 1),
                       slope_mid      = c(1, 1, 0),
                       slope_post     = c(1, 1, 1))
        for (term in names(combos)) {
            w <- combos[[term]]
            est <- sum(w * b[nm])
            se  <- sqrt(drop(t(w) %*% V[nm, nm] %*% w))
            rows[[paste(q, term)]] <- data.table(
                age_group = as.integer(a), spec = spec, ai_q = q,
                term = term, coef = est, se = se,
                n_obs = n_obs, n_occ = n_occ)
        }
    }
    rbindlist(rows)
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(d[alder_gr == a])
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s: n=%d, n_occ=%d, t %d..%d ---\n",
                a, n_obs, n_occ, min(sub$t), max(sub$t)))

    # --- Spec 1: joint (kvintil x kalendermaaned-FE simultant) ---
    fit_j <- tryCatch(
        fepois(count ~ i(ai_q, t, ref = "3") + i(ai_q, h1, ref = "3")
                     + i(ai_q, h2, ref = "3") | yrke4 + t + q_m_key,
               data = sub, cluster = ~yrke4),
        error = function(e) {
            cat("  joint fepois failed:", conditionMessage(e), "\n"); NULL })
    if (!is.null(fit_j)) {
        coef_rows[[paste(a, "joint")]] <-
            derive_rows(fit_j, a, "joint", n_obs, n_occ)
        cat("  joint: ok\n")
    }

    # --- Spec 2: preseas-offset (forbedret steg 1) ---
    sub_seas <- balance(d[alder_gr == a & date >= SEAS_FROM & date <= SEAS_TO])
    fit_pre <- tryCatch(
        fepois(count ~ i(ai_q, t, ref = "3") | yrke4 + t + q_m_key,
               data = sub_seas),
        error = function(e) {
            cat("  step1 fepois failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit_pre)) next
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_dt <- data.table(q_m_key = names(seas_fe), seas = as.numeric(seas_fe))
    seas_dt[, q := sub("_.*", "", q_m_key)]
    seas_dt[, seas := seas - mean(seas), by = q]
    cat(sprintf("  step1: %d (q, m) celler, sesongspenn %.3f..%.3f\n",
                nrow(seas_dt), min(seas_dt$seas), max(seas_dt$seas)))

    sub2 <- merge(sub, seas_dt[, .(q_m_key, seas)], by = "q_m_key",
                  all.x = TRUE, sort = FALSE)
    stopifnot(!anyNA(sub2$seas))
    fit_p <- tryCatch(
        fepois(count ~ i(ai_q, t, ref = "3") + i(ai_q, h1, ref = "3")
                     + i(ai_q, h2, ref = "3") | yrke4 + t,
               data = sub2, offset = ~seas, cluster = ~yrke4),
        error = function(e) {
            cat("  preseas fepois failed:", conditionMessage(e), "\n"); NULL })
    if (!is.null(fit_p)) {
        coef_rows[[paste(a, "preseas")]] <-
            derive_rows(fit_p, a, "preseas", n_obs, n_occ)
        cat("  preseas: ok\n")
    }
}

out <- rbindlist(coef_rows)
setorder(out, age_group, spec, ai_q, term)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))

# Kompakt utskrift: helninger i logpoeng/aar for Q5 vs Q3.
cat("\n=== Q5 vs Q3, logpoeng/aar (coef x 12), z i parentes ===\n")
pr <- out[ai_q == 5L & term %in% c("slope_pre", "slope_mid", "slope_post")]
for (i in seq_len(nrow(pr))) {
    r <- pr[i]
    cat(sprintf("  age %d %-8s %-10s %+6.3f (z=%+.2f)\n",
                r$age_group, r$spec, r$term, r$coef * 12, r$coef / r$se))
}
