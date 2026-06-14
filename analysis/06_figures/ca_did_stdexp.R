# =============================================================================
# ca_did_stdexp.R : pooled post-treatment (DiD) Poisson estimates, continuous
#                   standardized exposure and wage, per age group.
# =============================================================================
# Outcome parameterized via commandArgs[1] in {count, nyjobb} (default count):
#   count  : cell employment headcount.
#   nyjobb : new hires = round(count * ny_jobb share); cells with count >= 10.
#
# For each timing (ChatGPT, agentic) and each decade age group, three nested
# regressions (Post = 1{k >= 0}, pre-period reference):
#   M1 (exp):   log E[y] = a_j + b_t + d_exp z(exp) Post
#   M2 (wage):  log E[y] = a_j + b_t + d_wage z(lnw) Post
#   M3 (full):  log E[y] = a_j + b_t + d_exp z(exp)Post + d_wage z(lnw)Post
#                                    + d_int (z(exp)*z(lnw)) Post
#   d_* = average post-treatment effect on log y per SD. z(exp) pooled across
#   occupations; z(lnw) standardized within age group. Private sector; occ +
#   month FE; SE clustered at occupation.
#
# Output: analysis/output/coefficients/coef_ca_did_stdexp[_<outcome>].csv
#         and ..._modelstats.csv
# =============================================================================

suppressMessages({ library(data.table); library(fixest) })

args <- commandArgs(trailingOnly = TRUE)
OUTCOME <- if (length(args) >= 1) args[1] else "count"
stopifnot(OUTCOME %in% c("count", "nyjobb"))
SUF <- if (OUTCOME == "count") "" else paste0("_", OUTCOME)
ESTIMATOR <- if (length(args) >= 2) args[2] else "ppml"  # ppml | olslog
stopifnot(ESTIMATOR %in% c("ppml", "olslog"))
if (ESTIMATOR == "olslog") SUF <- paste0(SUF, "_olslog")
MIN_COUNT <- 10L

BASE <- getwd()
DATA_FILE <- file.path(BASE, "microdata-output",
                       "09_occ_agedecade_sektor_kpos_2021m01_2026m02_parsed.csv")
EXP_FILE  <- file.path(BASE, "data", "ai_exposure",
                       "styrk08_eloundou_beta_mapping.csv")
WAGE_FILE <- file.path(BASE, "analysis", "output",
                       "occ_age_exp_wage_prechatgpt.csv")
OUT_CSV   <- file.path(BASE, "analysis", "output", "coefficients",
                       paste0("coef_ca_did_stdexp", SUF, ".csv"))
OUT_STATS <- file.path(BASE, "analysis", "output", "coefficients",
                       paste0("coef_ca_did_stdexp", SUF, "_modelstats.csv"))

ALDER_KEEP <- c("1", "2", "3", "4")
CONFIGS <- list(
    chatgpt = list(ref_ym = 2022L * 12L + 10L,
                   from = as.IDate("1900-01-01"), to = as.IDate("2025-04-16")),
    agentic = list(ref_ym = 2025L * 12L + 4L,
                   from = as.IDate("2023-07-16"), to = as.IDate("2100-01-01")))

cat(sprintf("OUTCOME = %s\n", OUTCOME))
vars_keep <- if (OUTCOME == "nyjobb") c("count", "ny_jobb") else "count"
raw <- fread(DATA_FILE, colClasses = c(yrke4 = "character",
                                       alder_gr = "character",
                                       sekt = "integer",
                                       variable = "character",
                                       value = "numeric"))
raw <- raw[sekt == 2L & alder_gr %in% ALDER_KEEP & variable %in% vars_keep]
raw[, date := as.IDate(date)]
if (OUTCOME == "count") {
    dy <- raw[variable == "count", .(date, yrke4, alder_gr, y = value)]
} else {
    dw <- dcast(raw, date + yrke4 + alder_gr ~ variable, value.var = "value")
    dw <- dw[!is.na(count) & count >= MIN_COUNT & !is.na(ny_jobb)]
    dy <- dw[, .(date, yrke4, alder_gr,
                 y = as.integer(round(count * ny_jobb)))]
}

beta <- fread(EXP_FILE, colClasses = c(styrk08 = "character"))
beta[, yrke4 := sprintf("%04d", as.integer(styrk08))]
beta <- beta[!is.na(eloundou_beta), .(yrke4, beta = as.numeric(eloundou_beta))]
beta <- unique(beta, by = "yrke4")
beta[, z_exp := (beta - mean(beta)) / sd(beta)]   # pooled, matches ES scripts

wage <- fread(WAGE_FILE, colClasses = c(yrke4 = "character",
                                        alder_gr = "character"))
wage <- wage[, .(yrke4, alder_gr, ln_wage = as.numeric(ln_wage))]
wage[, yrke4 := sprintf("%04d", as.integer(yrke4))]

balance <- function(sub, occvars) {
    grid <- CJ(yrke4 = occvars$yrke4, k = sort(unique(sub$k)))
    grid <- merge(grid, occvars, by = "yrke4", all.x = TRUE)
    out <- merge(grid, sub[, .(yrke4, k, y)], by = c("yrke4", "k"),
                 all.x = TRUE)
    out[is.na(y), y := 0]
    # kk: each pre-month kept as its own level; all post months collapsed to
    # "POST"; k = -1 is the reference. The POST coefficient is then the average
    # post-period effect relative to the reference month (pre-months controlled).
    out[, kk := ifelse(k >= 0L, "POST", as.character(k))]
    out
}

harvest <- function(fit, var) {
    ct <- as.data.frame(coeftable(fit))
    cand <- c(paste0("kk::POST:", var), paste0(var, ":kk::POST"))
    hit <- cand[cand %in% rownames(ct)]
    if (length(hit) == 0) return(c(NA, NA))
    c(ct[hit[1], "Estimate"], ct[hit[1], "Std. Error"])
}

rows <- list()
stat_rows <- list()
for (cfg_name in names(CONFIGS)) {
    cfg <- CONFIGS[[cfg_name]]
    d <- dy[date >= cfg$from & date <= cfg$to]
    d[, ym_int := year(date) * 12L + month(date)]
    d[, k := as.integer(ym_int - (cfg$ref_ym + 1L))]
    base_w <- d[k < 0, .(w = mean(y)), by = .(yrke4, alder_gr)]  # fixed weight
    cat(sprintf("\n=== %s : k %d..%d ===\n", cfg_name, min(d$k), max(d$k)))

    for (a in ALDER_KEEP) {
        sub <- d[alder_gr == a]
        occ <- merge(unique(sub[, .(yrke4)]), beta, by = "yrke4")
        occ <- merge(occ, wage[alder_gr == a, .(yrke4, ln_wage)], by = "yrke4")
        occ <- occ[is.finite(ln_wage)]
        # z_exp pooled (carried from beta); z_wage age-specific
        occ[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage)]
        occ[, z_expwage := z_exp * z_wage]
        occvars <- occ[, .(yrke4, z_exp, z_wage, z_expwage)]

        bal <- balance(sub[yrke4 %in% occvars$yrke4], occvars)
        bal <- merge(bal, base_w[alder_gr == a, .(yrke4, w)], by = "yrke4",
                     all.x = TRUE)
        n_obs <- nrow(bal); n_occ <- uniqueN(bal$yrke4)
        cat(sprintf("  age %s: n=%d n_occ=%d\n", a, n_obs, n_occ))

        est <- function(rhs) {
            f <- as.formula(paste(if (ESTIMATOR == "ppml") "y ~" else "log(y) ~",
                                  rhs, "| yrke4 + k"))
            if (ESTIMATOR == "ppml")
                fepois(f, bal, cluster = ~yrke4)
            else
                feols(f, bal[y > 0 & is.finite(w) & w > 0], weights = ~w,
                      cluster = ~yrke4)
        }
        m1 <- est("i(kk, z_exp, ref = \"-1\")")
        m2 <- est("i(kk, z_wage, ref = \"-1\")")
        m3 <- est("i(kk, z_exp, ref = \"-1\") + i(kk, z_wage, ref = \"-1\") + i(kk, z_expwage, ref = \"-1\")")

        add <- function(model, var, label) {
            v <- harvest(get(model), var)
            data.table(timing = cfg_name, age_group = as.integer(a),
                       model = model, term = label,
                       coef = v[1], se = v[2], n_obs = n_obs, n_occ = n_occ)
        }
        rows[[length(rows) + 1]] <- rbindlist(list(
            add("m1", "z_exp", "exp"),
            add("m2", "z_wage", "wage"),
            add("m3", "z_exp", "exp"),
            add("m3", "z_wage", "wage"),
            add("m3", "z_expwage", "exp_x_wage")))

        for (mm in c("m1", "m2", "m3")) {
            fit <- get(mm)
            pr2 <- tryCatch(as.numeric(r2(fit,
                            if (ESTIMATOR == "ppml") "pr2" else "r2")),
                            error = function(e) NA_real_)
            stat_rows[[length(stat_rows) + 1]] <- data.table(
                timing = cfg_name, age_group = as.integer(a), model = mm,
                nobs = nobs(fit),
                n_clusters = as.integer(fit$fixef_sizes[["yrke4"]]),
                pr2 = pr2)
        }
    }
}

out <- rbindlist(rows)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
stats <- rbindlist(stat_rows)
fwrite(stats, OUT_STATS)
cat(sprintf("Saved %d model-stat rows to %s\n", nrow(stats), OUT_STATS))
