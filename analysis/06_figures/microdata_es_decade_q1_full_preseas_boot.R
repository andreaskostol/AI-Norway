# =============================================================================
# microdata_es_decade_q1_full_preseas_boot.R : Cluster-bootstrap-SE for
#                                              full-vindu 2-stegs preseas-ES.
# =============================================================================
# Boot-variant av microdata_es_decade_q3_full_preseas.R (s2124-vinduet):
# loeser generated-regressor-problemet ved cluster bootstrap paa yrke4 over
# BEGGE stegene, jf. microdata_es_decade_q3_preseas_boot.R.
#
# Forskjeller fra den gamle boot-varianten:
#   - Full-vindu ES: k = -22 .. 39 (ingen 2025m4-cutoff)
#   - Forbedret steg 1: HELE aar 2021-2024 (balansert kalender) med
#     kvintilspesifikke lineaere trender + maaned-FE, slik at differensielle
#     trender ikke kontaminerer sesongfaktorene. Sesong demeanes innen
#     kvintil.
#
# CLI args:
#   args[1] = B (antall bootstrap-iterasjoner, default 200)
#   args[2] = age_group (1..4, default kjor alle)
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q1_full_preseas_boot.csv
#         (samme schema som ikke-boot, men med se_naive + bootstrap-se)
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

args <- commandArgs(trailingOnly = TRUE)
B <- if (length(args) >= 1) as.integer(args[1]) else 200L
AGE_ARG <- if (length(args) >= 2) args[2] else NA

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_q1_full_preseas_boot.csv")

REF_YM_INT <- 2022L * 12L + 10L           # oktober 2022 (k = -1, t = 0)
SEAS_FROM  <- as.IDate("2021-01-16")       # steg 1: hele aar 2021-2024
SEAS_TO    <- as.IDate("2024-12-16")
ALDER_KEEP <- c("1", "2", "3", "4")
if (!is.na(AGE_ARG)) ALDER_KEEP <- AGE_ARG

set.seed(42L)

cat(sprintf("B = %d bootstrap iterations\n", B))
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
    out
}

# En 2-stegs-tilpasning paa et (evt. bootstrap-) sample.
# Steg 1: q x cal_month-FE paa hele aar 2021-2024, renset for
#         kvintiltrender. Steg 2: full-vindu ES med offset.
two_step_fit <- function(sub, return_se = FALSE) {
    sub[, ai_q_f := factor(ai_q, levels = 1:5)]
    pre <- sub[date >= SEAS_FROM & date <= SEAS_TO]
    fit_pre <- tryCatch(
        fepois(count ~ i(ai_q_f, t, ref = "3") | yrke4 + t + q_m_key,
               data = pre, warn = FALSE, notes = FALSE),
        error = function(e) NULL)
    if (is.null(fit_pre)) return(NULL)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_dt <- data.table(q_m_key = names(seas_fe), seas = as.numeric(seas_fe))
    seas_dt[, q := sub("_.*", "", q_m_key)]
    seas_dt[, seas := seas - mean(seas), by = q]
    sub[, seas_offset := NULL]
    sub <- merge(sub, seas_dt[, .(q_m_key, seas_offset = seas)],
                 by = "q_m_key", all.x = TRUE, sort = FALSE)
    sub[is.na(seas_offset), seas_offset := 0]

    fit <- tryCatch(
        fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "1") | yrke4 + k,
               data = sub, offset = ~seas_offset, cluster = ~yrke4,
               warn = FALSE, notes = FALSE),
        error = function(e) NULL)
    if (is.null(fit)) return(NULL)
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m <- regmatches(ct$name,
                    regexec("k::(-?[0-9]+):ai_q_f::([0-9]+)", ct$name))
    parsed <- do.call(rbind, lapply(m, function(x)
        if (length(x) == 3) c(as.integer(x[2]), as.integer(x[3]))
        else c(NA, NA)))
    ct$k <- parsed[, 1]; ct$ai_q <- parsed[, 2]
    ct <- ct[!is.na(ct$k), ]
    ct$key <- paste0(ct$k, "_", ct$ai_q)
    if (return_se) {
        return(setNames(as.numeric(ct[, "Std. Error"]), ct$key))
    }
    setNames(as.numeric(ct[, "Estimate"]), ct$key)
}

# Cluster bootstrap: resample yrke4 med replacement, kjor 2-stegs, lagre.
cluster_boot <- function(sub, B) {
    yrke4s_all <- unique(sub$yrke4)
    n_occ <- length(yrke4s_all)
    idx <- split(seq_len(nrow(sub)), sub$yrke4)
    boot_estimates <- list()
    for (b in seq_len(B)) {
        drawn <- sample(yrke4s_all, n_occ, replace = TRUE)
        boot_sub <- rbindlist(lapply(seq_along(drawn), function(i) {
            s <- sub[idx[[drawn[i]]]]
            s[, yrke4 := paste0(drawn[i], "_", i)]
            s
        }))
        est <- tryCatch(two_step_fit(boot_sub, return_se = FALSE),
                        error = function(e) NULL)
        if (!is.null(est)) boot_estimates[[length(boot_estimates) + 1L]] <- est
        if (b %% 20L == 0L)
            cat(sprintf("    boot %d/%d (%d successful)\n",
                        b, B, length(boot_estimates)))
    }
    boot_estimates
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(d[alder_gr == a])
    sub[, seas_offset := NA_real_]
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n=== age group %s, n=%d, n_occ=%d ===\n", a, n_obs, n_occ))

    point <- two_step_fit(copy(sub), return_se = FALSE)
    naive_se <- two_step_fit(copy(sub), return_se = TRUE)
    if (is.null(point) || is.null(naive_se)) {
        cat("  failed; skip\n"); next
    }

    cat(sprintf("  running %d cluster bootstraps...\n", B))
    boots <- cluster_boot(sub, B)
    cat(sprintf("  %d successful bootstraps\n", length(boots)))

    all_keys <- unique(unlist(lapply(boots, names)))
    boot_mat <- do.call(rbind, lapply(boots, function(v) v[all_keys]))
    se_boot <- apply(boot_mat, 2L, sd, na.rm = TRUE)

    common <- intersect(names(point), all_keys)
    parsed_kq <- do.call(rbind, strsplit(common, "_"))
    cr <- data.table(age_group = as.integer(a),
                     ai_q = as.integer(parsed_kq[, 2]),
                     k = as.integer(parsed_kq[, 1]),
                     coef = unname(point[common]),
                     se_naive = unname(naive_se[common]),
                     se = unname(se_boot[common]),
                     n_obs = n_obs, n_occ = n_occ,
                     n_boot = length(boots))
    ref_rows <- data.table(age_group = as.integer(a),
                           ai_q = c(2L, 3L, 4L, 5L),
                           k = -1L, coef = 0, se_naive = 0, se = 0,
                           n_obs = n_obs, n_occ = n_occ,
                           n_boot = length(boots))
    coef_rows[[a]] <- rbindlist(list(cr, ref_rows))
    cat(sprintf("  saved %d coefs; median ratio se_boot/se_naive = %.3f\n",
                nrow(cr), median(cr$se / cr$se_naive, na.rm = TRUE)))
}

out <- rbindlist(coef_rows)
setorder(out, age_group, ai_q, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
