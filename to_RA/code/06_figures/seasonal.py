"""
seasonal.py

Shared seasonal-adjustment helper for the figure and table scripts. This is the
exact X-11-style core used by the kiindeksen.no dashboard (dashboard/
build_release.py), so the paper and the dashboard remove seasonality the same
way. Factoring it out here removes the duplicate copies that previously lived in
plot_canaries_style_index.py and plot_canaries_style_occupations.py.

Method (see analysis/docs/sesongjustering.md):
  1. Take the series in logs (so the seasonal pattern is multiplicative).
  2. Estimate the trend as a centred 2x12 moving average (13 months, half weight
     on the two endpoints) -- a sesongfri trend that handles the COVID recovery.
  3. The factor for each calendar month is the mean log-deviation from trend for
     that month over the estimation window, demeaned to sum to zero.
  4. Freeze those factors and subtract them from every month of the series.

Usage:
    from seasonal import seasonal_adjust
    adjusted = seasonal_adjust(df_with_date_and_value, "2021-01-16", "2024-12-16")
"""

import numpy as np                       # numerical arrays for the log/MA maths
import pandas as pd                      # the helper takes and returns a DataFrame


def seasonal_adjust(s, seas_from, seas_to):
    """Remove frozen calendar-month factors from one series (on the log scale).

    Args:
        s:         DataFrame with a string 'date' column ("YYYY-MM-DD") and a
                   numeric 'value' column (one row per month, one series).
        seas_from: first month (inclusive) of the factor-estimation window.
        seas_to:   last month (inclusive) of the factor-estimation window.

    Returns:
        A copy of `s`, sorted by date, with 'value' seasonally adjusted.
    """
    s = s.sort_values("date").copy()                 # work on a date-sorted copy
    vals = s["value"].to_numpy(dtype=float)          # values as a float array
    pos = vals > 0                                    # mask of usable (positive) months
    logv = np.where(pos, np.log(np.where(pos, vals, 1.0)), np.nan)  # log; NaN where <=0
    m_all = s["date"].str[5:7].astype(int).to_numpy()  # calendar month (1-12) per row
    in_win = ((s["date"] >= seas_from)               # estimation-window mask (as array)
              & (s["date"] <= seas_to)).to_numpy()

    yw = logv[in_win]                                # log values inside the window
    mw = m_all[in_win]                               # calendar month inside the window
    nw = len(yw)                                     # number of window months

    w = np.ones(13)                                  # 13-term moving-average weights
    w[0] = w[12] = 0.5                               # half weight on the two endpoints
    w = w / 12.0                                     # normalise so the weights sum to 1

    ma = np.full(nw, np.nan)                         # trend estimate, NaN where undefined
    for i in range(6, nw - 6):                       # only months with a full 13-window
        ma[i] = (yw[i - 6:i + 7] * w).sum()         # centred 2x12 MA (NaN if a month <=0)

    d = yw - ma                                      # log-deviation from trend
    fac = np.zeros(12)                               # one seasonal factor per calendar month
    for mm in range(1, 13):                          # for each calendar month 1..12
        dm = d[mw == mm]                             # its log-deviations across years
        if np.isfinite(dm).any():                    # if at least one is defined,
            fac[mm - 1] = np.nanmean(dm)             # the factor = mean deviation (skip NaN)
    fac = fac - fac.mean()                           # demean so adjustment leaves level

    adj = np.where(pos,                              # only adjust positive months
                   np.exp(logv - fac[m_all - 1]),    # subtract frozen factor (in logs)
                   np.nan)                           # leave non-positive months as NaN
    s["value"] = adj                                 # store the adjusted series
    return s                                         # adjusted, date-sorted series
