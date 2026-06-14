# =============================================================================
# ca_es_yagan.R : CA event study with Yagan (2020) relative outcome (ratio)
# =============================================================================
# Mirrors ca_es_stdexp.R but replaces Poisson PPML on raw counts with linear
# OLS (feols) on the Yagan ratio outcome computed at the
# (yrke4, alder_gr, sektor) cell level, sektor = 2 (private):
#
#   y_ratio_{c,t} = y_{c,t} / mean(y_{c, pre})       unitless, 1 = baseline
#                                                    (Yagan Fig. 6B)
#
# The baseline is the mean of y over the 12 months immediately preceding
# the anchor's reference month (k in [-12, -1]):
#   chatgpt : ref_ym = ym(2022, 10), pre = 2021m11..2022m10
#   agentic : ref_ym = ym(2025,  4), pre = 2024m05..2025m04
#
# Per (anchor x age x timing) we fit, for each outcome (count / nyjobb),
# the same FULL and EXP-only event-study specifications as ca_es_stdexp.R:
#   FULL : y_ratio ~ i(k, z_exp) + i(k, z_wage) + i(k, z_expwage) | yrke4 + k
#   EXP  : y_ratio ~ i(k, z_exp)                                  | yrke4 + k
# Cells weighted by the anchor's baseline mean count (same convention as
# ca_es_stdexp.R's olslog variant); SE clustered at occupation.
#
# Output: analysis/output/coefficients/coef_ca_es_yagan.csv
#   schema: outcome, timing, age_group, term, k, coef, se, n_obs
#     outcome in {count, nyjobb}; term in {exp, wage, exp_x_wage, exp_only};
#     k = -1 reference row added with coef = 0, se = 0 for each
#     (outcome x timing x age x term).
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

BASE      <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
WAGE_FILE <- file.path(BASE, "analysis", "output",
                       "occ_age_exp_wage_prechatgpt.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_ca_es_yagan.csv")

MIN_COUNT  <- 10L
ALDER_KEEP <- c("1", "2", "3", "4")

# Two anchors. ref_ym is the LAST untreated month (k = -1).
# from / to define the panel window passed to the regression (same as the
# PPML script's CONFIGS); pre-window for the Yagan baseline is k in [-12, -1]
# inside that panel.
CONFIGS <- list(
    chatgpt = list(ref_ym = 2022L * 12L + 10L,
                   from   = as.IDate("1900-01-01"),
                   to     = as.IDate("2025-04-16")),
    agentic = list(ref_ym = 2025L * 12L +  4L,
                   from   = as.IDate("2023-07-16"),
                   to     = as.IDate("2100-01-01"))
)

# -----------------------------------------------------------------------------
# Load + build outcomes (count and nyjobb)
# -----------------------------------------------------------------------------
raw <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                       alder_gr = "character",
                                       sekt = "integer",
                                       variable = "character",
                                       value = "numeric"))
raw <- raw[sekt == 2L & alder_gr %in% ALDER_KEEP &
           variable %in% c("count", "ny_jobb")]
raw[, date := as.IDate(date)]

dy_count  <- raw[variable == "count", .(date, yrke4, alder_gr, y = value)]
dw <- dcast(raw, date + yrke4 + alder_gr ~ variable, value.var = "value")
dw <- dw[!is.na(count) & count >= MIN_COUNT & !is.na(ny_jobb)]
dy_nyjobb <- dw[, .(date, yrke4, alder_gr,
                    y = as.integer(round(count * ny_jobb)))]

DY <- list(count = dy_count, nyjobb = dy_nyjobb)
rm(raw, dw, dy_count, dy_nyjobb); gc()

# -----------------------------------------------------------------------------
# z_exp (pooled) and z_wage (within age) — identical to ca_es_stdexp.R
# -----------------------------------------------------------------------------
beta <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
beta[, yrke4 := sprintf("%04d", as.integer(styrk08))]
beta <- beta[!is.na(eloundou_beta), .(yrke4, beta = as.numeric(eloundou_beta))]
beta <- unique(beta, by = "yrke4")
beta[, z_exp := (beta - mean(beta)) / sd(beta)]

wage <- fread(WAGE_FILE, colClasses = c(yrke4 = "character",
                                        alder_gr = "character"))
wage <- wage[, .(yrke4, alder_gr, ln_wage = as.numeric(ln_wage))]
wage[, yrke4 := sprintf("%04d", as.integer(yrke4))]

# -----------------------------------------------------------------------------
# Helpers (parse_term, harvest) identical to ca_es_stdexp.R
# -----------------------------------------------------------------------------
parse_term <- function(nm) {
    if (grepl("z_expwage", nm)) "exp_x_wage"
    else if (grepl("z_wage", nm)) "wage"
    else if (grepl("z_exp",  nm)) "exp"
    else NA_character_
}

harvest <- function(fit, fixed_term = NULL) {
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    ct$k <- as.integer(sub("\\D*k::(-?[0-9]+).*", "\\1", ct$name))
    ct$term <- if (is.null(fixed_term)) vapply(ct$name, parse_term, character(1))
               else fixed_term
    ct <- ct[!is.na(ct$k) & !is.na(ct$term), ]
    data.table(term = ct$term, k = ct$k,
               coef = ct[, "Estimate"], se = ct[, "Std. Error"])
}

# Build a balanced (yrke4 x k) panel and attach occupation-level treatment
# variables. Missing cell-months are set to y = 0 (= the cell had no workers
# of this age in that month, the cell-aggregate analogue of Yagan's binary
# "non-employed" individual).
balance <- function(sub, occvars) {
    grid <- CJ(yrke4 = occvars$yrke4, k = sort(unique(sub$k)))
    grid <- merge(grid, occvars, by = "yrke4", all.x = TRUE)
    out  <- merge(grid, sub[, .(yrke4, k, y)], by = c("yrke4", "k"),
                  all.x = TRUE)
    out[is.na(y), y := 0]
    out
}

# -----------------------------------------------------------------------------
# Main loop : outcome x anchor x age x variant
# -----------------------------------------------------------------------------
rows <- list()
for (oc in c("count", "nyjobb")) {
    dy <- DY[[oc]]
    for (cfg_name in names(CONFIGS)) {
        cfg <- CONFIGS[[cfg_name]]
        d <- dy[date >= cfg$from & date <= cfg$to]
        d[, ym_int := year(date) * 12L + month(date)]
        d[, k := as.integer(ym_int - (cfg$ref_ym + 1L))]
        cat(sprintf("\n=== %s / %s : k %d..%d ===\n",
                    oc, cfg_name, min(d$k), max(d$k)))

        for (a in ALDER_KEEP) {
            sub <- d[alder_gr == a]

            # Treatment variables (z_exp pooled, z_wage age-specific)
            occ <- merge(unique(sub[, .(yrke4)]), beta, by = "yrke4")
            occ <- merge(occ, wage[alder_gr == a, .(yrke4, ln_wage)],
                         by = "yrke4")
            occ <- occ[is.finite(ln_wage)]
            occ[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage)]
            occ[, z_expwage := z_exp * z_wage]
            occvars <- occ[, .(yrke4, z_exp, z_wage, z_expwage)]

            bal <- balance(sub[yrke4 %in% occvars$yrke4], occvars)

            # 12-month Yagan baseline within this (oc x anchor x age) panel.
            # The pre-window is k in [-12, -1] for both anchors by construction.
            base_y <- bal[k >= -12L & k <= -1L,
                          .(base = mean(y)), by = yrke4]
            bal <- merge(bal, base_y, by = "yrke4", all.x = TRUE)

            # Yagan ratio (1 = baseline). Cells with base = 0 are dropped
            # (the ratio is undefined and feols rejects weights = 0).
            bal[, y_ratio := ifelse(is.finite(base) & base > 0,
                                    y / base, NA_real_)]

            n_panel <- nrow(bal); n_occ_panel <- uniqueN(bal$yrke4)
            cat(sprintf("  age %s: n_panel=%d n_occ_panel=%d\n",
                        a, n_panel, n_occ_panel))

            # Estimator: feols with baseline-mean weight (same convention as
            # ca_es_stdexp.R's olslog variant). yrke4 + k FE; cluster at yrke4.
            est <- function(rhs) {
                f <- as.formula(paste("y_ratio ~", rhs, "| yrke4 + k"))
                d_fit <- bal[is.finite(base) & base > 0]
                tryCatch(
                    feols(f, data = d_fit, weights = ~base, cluster = ~yrke4),
                    error = function(e) {
                        cat(sprintf("    feols failed (%s): %s\n",
                                    substr(rhs, 1, 30),
                                    conditionMessage(e)))
                        NULL
                    })
            }

            fit_full <- est(paste("i(k, z_exp, ref=-1)",
                                  "+ i(k, z_wage, ref=-1)",
                                  "+ i(k, z_expwage, ref=-1)"))
            fit_exp  <- est("i(k, z_exp, ref=-1)")

            n_obs_reg <- if (!is.null(fit_full)) nobs(fit_full)
                         else if (!is.null(fit_exp)) nobs(fit_exp)
                         else NA_integer_

            parts <- list()
            if (!is.null(fit_full)) parts[[1]] <- harvest(fit_full)
            if (!is.null(fit_exp))
                parts[[2]] <- harvest(fit_exp, fixed_term = "exp_only")
            ref <- data.table(
                term = c("exp", "wage", "exp_x_wage", "exp_only"),
                k = -1L, coef = 0, se = 0)
            got <- rbindlist(c(parts, list(ref)), use.names = TRUE)
            got[, `:=`(outcome = oc, timing = cfg_name,
                       age_group = as.integer(a),
                       n_obs = n_obs_reg)]
            rows[[length(rows) + 1L]] <- got
        }
    }
}

# -----------------------------------------------------------------------------
# Save
# -----------------------------------------------------------------------------
out <- rbindlist(rows, use.names = TRUE)
setcolorder(out, c("outcome", "timing", "age_group",
                   "term", "k", "coef", "se", "n_obs"))
setorder(out, outcome, timing, age_group, term, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
