# =============================================================================
# 6e_ca_es_firmfe.R : comparative-advantage EVENT STUDY on individual-level
#                     (firm-FE) data — firm-FE analogue of chapter 1 of
#                     analysis/output/interaction_results.tex
# =============================================================================
# PURPOSE
#   The cell-level note (interaction_results.tex, §1) fits, per decade age group
#   and per timing (ChatGPT / agentic), the Poisson event study
#
#       log E[y_{j,t}] = a_j + b_t
#                      + sum_k [ d_exp(k) z(exp)_j
#                              + d_wage(k) z(lnw)_j
#                              + d_int(k) (z(exp) z(lnw))_j ] * 1{t=k}
#
#   with occupation (yrke4) FE a_j and month FE b_t, on microdata.no cell counts,
#   k = -1 (Oct 2022) reference. (In the microdata.no aggregate, private sector is
#   coded sekt == 2; on the secure register it is sekt == 3 = in_headline_priv,
#   which is what this script uses.)
#
#   This script reproduces that specification on the SECURE-SERVER individual-
#   level firm panel, replacing the FE structure with the BCC eq. 4.1 form
#   (DESIGN_CHOICES.md §3): firm x exposure-cell + firm x month, nothing else.
#   firm x month (frtk_id^ym) absorbs all firm-level time shocks (the BCC trick);
#   the exposure-cell FE absorbs firm-specific occupation baselines. TWO variants
#   of the exposure cell are run (arg fe=occ|quint|both):
#
#     fe=occ   : firm x OCCUPATION   (frtk_id^yrke4 + frtk_id^ym)
#                Continuous-treatment-faithful: the cell = the level at which
#                z_exp/z_wage vary. Absorbs firm-occupation baselines (subsumes a
#                plain occupation FE). Cleanest, but identifies only off firms
#                with >=2 occupations in the same age-month -> narrower sample.
#     fe=quint : firm x QUINTILE     (frtk_id^ai_q + frtk_id^ym)
#                BCC-literal coarse cell (5 bins). More firms qualify (>=2
#                quintiles) -> more power; but z_exp varies WITHIN quintile so
#                within-quintile occupation levels are not absorbed.
#
#   In both, the treatment i(k,z_exp)+i(k,z_wage)+i(k,z_expwage) survives the FE
#   (it varies by occupation x time within firm-month) and is identified within
#   firm over time -- exactly BCC's within-firm differential-exposure logic. The
#   aim is to see how close the event-study paths are to the cell-level note
#   (occupation + month FE) once we move to individual data and net out firm-time.
#
#   Per age bin and timing we fit TWO models (mirroring ca_es_stdexp.R):
#     FULL : i(k,z_exp) + i(k,z_wage) + i(k,z_expwage)   -> 3 term paths
#     EXP  : i(k,z_exp)                                   -> exposure-only path
#   for TWO outcomes: count_all (employment) and count_new (new hires).
#
# MEASUREMENT (kept identical to the cell-level note where possible)
#   z_exp  : Eloundou GPT-4 beta from styrk08_eloundou_beta_mapping.csv,
#            z-scored (pooled) over ALL mapped occupations. Identical object to
#            the cell-level note, so exposure is comparable across approaches.
#   z_wage : pre-ChatGPT (ym <= 2022m10) employment-weighted mean full-time-
#            equivalent wage per (yrke4, age_bin), logged, z-scored WITHIN age.
#            FTE = mean(lonn_kontant) * 100 / mean(arb_stillingspst) at cell
#            level (m_wage_all, m_position_all), aggregated count-weighted to
#            yrke4 x age. NB: this is computed natively on the secure sample
#            (private, sekt 3), so it is the secure-sample analogue of the
#            note's wage, not the identical vector.
#
# Inputs : $DATA/cells_flagged.rds
#          $DATA/styrk08_eloundou_beta_mapping.csv
# Outputs: $output/coefficients/coef_ca_es_firmfe.csv
#            (timing, outcome, fe, age_bin, term, k, coef, se, n_obs, n_frtk)
#            fe in {occ, quint}; term in {exp, wage, exp_x_wage, exp_only};
#            k=-1 reference row = 0
#          $output/log_6e_ca_es_firmfe.txt
#
# Usage  : cd H:\Dokumenter\ai_norway_indiv\scripts ; Rscript 6e_ca_es_firmfe.R
#          optional NAMED args (any order; all default to both):
#            outcome=count|nyjobb|both  timing=chatgpt|agentic|both
#            fe=occ|quint|both
#          e.g. Rscript 6e_ca_es_firmfe.R outcome=count timing=chatgpt fe=occ
#          The full event study on the firm x month panel is COMPUTE-HEAVY
#          (doubled when fe=both); subset via args to parallelise across runs.
# =============================================================================

if (file.exists("0_settings.R")) {
    source("0_settings.R")
} else if (file.exists("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")) {
    source("H:/Dokumenter/ai_norway_indiv/scripts/0_settings.R")
} else {
    stop("Cannot locate 0_settings.R. cd into the scripts folder before running.")
}

req("fixest"); req("data.table")   # req() comes from 0_settings.R

log_path <- file.path(OUTPUT, "log_6e_ca_es_firmfe.txt")
log_con  <- file(log_path, open = "wt")
sink(log_con, split = TRUE)
sink(log_con, type = "message")
close_log <- function() {
    try(sink(type = "message"), silent = TRUE)
    try(sink(),                 silent = TRUE)
    try(close(log_con),         silent = TRUE)
}
cat("== 6e_ca_es_firmfe.R starting ", format(Sys.time()), " ==\n")

# -----------------------------------------------------------------------------
# Arguments: which outcomes / timings to run
# -----------------------------------------------------------------------------
# Named args (key=value) so the script is robust to being sourced by 99_master.R
# with script-selector tokens present; unrecognized tokens are ignored.
args <- commandArgs(trailingOnly = TRUE)
getarg <- function(key, choices, default) {
    hit <- sub(paste0("^", key, "="), "",
               args[grepl(paste0("^", key, "="), args)])
    if (length(hit) && tolower(hit[1]) %in% choices) tolower(hit[1]) else default
}
OUTCOME_ARG <- getarg("outcome", c("count", "nyjobb", "both"), "both")
TIMING_ARG  <- getarg("timing",  c("chatgpt", "agentic", "both"), "both")
FE_ARG      <- getarg("fe",      c("occ", "quint", "both"), "both")
OUTCOMES <- if (OUTCOME_ARG == "both") c("count", "nyjobb") else OUTCOME_ARG
TIMINGS  <- if (TIMING_ARG  == "both") c("chatgpt", "agentic") else TIMING_ARG
FE_SPECS <- if (FE_ARG == "both") c("occ", "quint") else FE_ARG
YVAR <- c(count = "count_all", nyjobb = "count_new")
# Occupation-cell FE: firm x occupation (continuous-faithful) vs firm x quintile
# (BCC-literal). firm x month (frtk_id^ym) is always included on top.
FE_CELL <- c(occ = "frtk_id^yrke4", quint = "frtk_id^ai_q")
cat(sprintf("Outcomes: %s | Timings: %s | FE: %s\n",
            paste(OUTCOMES, collapse = ","), paste(TIMINGS, collapse = ","),
            paste(FE_SPECS, collapse = ",")))

# Per-timing event windows. k = ym - (ref_ym + 1), so the ref month is k = -1.
# ChatGPT window ends 2025m4 BY DESIGN (the pre-agentic period, matching the
# cell-level note) -- this is a definitional choice, NOT a stale data cutoff.
# The agentic window runs to the data edge (YM_PERIOD_END from 0_settings.R),
# so its post period grows with each delivery.
CONFIGS <- list(
    chatgpt = list(ref_ym = ym(2022, 10), from = ym(2021, 1), to = ym(2025, 4)),
    agentic = list(ref_ym = ym(2025,  4), from = ym(2023, 7), to = YM_PERIOD_END)
)

# -----------------------------------------------------------------------------
# z_exp: pooled z-score of Eloundou beta over ALL mapped occupations
#        (identical construction to ca_es_stdexp.R).
# -----------------------------------------------------------------------------
beta <- fread(file.path(DATA, "styrk08_eloundou_beta_mapping.csv"),
              colClasses = c(styrk08 = "character"))
beta[, yrke4 := sprintf("%04d", as.integer(styrk08))]
beta <- beta[!is.na(eloundou_beta), .(yrke4, b = as.numeric(eloundou_beta))]
beta <- unique(beta, by = "yrke4")
beta[, z_exp := (b - mean(b)) / sd(b)]
zexp <- beta[, .(yrke4, z_exp)]
cat(sprintf("z_exp built for %d occupations (pooled standardization)\n",
            nrow(zexp)))

# -----------------------------------------------------------------------------
# Load cells (private sector), pad yrke4 to 4 digits.
# -----------------------------------------------------------------------------
d <- load_cells()
cat(sprintf("Loaded %d rows from cells_flagged.rds\n", nrow(d)))
d <- d[in_headline_priv == 1]
# yrke4 is a plain zero-padded character in cells_flagged.rds; re-pad
# defensively so the inner-join with the styrk08 mapping cannot silently
# empty the panel on a formatting mismatch.
d[, yrke4 := pad0(yrke4, 4)]
cat(sprintf("After in_headline_priv filter: %d rows, %d distinct yrke4\n",
            nrow(d), uniqueN(d$yrke4)))

# -----------------------------------------------------------------------------
# z_wage: pre-ChatGPT employment-weighted ln FTE wage per (yrke4, age_bin),
#         z-scored within age. Computed once; used for both timings.
# -----------------------------------------------------------------------------
YM_PRE <- ym(2022, 10)   # last fully untreated ChatGPT month
pre <- d[ym <= YM_PRE & count_all > 0 &
         !is.na(m_wage_all) & m_wage_all > 0 &
         !is.na(m_position_all) & m_position_all >= 10]
wage <- pre[, .(wbar   = sum(count_all * m_wage_all)     / sum(count_all),
                posbar = sum(count_all * m_position_all) / sum(count_all)),
            by = .(yrke4, age_bin)]
wage[, fte := wbar * 100 / posbar]
wage <- wage[is.finite(fte) & fte > 0]
wage[, ln_wage := log(fte)]
wage[, z_wage := (ln_wage - mean(ln_wage)) / sd(ln_wage), by = age_bin]
zwage <- wage[, .(yrke4, age_bin, z_wage)]
cat(sprintf("z_wage built for %d (yrke4 x age) cells\n", nrow(zwage)))

# -----------------------------------------------------------------------------
# Harvest helpers (identical parsing to ca_es_stdexp.R; both FE (firm^yrke4 and
# firm^ym) are absorbed so the only coef names are the i(k, .) interactions
# "k::<int>:<var>").
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

# -----------------------------------------------------------------------------
# Main loop: outcome x timing x age_bin
# -----------------------------------------------------------------------------
rows <- list()
diag_rows <- list()
for (oc in OUTCOMES) {
    yv <- YVAR[[oc]]
    cat(sprintf("\n################ OUTCOME = %s (%s) ################\n", oc, yv))
    # collapse to (frtk_id, yrke4, age_bin, ym); carry ai_q (quintile, constant
    # within yrke4) for the firm x quintile FE variant; attach z_exp.
    dd <- d[, .(y = sum(.SD[[1L]]), ai_q = first(ai_q)),
            by = .(frtk_id, yrke4, age_bin, ym), .SDcols = yv]
    dd <- merge(dd, zexp, by = "yrke4")    # inner join: drops occ w/o exposure
    if (nrow(dd) == 0)
        stop("Empty panel after z_exp merge — check yrke4 vs styrk08 padding.")

    for (tm in TIMINGS) {
        cfg <- CONFIGS[[tm]]
        dt <- dd[ym >= cfg$from & ym <= cfg$to]
        dt[, k := as.integer(ym - (cfg$ref_ym + 1L))]
        dt <- dt[k >= KMIN & k <= KMAX]
        if (nrow(dt) == 0) {
            cat(sprintf("\n=== %s / %s : window empty within the panel, skip ===\n",
                        oc, tm))
            next
        }
        cat(sprintf("\n=== %s / %s : k %d..%d, %d rows ===\n",
                    oc, tm, min(dt$k), max(dt$k), nrow(dt)))

        for (a in 1:N_AGE_BINS) {
            sub <- dt[age_bin == a]
            zw_a <- zwage[age_bin == a, .(yrke4, z_wage)]
            sub <- merge(sub, zw_a, by = "yrke4")   # drops occ w/o wage
            sub[, z_expwage := z_exp * z_wage]
            n_obs <- nrow(sub); n_frtk <- uniqueN(sub$frtk_id)
            n_occ <- uniqueN(sub$yrke4)
            if (n_obs == 0 || !(-1 %in% sub$k)) {
                cat(sprintf("  age %d: no rows or no k=-1 reference, skip\n", a))
                next
            }

            for (fe in FE_SPECS) {
                fe_rhs <- paste("|", FE_CELL[[fe]], "+ frtk_id^ym")
                t0 <- Sys.time()
                ff <- function(rhs) tryCatch(
                    fepois(as.formula(paste("y ~", rhs, fe_rhs)),
                           data = sub, cluster = ~frtk_id),
                    error = function(e) {
                        cat("  fit failed:", conditionMessage(e), "\n"); NULL })
                fit_full <- ff(paste("i(k, z_exp, ref=-1)",
                                     "+ i(k, z_wage, ref=-1)",
                                     "+ i(k, z_expwage, ref=-1)"))
                fit_exp  <- ff("i(k, z_exp, ref=-1)")
                cat(sprintf("  age %d fe=%-5s: n=%d n_frtk=%d n_occ=%d fit %.1fs\n",
                            a, fe, n_obs, n_frtk, n_occ,
                            as.numeric(Sys.time() - t0, units = "secs")))
                diag_rows[[length(diag_rows) + 1]] <- fixest_diag_row(
                    fit_full, "6e", sprintf("%s_%s_%s_age%d_full", tm, oc, fe, a),
                    n_obs, n_frtk)
                diag_rows[[length(diag_rows) + 1]] <- fixest_diag_row(
                    fit_exp, "6e", sprintf("%s_%s_%s_age%d_exp_only", tm, oc, fe, a),
                    n_obs, n_frtk)

                parts <- list()
                if (!is.null(fit_full)) parts[[1]] <- harvest(fit_full)
                if (!is.null(fit_exp))
                    parts[[2]] <- harvest(fit_exp, fixed_term = "exp_only")
                ref <- data.table(
                    term = c("exp", "wage", "exp_x_wage", "exp_only"),
                    k = -1L, coef = 0, se = 0)
                got <- rbindlist(c(parts, list(ref)), use.names = TRUE)
                got[, `:=`(timing = tm, outcome = oc, fe = fe, age_bin = a,
                           n_obs = n_obs, n_frtk = n_frtk)]
                rows[[length(rows) + 1]] <- got
            }
        }
    }
    rm(dd); gc()
}

out <- rbindlist(rows, use.names = TRUE, fill = TRUE)
if (nrow(out) > 0)
    setcolorder(out, c("timing", "outcome", "fe", "age_bin", "term", "k",
                       "coef", "se", "n_obs", "n_frtk"))
if (nrow(out) > 0) setorder(out, timing, outcome, fe, age_bin, term, k)
atomic_fwrite(out, file.path(COEFS, "coef_ca_es_firmfe.csv"))
cat(sprintf("\nSaved %d rows to coef_ca_es_firmfe.csv\n", nrow(out)))

atomic_fwrite(rbindlist(diag_rows),
              file.path(DIAG, "fixest_diag_6e_ca_es_firmfe.csv"))
cat("Wrote diagnostics/fixest_diag_6e_ca_es_firmfe.csv\n")
cat("== 6e_ca_es_firmfe.R done ", format(Sys.time()), " ==\n")
close_log()
