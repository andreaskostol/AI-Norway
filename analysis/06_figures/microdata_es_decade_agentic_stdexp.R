# =============================================================================
# microdata_es_decade_agentic_stdexp.R : continuous-exposure agentic event-study
# =============================================================================
# Identical to microdata_es_decade_agentic.R except the treatment is
# STANDARDIZED continuous Eloundou exposure z(beta) instead of quintile dummies.
# Re-anchored to April 2025 (last pre-agentic month); pre-window from 2023m7.
#
# Spec (per decade age group a):
#   log E[count_{j,t}] = alpha_j + beta_t
#                      + sum_{k != -1} delta_k * z(exp_j) * 1{k(t)=k}
#   k = months since April 2025 (Apr 2025 = -1, May 2025 = 0).
#   Window: 2023m7 through end of data (2026m2). Cluster SE at occupation.
#   Private sector (sekt==2).
#
# Output: analysis/output/coefficients/coef_microdata_es_decade_agentic_stdexp.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_microdata_es_decade_agentic_stdexp.csv")

REF_YM_INT  <- 2025L * 12L + 4L            # April 2025
WINDOW_FROM <- as.IDate("2023-07-16")      # 22 pre-period months
ALDER_KEEP  <- c("1", "2", "3", "4")

cat("Loading", DATA_FILE, "\n")
d <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                     alder_gr = "character",
                                     sekt = "integer",
                                     variable = "character",
                                     value = "numeric"))
d <- d[variable == "count" & sekt == 2L & alder_gr %in% ALDER_KEEP]
d[, date := as.IDate(date)]
d <- d[date >= WINDOW_FROM]
d[, ym_int := year(date) * 12L + month(date)]
d[, k := as.integer(ym_int - (REF_YM_INT + 1L))]   # Apr 2025 = k = -1
d <- d[, .(count = value, yrke4, alder_gr, k)]

cat(sprintf("k range: %d..%d\n", min(d$k), max(d$k)))

# standardized continuous exposure (each occupation counts once)
exp <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
exp[, yrke4 := sprintf("%04d", as.integer(styrk08))]
exp <- exp[!is.na(eloundou_beta), .(yrke4, beta = as.numeric(eloundou_beta))]
exp <- unique(exp, by = "yrke4")
exp[, z_exp := (beta - mean(beta)) / sd(beta)]
cat(sprintf("z_exp built on %d occupations (beta mean=%.3f sd=%.3f)\n",
            nrow(exp), mean(exp$beta), sd(exp$beta)))
d <- merge(d, exp[, .(yrke4, z_exp)], by = "yrke4")

balance <- function(sub) {
    yrke4s <- unique(sub$yrke4); ks <- sort(unique(sub$k))
    grid <- CJ(yrke4 = yrke4s, k = ks)
    grid <- merge(grid, unique(sub[, .(yrke4, z_exp)]),
                  by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, count)],
                 by = c("yrke4", "k"), all.x = TRUE)
    out[is.na(count), count := 0]
    out
}

coef_rows <- list()
for (a in ALDER_KEEP) {
    sub <- balance(d[alder_gr == a])
    n_obs <- nrow(sub); n_occ <- uniqueN(sub$yrke4)
    cat(sprintf("\n--- age group %s, n=%d, n_occ=%d ---\n", a, n_obs, n_occ))
    fit <- tryCatch(
        fepois(count ~ i(k, z_exp, ref = -1) | yrke4 + k,
               data = sub, cluster = ~yrke4),
        error = function(e) {
            cat("  fepois failed:", conditionMessage(e), "\n"); NULL })
    if (is.null(fit)) next
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    m <- regmatches(ct$name, regexec("k::(-?[0-9]+):z_exp", ct$name))
    ct$k <- sapply(m, function(x) if (length(x) == 2) as.integer(x[2]) else NA)
    ct <- ct[!is.na(ct$k), ]
    cr <- data.table(age_group = as.integer(a), k = ct$k,
                     coef = ct[, "Estimate"], se = ct[, "Std. Error"],
                     n_obs = n_obs, n_occ = n_occ)
    ref_row <- data.table(age_group = as.integer(a), k = -1L,
                          coef = 0, se = 0, n_obs = n_obs, n_occ = n_occ)
    coef_rows[[a]] <- rbindlist(list(cr, ref_row))
    cat(sprintf("  harvested %d coefs\n", nrow(cr)))
}

out <- rbindlist(coef_rows)
setorder(out, age_group, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
