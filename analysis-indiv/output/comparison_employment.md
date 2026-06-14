# Specification comparison: per-age DiD-Poisson, employment (Q1 reference)

Coefficient (std. error) on `post x quintile`, employment count, private sector.
Each column is one specification; reading across a row isolates the factor
named in the chain (see DESIGN_CHOICES.md §22). Stars: * p<.10, ** p<.05, *** p<.01.

n_units = foretak (7b) / occupations (cell specs). The published-cell occupation
count is lower than the register cell specs because microdata.no suppresses small
cells -- a documented residual gap, not a like-for-like occupation universe.

## Age 21-30 (age_bin 1)

| Q vs Q1 | 7b firm-FE (firm x q + firm x t) | 7d cell-spec, restricted | 7d cell-spec, unrestricted_priv | published microdata.no cell |
|---|---|---|---|---|
| Q2 | +0.0611** (0.0276) | +0.0612* (0.0363) | +0.0513 (0.0362) | +0.0428 (0.0341) |
| Q3 | +0.0482*** (0.0184) | +0.0482** (0.0229) | +0.0488** (0.0198) | +0.0449** (0.0204) |
| Q4 | +0.0280* (0.0161) | +0.0246 (0.0212) | +0.0261 (0.0216) | +0.0193 (0.0203) |
| Q5 | +0.0132 (0.0210) | +0.0104 (0.0241) | +0.0204 (0.0214) | +0.0215 (0.0220) |

## Age 31-40 (age_bin 2)

| Q vs Q1 | 7b firm-FE (firm x q + firm x t) | 7d cell-spec, restricted | 7d cell-spec, unrestricted_priv | published microdata.no cell |
|---|---|---|---|---|
| Q2 | +0.0403** (0.0205) | +0.0247 (0.0426) | +0.0223 (0.0373) | +0.0181 (0.0357) |
| Q3 | +0.0252** (0.0125) | +0.0453** (0.0188) | +0.0433*** (0.0165) | +0.0432*** (0.0167) |
| Q4 | +0.0506*** (0.0108) | +0.0813*** (0.0174) | +0.0785*** (0.0196) | +0.0707*** (0.0169) |
| Q5 | +0.0511*** (0.0122) | +0.0847*** (0.0197) | +0.0755*** (0.0181) | +0.0783*** (0.0186) |

## Age 41-50 (age_bin 3)

| Q vs Q1 | 7b firm-FE (firm x q + firm x t) | 7d cell-spec, restricted | 7d cell-spec, unrestricted_priv | published microdata.no cell |
|---|---|---|---|---|
| Q2 | -0.0190 (0.0194) | -0.0328 (0.0417) | -0.0160 (0.0357) | -0.0206 (0.0339) |
| Q3 | -0.0122 (0.0113) | -0.0015 (0.0166) | -0.0015 (0.0158) | -0.0049 (0.0153) |
| Q4 | -0.0126 (0.0095) | +0.0060 (0.0153) | +0.0120 (0.0194) | +0.0000 (0.0154) |
| Q5 | -0.0207* (0.0108) | -0.0155 (0.0186) | -0.0159 (0.0169) | -0.0146 (0.0169) |

## Age 51-60 (age_bin 4)

| Q vs Q1 | 7b firm-FE (firm x q + firm x t) | 7d cell-spec, restricted | 7d cell-spec, unrestricted_priv | published microdata.no cell |
|---|---|---|---|---|
| Q2 | -0.0125 (0.0169) | -0.0060 (0.0335) | +0.0089 (0.0273) | +0.0080 (0.0268) |
| Q3 | +0.0090 (0.0107) | +0.0107 (0.0157) | +0.0108 (0.0136) | +0.0102 (0.0135) |
| Q4 | +0.0248*** (0.0089) | +0.0320** (0.0158) | +0.0390* (0.0215) | +0.0216 (0.0134) |
| Q5 | +0.0071 (0.0096) | +0.0093 (0.0193) | +0.0079 (0.0161) | +0.0103 (0.0166) |
