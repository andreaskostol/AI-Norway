# seasonal.R
#
# R port of analysis/06_figures/seasonal.py -- the shared X-11-style seasonal
# adjustment used by the kiindeksen.no dashboard and the paper. Keeping an exact
# R twin lets the new R table/figure scripts adjust series the same way the
# Python pipeline does. See analysis/docs/sesongjustering.md for the method.
#
# Method:
#   1. Take the series in logs (so the seasonal pattern is multiplicative).
#   2. Estimate the trend as a centred 2x12 moving average (13 months, half
#      weight on the two endpoints).
#   3. The factor for each calendar month is the mean log-deviation from trend
#      for that month over the estimation window, demeaned to sum to zero.
#   4. Freeze those factors and subtract them from every month.

seasonal_adjust <- function(date, value, seas_from, seas_to) {
  # date:      character vector "YYYY-MM-DD", one element per month
  # value:     numeric vector of the series (same length/order as date)
  # seas_from: first month (inclusive) of the factor-estimation window
  # seas_to:   last month (inclusive) of the factor-estimation window
  # returns:   numeric vector of the seasonally adjusted series (date order in)

  ord   <- order(date)                              # sort everything by date
  date  <- date[ord]                                # date in ascending order
  value <- as.numeric(value[ord])                   # values aligned to sorted dates

  pos  <- value > 0                                 # mask of usable (positive) months
  logv <- ifelse(pos, log(ifelse(pos, value, 1)), NA_real_)  # log; NA where value <= 0
  mon  <- as.integer(substr(date, 6, 7))            # calendar month 1..12 for each row
  inwin <- (date >= seas_from) & (date <= seas_to)  # estimation-window membership

  yw <- logv[inwin]                                 # log values inside the window
  mw <- mon[inwin]                                  # calendar month inside the window
  nw <- length(yw)                                  # number of window months

  w <- rep(1, 13)                                   # 13-term moving-average weights
  w[1] <- 0.5; w[13] <- 0.5                         # half weight on the two endpoints
  w <- w / 12                                       # normalise so the weights sum to 1

  ma <- rep(NA_real_, nw)                           # trend estimate, NA where undefined
  if (nw >= 13) {                                   # need at least one full 13-window
    for (i in 7:(nw - 6)) {                         # only months with a full window
      ma[i] <- sum(yw[(i - 6):(i + 6)] * w)         # centred 2x12 MA (NA if a month <= 0)
    }
  }

  d   <- yw - ma                                    # log-deviation from trend
  fac <- rep(0, 12)                                 # one seasonal factor per calendar month
  for (mm in 1:12) {                                # for each calendar month 1..12
    dm <- d[mw == mm]                               # its log-deviations across years
    if (any(is.finite(dm))) {                       # if at least one is defined,
      fac[mm] <- mean(dm[is.finite(dm)])            # factor = mean deviation (skip NA)
    }
  }
  fac <- fac - mean(fac)                            # demean so adjustment leaves the level

  adj <- ifelse(pos, exp(logv - fac[mon]), NA_real_)  # subtract frozen factor (in logs)
  adj                                               # adjusted series, in input (sorted) order
}
