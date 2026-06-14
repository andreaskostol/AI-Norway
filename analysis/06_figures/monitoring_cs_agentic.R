# =============================================================================
# monitoring_cs_agentic.R : Anytime-valid konfidens-sekvenser for agentic-
#                           overvaakingen (Q vs Q3, per decade age group).
# =============================================================================
# Simulerer maanedlig sanntidsovervaaking: for hver monitor-maaned m fra
# mai 2025 til siste datamaaned re-estimeres en kollapset Poisson-DiD paa
# data t.o.m. m:
#
#   log E[count_{j,t}] = seas_{q(j),m(t)} + alpha_j + beta_t
#                      + sum_{q != 3} delta_q^(m) * 1{ai_q(j)=q} * Post_t
#   Post_t = 1{t >= mai 2025}. Vindu fra juli 2023 (BCC 22-mnd pre).
#   Sesongoffset: steg 1 paa hele aar 2021-2024 med kvintiltrender
#   (ingen look-ahead: vinduet ligger foer overvaakingsstart).
#
# For hver (age, q)-serie pakkes delta^(m) inn i baade konvensjonelt 95%-KI
# og en anytime-valid konfidens-sekvens (CS) basert paa normal mixture-
# grensen (Robbins; Howard et al. 2021, Ann. Stat.; Waudby-Smith et al.
# 2024, Ann. Stat. for asymptotisk versjon som kun krever CLT):
#
#   V_m = 1 / se_m^2   (informasjon)
#   CS_m = delta_m +/- sqrt((V_m + rho2) * log((V_m + rho2)/(alpha^2 rho2))) / V_m
#
# Dekning 1-alpha SIMULTANT over alle m (Villes ulikhet) - gyldig under
# valgfri stopping/fortsettelse. rho2 velges ex ante slik at grensen er
# strammest ved en maalhorisont paa 12 overvaakingsmaaneder (informasjon
# framskrevet linaert fra foerste maaned). "Alarm" = foerste maaned CS
# ekskluderer null.
#
# Approksimasjonsforbehold: delta^(m)-sekvensen er avhengig over m
# (ekspanderende vindu); CS-en hviler paa den asymptotiske normal-
# approksimasjonen i Waudby-Smith et al. (2024), ikke paa uavhengige
# inkrementer.
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_monitor_cs_agentic.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_monitor_cs_agentic.csv")

REF_YM_INT  <- 2022L * 12L + 10L          # oktober 2022 (t = 0)
SEAS_FROM   <- as.IDate("2021-01-16")      # steg 1: hele aar 2021-2024
SEAS_TO     <- as.IDate("2024-12-16")
WINDOW_FROM <- as.IDate("2023-07-16")      # BCC 22-mnd pre-vindu
POST_FROM   <- as.IDate("2025-05-16")      # foerste agentic-maaned
ALDER_KEEP  <- c("1", "2", "3", "4")
ALPHA       <- 0.05
TARGET_M    <- 12L                          # maalhorisont for rho2 (mnd)

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
    out[, q_m_key := paste0(ai_q, "_", cal_month)]
    out[, ai_q_f := factor(ai_q, levels = 1:5)]
    out
}

# Normal mixture-grense: halvbredde paa parameter-skala ved informasjon V.
cs_halfwidth <- function(V, rho2, alpha = ALPHA) {
    sqrt((V + rho2) * log((V + rho2) / (alpha^2 * rho2))) / V
}

monitor_months <- sort(unique(d[date >= POST_FROM, date]))
cat(sprintf("monitor months: %s .. %s (%d)\n",
            min(monitor_months), max(monitor_months),
            length(monitor_months)))

rows <- list()
for (a in ALDER_KEEP) {
    # Steg 1: sesongfaktorer (en gang per aldersgruppe, ingen look-ahead).
    sub_seas <- balance(d[alder_gr == a & date >= SEAS_FROM & date <= SEAS_TO])
    fit_pre <- fepois(count ~ i(ai_q_f, t, ref = "3") | yrke4 + t + q_m_key,
                      data = sub_seas, warn = FALSE, notes = FALSE)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_dt <- data.table(q_m_key = names(seas_fe), seas = as.numeric(seas_fe))
    seas_dt[, q := sub("_.*", "", q_m_key)]
    seas_dt[, seas := seas - mean(seas), by = q]

    full <- balance(d[alder_gr == a & date >= WINDOW_FROM])
    full <- merge(full, seas_dt[, .(q_m_key, seas)], by = "q_m_key",
                  all.x = TRUE, sort = FALSE)
    stopifnot(!anyNA(full$seas))
    full[, post := as.integer(date >= POST_FROM)]

    cat(sprintf("\n--- age group %s ---\n", a))
    for (m in seq_along(monitor_months)) {
        mm <- monitor_months[m]
        sub <- full[date <= mm]
        fit <- tryCatch(
            fepois(count ~ i(ai_q_f, post, ref = "3") | yrke4 + t,
                   data = sub, offset = ~seas, cluster = ~yrke4,
                   warn = FALSE, notes = FALSE),
            error = function(e) NULL)
        if (is.null(fit)) { cat(sprintf("  %s: failed\n", mm)); next }
        ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
        pm <- regmatches(ct$name, regexec("ai_q_f::([0-9]+):post", ct$name))
        ct$ai_q <- sapply(pm, function(x)
            if (length(x) == 2) as.integer(x[2]) else NA_integer_)
        ct <- ct[!is.na(ct$ai_q), ]
        rows[[paste(a, m)]] <- data.table(
            age_group = as.integer(a), ai_q = ct$ai_q,
            monitor_date = mm, n_post = m,
            coef = ct[, "Estimate"], se = ct[, "Std. Error"])
    }
}

out <- rbindlist(rows)

# CS-grense per (age, q)-serie. rho2 velges fra informasjonen i foerste
# overvaakingsmaaned, framskrevet lineaert til TARGET_M maaneder.
out[, V := 1 / se^2]
out[, rho2 := {
    V1 <- V[n_post == min(n_post)][1]
    V_target <- V1 * TARGET_M
    optimize(function(r2) cs_halfwidth(V_target, r2),
             interval = c(V1 * 1e-4, V_target * 100))$minimum
}, by = .(age_group, ai_q)]
out[, cs_half := cs_halfwidth(V, rho2)]
out[, `:=`(ci_lo = coef - 1.96 * se, ci_hi = coef + 1.96 * se,
           cs_lo = coef - cs_half, cs_hi = coef + cs_half)]
out[, cs_excl_zero := as.integer(cs_lo > 0 | cs_hi < 0)]
out[, ci_excl_zero := as.integer(ci_lo > 0 | ci_hi < 0)]
out[, c("V", "rho2") := NULL]
setorder(out, age_group, ai_q, monitor_date)

dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))

cat("\n=== Status siste maaned (Q5 og Q4 vs Q3) ===\n")
last <- out[monitor_date == max(monitor_date) & ai_q %in% c(4L, 5L)]
for (i in seq_len(nrow(last))) {
    r <- last[i]
    cat(sprintf(paste0("  age %d Q%d: coef %+.4f  KI [%+.3f, %+.3f]%s",
                       "  CS [%+.3f, %+.3f]%s\n"),
                r$age_group, r$ai_q, r$coef, r$ci_lo, r$ci_hi,
                ifelse(r$ci_excl_zero == 1L, "*", " "),
                r$cs_lo, r$cs_hi,
                ifelse(r$cs_excl_zero == 1L, "*", " ")))
}
first_cross <- out[cs_excl_zero == 1L,
                   .(first_alarm = min(monitor_date)), by = .(age_group, ai_q)]
if (nrow(first_cross)) {
    cat("\nFoerste CS-alarm:\n"); print(first_cross)
} else cat("\nIngen CS-alarm i overvaakingsperioden.\n")
