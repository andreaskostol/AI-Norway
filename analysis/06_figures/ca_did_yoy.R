# =============================================================================
# ca_did_yoy.R : CA pooled-DiD with YoY-matched ratio (robustness for
#                ca_did_yagan.R)
# =============================================================================
# Identical structure to ca_did_yagan.R but the baseline for month t is the
# single pre-window observation in the same calendar-month-of-year, with the
# pre-window fixed at k in [-12, -1] per anchor:
#
#   y_yoy_ratio_{c,t} = y_{c,t} / y_{c, m(t)}
#
# Three nested models per (outcome x timing x age):
#   M1 (exp):   y_yoy_ratio ~ i(kk, z_exp)                       | yrke4 + k
#   M2 (wage):  y_yoy_ratio ~ i(kk, z_wage)                      | yrke4 + k
#   M3 (full):  y_yoy_ratio ~ i(kk, z_exp) + i(kk, z_wage)
#                            + i(kk, z_expwage)                  | yrke4 + k
#
# Outputs:
#   analysis/output/coefficients/coef_ca_did_yoy.csv
#     schema: outcome, timing, age_group, model, term,
#             coef, se, n_obs, n_occ
#   analysis/output/coefficients/coef_ca_did_yoy_modelstats.csv
#     schema: outcome, timing, age_group, model, nobs, n_clusters, r2
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
                       "coef_ca_did_yoy.csv")
OUT_STATS <- file.path(BASE, "analysis", "output", "coefficients",
                       "coef_ca_did_yoy_modelstats.csv")

MIN_COUNT  <- 10L
ALDER_KEEP <- c("1", "2", "3", "4")
CONFIGS <- list(
    chatgpt = list(ref_ym = 2022L * 12L + 10L,
                   from   = as.IDate("1900-01-01"),
                   to     = as.IDate("2025-04-16")),
    agentic = list(ref_ym = 2025L * 12L +  4L,
                   from   = as.IDate("2023-07-16"),
                   to     = as.IDate("2100-01-01"))
)

# -----------------------------------------------------------------------------
# Load + build outcomes
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
# z_exp and z_wage
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
# Helpers
# -----------------------------------------------------------------------------
moy <- function(k, ref_ym) ((k + ref_ym + 1L - 1L) %% 12L) + 1L

balance <- function(sub, occvars) {
    grid <- CJ(yrke4 = occvars$yrke4, k = sort(unique(sub$k)))
    grid <- merge(grid, occvars, by = "yrke4", all.x = TRUE)
    out  <- merge(grid, sub[, .(yrke4, k, y)], by = c("yrke4", "k"),
                  all.x = TRUE)
    out[is.na(y), y := 0]
    out[, kk := ifelse(k >= 0L, "POST", as.character(k))]
    out
}

harvest <- function(fit, var) {
    if (is.null(fit)) return(c(NA_real_, NA_real_))
    ct <- as.data.frame(coeftable(fit))
    cand <- c(paste0("kk::POST:", var), paste0(var, ":kk::POST"))
    hit <- cand[cand %in% rownames(ct)]
    if (length(hit) == 0) return(c(NA_real_, NA_real_))
    c(ct[hit[1], "Estimate"], ct[hit[1], "Std. Error"])
}

# -----------------------------------------------------------------------------
# Main loop
# -----------------------------------------------------------------------------
rows <- list(); stat_rows <- list()
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
            occ <- merge(unique(sub[, .(yrke4)]), beta, by = "yrke4")
            occ <- merge(occ, wage[alder_gr == a, .(yrke4, ln_wage)],
                         by = "yrke4")
            occ <- occ[is.finite(ln_wage)]
            occ[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage)]
            occ[, z_expwage := z_exp * z_wage]
            occvars <- occ[, .(yrke4, z_exp, z_wage, z_expwage)]

            bal <- balance(sub[yrke4 %in% occvars$yrke4], occvars)
            bal[, month_of_year := moy(k, cfg$ref_ym)]
            base_yoy <- bal[k >= -12L & k <= -1L,
                            .(yrke4, month_of_year, base = y)]
            stopifnot(uniqueN(base_yoy, by = c("yrke4", "month_of_year")) ==
                       nrow(base_yoy))
            bal <- merge(bal, base_yoy,
                         by = c("yrke4", "month_of_year"), all.x = TRUE)
            bal[, y_yoy_ratio := ifelse(is.finite(base) & base > 0,
                                         y / base, NA_real_)]

            n_panel <- nrow(bal); n_occ_panel <- uniqueN(bal$yrke4)
            cat(sprintf("  age %s: n_panel=%d n_occ_panel=%d\n",
                        a, n_panel, n_occ_panel))

            est <- function(rhs) {
                f <- as.formula(paste("y_yoy_ratio ~", rhs, "| yrke4 + k"))
                d_fit <- bal[is.finite(base) & base > 0]
                tryCatch(
                    feols(f, data = d_fit, weights = ~base, cluster = ~yrke4),
                    error = function(e) {
                        cat(sprintf("    feols failed: %s\n",
                                    conditionMessage(e)))
                        NULL
                    })
            }

            m1 <- est("i(kk, z_exp,     ref = \"-1\")")
            m2 <- est("i(kk, z_wage,    ref = \"-1\")")
            m3 <- est(paste("i(kk, z_exp,     ref = \"-1\")",
                             "+ i(kk, z_wage,    ref = \"-1\")",
                             "+ i(kk, z_expwage, ref = \"-1\")"))

            fit_any <- if (!is.null(m3)) m3
                       else if (!is.null(m1)) m1
                       else if (!is.null(m2)) m2 else NULL
            n_obs_reg <- if (!is.null(fit_any)) nobs(fit_any)
                          else NA_integer_
            n_occ_reg <- if (!is.null(fit_any))
                              as.integer(fit_any$fixef_sizes[["yrke4"]])
                          else NA_integer_

            add <- function(fit, model, var, label) {
                v <- harvest(fit, var)
                data.table(outcome = oc,
                           timing = cfg_name, age_group = as.integer(a),
                           model = model, term = label,
                           coef = v[1], se = v[2],
                           n_obs = n_obs_reg, n_occ = n_occ_reg)
            }
            rows[[length(rows) + 1L]] <- rbindlist(list(
                add(m1, "m1", "z_exp",     "exp"),
                add(m2, "m2", "z_wage",    "wage"),
                add(m3, "m3", "z_exp",     "exp"),
                add(m3, "m3", "z_wage",    "wage"),
                add(m3, "m3", "z_expwage", "exp_x_wage")
            ))

            for (mm in c("m1", "m2", "m3")) {
                fit <- get(mm)
                if (is.null(fit)) next
                r2v <- tryCatch(as.numeric(r2(fit, "r2")),
                                error = function(e) NA_real_)
                stat_rows[[length(stat_rows) + 1L]] <- data.table(
                    outcome = oc,
                    timing = cfg_name, age_group = as.integer(a),
                    model = mm, nobs = nobs(fit),
                    n_clusters = as.integer(fit$fixef_sizes[["yrke4"]]),
                    r2 = r2v)
            }
        }
    }
}

out <- rbindlist(rows, use.names = TRUE)
setcolorder(out, c("outcome", "timing", "age_group",
                   "model", "term", "coef", "se", "n_obs", "n_occ"))
setorder(out, outcome, timing, age_group, model, term)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))

stats <- rbindlist(stat_rows, use.names = TRUE)
setcolorder(stats, c("outcome", "timing", "age_group",
                      "model", "nobs", "n_clusters", "r2"))
setorder(stats, outcome, timing, age_group, model)
fwrite(stats, OUT_STATS)
cat(sprintf("Saved %d model-stat rows to %s\n", nrow(stats), OUT_STATS))
