user_lib <- "C:/Users/Øystein M. Hernæs/R/win-library/4.1"
if (dir.exists(user_lib)) .libPaths(c(user_lib, .libPaths()))
suppressMessages(library(data.table))

BASE <- getwd()
if (!file.exists(file.path(BASE, "analysis/output/coefficients/coef_microdata_poisson_es.csv"))) {
    BASE <- "c:/Frischsenteret Dropbox/Øystein Hernæs/Research Hernaes/AI-Norway"
}

py <- fread(file.path(BASE, "analysis/output/coefficients/coef_microdata_poisson_es.csv"))
r  <- fread(file.path(BASE, "analysis/output/coefficients/coef_microdata_poisson_es_R.csv"))

setnames(py, c("coef","se"), c("coef_py","se_py"))
setnames(r,  c("coef","se"), c("coef_R","se_R"))
m <- merge(py[, .(age_bin, ai_q, k, coef_py, se_py)],
           r[,  .(age_bin, ai_q, k, coef_R,  se_R)],
           by = c("age_bin","ai_q","k"))
m[, d_coef := coef_py - coef_R]
m[, d_se   := se_py   - se_R  ]

cat("Rows compared:", nrow(m), "\n")
cat("max  |coef_py - coef_R| =", format(max(abs(m$d_coef)), digits = 4), "\n")
cat("mean |coef_py - coef_R| =", format(mean(abs(m$d_coef)), digits = 4), "\n")
cat("max  |se_py   - se_R|   =", format(max(abs(m$d_se)), digits = 4), "\n")
cat("mean |se_py   - se_R|   =", format(mean(abs(m$d_se)), digits = 4), "\n\n")

cat("Largest 10 coef discrepancies:\n")
print(m[order(-abs(d_coef))][1:10, .(age_bin, ai_q, k, coef_py, coef_R, d_coef)])

cat("\nLargest 10 SE discrepancies:\n")
print(m[order(-abs(d_se))][1:10, .(age_bin, ai_q, k, se_py, se_R, d_se)])

cat("\nQ5, age_bin = 1, k in {-12, 0, 12, 24, 36}:\n")
print(m[ai_q == 5 & age_bin == 1 & k %in% c(-12, 0, 12, 24, 36),
        .(k, coef_py, coef_R, se_py, se_R)])
