# =============================================================================
# microdata_es_decade_q3_full_preseas.R : Full-vindu Q3-referert Poisson
#                                         event-study MED differensiell
#                                         sesongkontroll (preseas-offset).
# =============================================================================
# Som microdata_es_decade_q3_full.R, men med kvintil x kalendermaaned-offset
# estimert i et separat steg 1 (samme forbedrede steg 1 som i
# trend_break_poisson.R). To steg-1-vinduer for robusthet:
#   s2124  : hele aar 2021-2024 (48 mnd, balansert kalender). Inneholder
#            post-ChatGPT-maaneder, men kvintilspesifikke lineaere trender +
#            maaned-FE i steg 1 renser sesongfaktorene for differensielle
#            trender; bare avvik fra trend med kvintil x kalendermaaned-form
#            kan lekke inn.
#   pregpt : kun pre-ChatGPT (2021m1-2022m10, 22 mnd). Helt fri for
#            behandling, men ubalansert kalender (nov/des observert 1 gang,
#            ellers 2) og faerre obs per celle -> stoyere faktorer.
#   Steg 2: fri event-study (k = -22..39 rundt okt 2022) med offset.
#
# NB: SE i steg 2 tar ikke hoyde for steg-1-usikkerhet (generert regressor).
#     For publisering: cluster-bootstrap over begge steg (jf. _boot-variantene).
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
#         data/ai_exposure/styrk08_eloundou_beta_mapping.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q3_full_preseas.csv
#         analysis/output/coefficients/coef_microdata_es_decade_q3_full_preseas_pregpt.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_DIR   <- file.path(BASE, "analysis", "output", "coefficients")

REF_YM_INT <- 2022L * 12L + 10L           # oktober 2022 (k = -1, t = 0)
ALDER_KEEP <- c("1", "2", "3", "4")
SEAS_WINDOWS <- list(
    s2124  = list(from = as.IDate("2021-01-16"), to = as.IDate("2024-12-16"),
                  file = "coef_microdata_es_decade_q3_full_preseas.csv"),
    pregpt = list(from = as.IDate("2021-01-16"), to = as.IDate("2022-10-16"),
                  file = "coef_microdata_es_decade_q3_full_preseas_pregpt.csv"))

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
    out[, ai_q := factor(ai_q, levels = 1:5)]
    out
}

for (w in names(SEAS_WINDOWS)) {
    win <- SEAS_WINDOWS[[w]]
    cat(sprintf("\n===== seas window %s: %s .. %s =====\n",
                w, win$from, win$to))
    coef_rows <- list()
    for (a in ALDER_KEEP) {
        sub_seas <- balance(d[alder_gr == a & date >= win$from
                              & date <= win$to])
        fit_pre <- tryCatch(
            fepois(count ~ i(ai_q, t, ref = "3") | yrke4 + t + q_m_key,
                   data = sub_seas),
            error = function(e) {
                cat("  step1 fepois failed:", conditionMessage(e), "\n")
                NULL })
        if (is.null(fit_pre)) next
        seas_fe <- fixef(fit_pre)[["q_m_key"]]
        seas_dt <- data.table(q_m_key = names(seas_fe),
                              seas = as.numeric(seas_fe))
        seas_dt[, q := sub("_.*", "", q_m_key)]
        seas_dt[, seas := seas - mean(seas), by = q]
        cat(sprintf("--- age group %s: steg 1 ok, sesongspenn %.3f..%.3f\n",
                    a, min(seas_dt$seas), max(seas_dt$seas)))

        sub <- balance(d[alder_gr == a])
        sub <- merge(sub, seas_dt[, .(q_m_key, seas)], by = "q_m_key",
                     all.x = TRUE, sort = FALSE)
        stopifnot(!anyNA(sub$seas))
        n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)

        fit <- tryCatch(
            fepois(count ~ i(k, ai_q, ref = -1, ref2 = "3") | yrke4 + k,
                   data = sub, offset = ~seas, cluster = ~yrke4),
            error = function(e) {
                cat("  step2 fepois failed:", conditionMessage(e), "\n")
                NULL })
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
                               ai_q = c(1L, 2L, 4L, 5L), k = -1L,
                               coef = 0, se = 0, n_obs = n_obs, n_occ = n_occ)
        coef_rows[[a]] <- rbindlist(list(cr, ref_rows))
        cat(sprintf("  step2: %d (k, q) coefs, n=%d, n_occ=%d\n",
                    nrow(cr), n_obs, n_occ))
    }
    out <- rbindlist(coef_rows)
    setorder(out, age_group, ai_q, k)
    dir.create(OUT_DIR, showWarnings = FALSE, recursive = TRUE)
    fwrite(out, file.path(OUT_DIR, win$file))
    cat(sprintf("Saved %d rows to %s\n", nrow(out), win$file))
}
