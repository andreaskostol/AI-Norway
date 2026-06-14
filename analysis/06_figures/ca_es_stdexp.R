# =============================================================================
# ca_es_stdexp.R : event-study version of the full comparative-advantage model.
# =============================================================================
# Outcome parameterized via commandArgs[1] in {count, nyjobb} (default count):
#   count  : cell employment headcount.
#   nyjobb : new hires = round(count * ny_jobb share); cells with count >= 10.
#
# Per age group and timing (ChatGPT / agentic), TWO event-study fits:
#   FULL : y ~ i(k,z_exp) + i(k,z_wage) + i(k,z_expwage) | yrke4 + k
#   EXP  : y ~ i(k,z_exp) | yrke4 + k            (exposure-only reference path)
#   k=-1 reference for every term. z(exp) pooled across occupations; z(lnw)
#   standardized within age group; interaction = product. Private sector; occ +
#   month FE; SE clustered at occupation.
#   ChatGPT: ref Oct 2022, through 2025m4. Agentic: ref Apr 2025, from 2023m7.
#
# Output: analysis/output/coefficients/coef_ca_es_stdexp[_<outcome>].csv
#         (timing, age_group, term, k, coef, se) ; term in
#         {exp, wage, exp_x_wage, exp_only}
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
                       paste0("coef_ca_es_stdexp", SUF, ".csv"))

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

# build outcome column y per (date, yrke4, alder_gr)
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
beta[, z_exp := (beta - mean(beta)) / sd(beta)]    # pooled

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
    out
}

parse_term <- function(nm) {
    if (grepl("z_expwage", nm)) "exp_x_wage"
    else if (grepl("z_wage", nm)) "wage"
    else if (grepl("z_exp", nm)) "exp"
    else NA_character_
}

harvest <- function(fit, timing, a, fixed_term = NULL) {
    ct <- as.data.frame(coeftable(fit)); ct$name <- rownames(ct)
    ct$k <- as.integer(sub("\\D*k::(-?[0-9]+).*", "\\1", ct$name))
    ct$term <- if (is.null(fixed_term)) vapply(ct$name, parse_term, character(1))
               else fixed_term
    ct <- ct[!is.na(ct$k) & !is.na(ct$term), ]
    data.table(timing = timing, age_group = as.integer(a), term = ct$term,
               k = ct$k, coef = ct[, "Estimate"], se = ct[, "Std. Error"])
}

rows <- list()
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
        occ[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage)]
        occ[, z_expwage := z_exp * z_wage]
        occvars <- occ[, .(yrke4, z_exp, z_wage, z_expwage)]
        bal <- balance(sub[yrke4 %in% occvars$yrke4], occvars)
        bal <- merge(bal, base_w[alder_gr == a, .(yrke4, w)], by = "yrke4",
                     all.x = TRUE)
        n_occ <- uniqueN(bal$yrke4)

        ff <- function(rhs) tryCatch({
            if (ESTIMATOR == "ppml")
                fepois(as.formula(paste("y ~", rhs, "| yrke4 + k")),
                       data = bal, cluster = ~yrke4)
            else
                feols(as.formula(paste("log(y) ~", rhs, "| yrke4 + k")),
                      data = bal[y > 0 & is.finite(w) & w > 0],
                      weights = ~w, cluster = ~yrke4)
        }, error = function(e) { cat("  failed:", conditionMessage(e), "\n")
                                 NULL })
        fit_full <- ff("i(k, z_exp, ref=-1) + i(k, z_wage, ref=-1) + i(k, z_expwage, ref=-1)")
        fit_exp  <- ff("i(k, z_exp, ref=-1)")
        parts <- list()
        if (!is.null(fit_full)) parts[[1]] <- harvest(fit_full, cfg_name, a)
        if (!is.null(fit_exp))
            parts[[2]] <- harvest(fit_exp, cfg_name, a, fixed_term = "exp_only")
        ref <- data.table(timing = cfg_name, age_group = as.integer(a),
                          term = c("exp", "wage", "exp_x_wage", "exp_only"),
                          k = -1L, coef = 0, se = 0)
        rows[[length(rows) + 1]] <- rbindlist(c(parts, list(ref)),
                                              use.names = TRUE)
        cat(sprintf("  age %s: n_occ=%d\n", a, n_occ))
    }
}

out <- rbindlist(rows)
setorder(out, timing, age_group, term, k)
dir.create(dirname(OUT_CSV), showWarnings = FALSE, recursive = TRUE)
fwrite(out, OUT_CSV)
cat(sprintf("\nSaved %d rows to %s\n", nrow(out), OUT_CSV))
