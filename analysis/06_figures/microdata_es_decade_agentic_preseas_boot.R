# =============================================================================
# microdata_es_decade_agentic_preseas_boot.R : Cluster-bootstrap-korrigerte SE
#                                              for 2-stegs preseas-modell
#                                              (q x cal_month) for agentic.
# =============================================================================
# Step 1: q x cal_month seasonal pattern fra hele pre-treatment (52 mnd).
# Step 2: event-study paa BCC 22-mnd vindu med sesong-offset.
# Cluster bootstrap paa yrke4 over BEGGE stegene propagerer step-1-usikkerhet.
#
# CLI args: args[1] = B (default 200)
# Output: analysis/output/coefficients/coef_microdata_es_decade_agentic_preseas_boot.csv
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
                       "coef_microdata_es_decade_agentic_preseas_boot.csv")

REF_YM_INT  <- 2025L * 12L + 4L
K_ES_FROM   <- -22L                    # BCC 22-mo pre-window for step 2
K_SEAS_FROM <- -52L                    # 2021m1 (full pre-treatment)
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
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]
d[, cal_month := month(date)]
d <- d[, .(count = value, yrke4, alder_gr, k, cal_month)]

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
    out
}

# Step 1: q x cal_month FE on k in [-52, -1] (full pre-treatment).
# Step 2: event-study on k in [-22, end] (BCC window).
two_step_fit <- function(sub, return_se = FALSE, cluster_var = "yrke4") {
    seas <- sub[k >= K_SEAS_FROM & k < 0]
    fit_pre <- tryCatch(
        fepois(count ~ 1 | yrke4 + q_m_key, data = seas, warn = FALSE),
        error = function(e) NULL)
    if (is.null(fit_pre)) return(NULL)
    seas_fe <- fixef(fit_pre)[["q_m_key"]]
    seas_fe <- seas_fe - mean(seas_fe)

    es <- sub[k >= K_ES_FROM]
    es[, seas_offset := seas_fe[q_m_key]]
    es[is.na(seas_offset), seas_offset := 0]
    es[, ai_q_f := factor(ai_q, levels = 1:5)]

    cluster_form <- as.formula(paste("~", cluster_var))
    fit <- tryCatch(
        fepois(count ~ i(k, ai_q_f, ref = -1, ref2 = "3") | yrke4 + k,
               data = es, offset = ~seas_offset, cluster = cluster_form,
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

cluster_boot <- function(sub, B) {
    yrke4s_all <- unique(sub$yrke4)
    n_occ <- length(yrke4s_all)
    boot_estimates <- list()
    for (b in seq_len(B)) {
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
    cat(sprintf("  step1: k in [%d, -1], n_pre = %d\n",
                K_SEAS_FROM, nrow(sub[k >= K_SEAS_FROM & k < 0])))
    cat(sprintf("  step2: k in [%d, %d], n_es = %d\n",
                K_ES_FROM, max(sub$k), nrow(sub[k >= K_ES_FROM])))

    point <- two_step_fit(copy(sub), return_se = FALSE)
    naive_se <- two_step_fit(copy(sub), return_se = TRUE)
    if (is.null(point) || is.null(naive_se)) { cat("  failed; skip\n"); next }

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
