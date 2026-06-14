# =============================================================================
# microdata_es_decade_q3_preseas_boot.R : Cluster-bootstrap-corrected SE for
#                                         the 2-step pre-period-seasonal
#                                         Q3-referenced ChatGPT event-study.
# =============================================================================
# Loeser generated-regressor-problemet: naive step-2 SE underestimerer fordi
# de behandler step-1 seasonal FE (delta_{q,m}) som kjent, men den har
# sampling error. Cluster bootstrap paa yrke4-nivaa over baade step 1 og
# step 2 propagerer step-1-usikkerhet inn i step-2 SE.
#
# Referanser:
#   - Murphy & Topel (1985, JBES) for analytisk korreksjon
#   - Abadie et al (2023) for moderne klyngebootstrap
#   - did2s (Callaway-Goodman-Bacon-Sant'Anna) for 2-stegs DiD-bootstrap
#
# Algoritme (per aldersgruppe):
#   1. Kjor original 2-stegs-spesifikasjon (gir punktestimat gamma_hat)
#   2. For b = 1..B:
#      a. Sample yrke4 med replacement (med yrke4-multiplisitet beholdt
#         som distinkte cluster-ID-er)
#      b. Steg 1 paa bootstrap pre-period -> delta_hat^(b)
#      c. Steg 2 paa full bootstrap-sample med offset = delta_hat^(b)
#      d. Lagre gamma_hat^(b)
#   3. SE_boot = sd over b av gamma_hat^(b)
#
# CLI args:
#   args[1] = B (antall bootstrap-iterasjoner, default 200)
#   args[2] = age_group (1..4, default kjor alle)
#
# Input:  microdata-output/09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv
# Output: analysis/output/coefficients/coef_microdata_es_decade_q3_preseas_boot.csv
#         (samme schema som ikke-boot, men SE er bootstrap-basert)
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
                       "coef_microdata_es_decade_q3_preseas_boot.csv")

REF_YM_INT  <- 2022L * 12L + 10L
CUTOFF_DATE <- as.IDate("2025-04-16")
ALDER_KEEP  <- c("1", "2", "3", "4")
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
d <- d[date <= CUTOFF_DATE]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, cal_month := month(date)]
d <- d[, .(count = value, yrke4, alder_gr, k, cal_month)]

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
    out
}

# One 2-step fit. Step 1: q x cal_month FE on pre-period.
# Step 2: i(k, ai_q) | yrke4 + k with offset from step 1.
two_step_fit <- function(sub, return_se = FALSE, cluster_var = "yrke4") {
    pre <- sub[k < 0]
    fit_pre <- tryCatch(
        fepois(count ~ 1 | yrke4 + q_m_key, data = pre, warn = FALSE),
        error = function(e) NULL)
    if (is.null(fit_pre)) return(NULL)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_fe <- seas_fe - mean(seas_fe)
    sub[, seas_offset := seas_fe[q_m_key]]
    sub[is.na(seas_offset), seas_offset := 0]
    sub[, ai_q_f := factor(ai_q, levels = 1:5)]

    cluster_form <- as.formula(paste("~", cluster_var))
    fit <- tryCatch(
        fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "3") | yrke4 + k,
               data = sub, offset = ~seas_offset, cluster = cluster_form,
               warn = FALSE),
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

# Cluster bootstrap: resample yrke4 with replacement, run 2-step, store gamma.
cluster_boot <- function(sub, B) {
    yrke4s_all <- unique(sub$yrke4)
    n_occ <- length(yrke4s_all)
    boot_estimates <- list()
    for (b in seq_len(B)) {
        # Sample yrke4 with replacement; same yrke4 drawn k times gives
        # k distinct boot clusters to preserve cluster structure.
        drawn <- sample(yrke4s_all, n_occ, replace = TRUE)
        boot_sub <- rbindlist(lapply(seq_along(drawn), function(i) {
            s <- copy(sub[yrke4 == drawn[i]])
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
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n=== age group %s, n=%d, n_occ=%d ===\n",
                a, n_obs, n_occ))

    # Point estimate (from full sample)
    point <- two_step_fit(copy(sub), return_se = FALSE)
    naive_se <- two_step_fit(copy(sub), return_se = TRUE)
    if (is.null(point) || is.null(naive_se)) {
        cat("  failed; skip\n"); next
    }

    # Bootstrap
    cat(sprintf("  running %d cluster bootstraps...\n", B))
    boots <- cluster_boot(sub, B)
    cat(sprintf("  %d successful bootstraps\n", length(boots)))

    # Compute bootstrap SE per (k, q): SD across boot iterations
    all_keys <- unique(unlist(lapply(boots, names)))
    boot_mat <- do.call(rbind, lapply(boots, function(v) {
        v[all_keys]
    }))
    se_boot <- apply(boot_mat, 2L, sd, na.rm = TRUE)

    # Match to point estimate (use all_keys order)
    common <- intersect(names(point), all_keys)
    parsed_kq <- do.call(rbind, strsplit(common, "_"))
    cr <- data.table(age_group = as.integer(a),
                     ai_q = as.integer(parsed_kq[, 2]),
                     k = as.integer(parsed_kq[, 1]),
                     coef = unname(point[common]),
                     se_naive = unname(naive_se[common]),
                     se = unname(se_boot[common]),  # bootstrap SE
                     n_obs = n_obs, n_occ = n_occ,
                     n_boot = length(boots))
    ref_rows <- data.table(age_group = as.integer(a),
                           ai_q = c(1L, 2L, 4L, 5L),
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
