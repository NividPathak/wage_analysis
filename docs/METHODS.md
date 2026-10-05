# Methods

This file documents the causal extension's design. It is filled in phase by phase; the final
version is completed in Phase 8.

## Data limitation: OEWS three-year pooling

OEWS estimates for a given May reference year pool six semiannual survey panels collected over
three years. Year-to-year changes are therefore smoothed, and BLS cautions against treating OEWS as a
clean annual time series. For this study that has two consequences:

1. Effects are biased toward zero, because only part of each year's estimate reflects post-policy
   survey panels.
2. Timing is blurred, so an effect can appear to build up over two or three years after a policy
   change even if the true effect is immediate.

The analysis handles this by (a) reading event-study effects over several post-treatment years
rather than one, and (b) running a robustness check with the treatment lagged 1 and 2 years.

## Treatment definition (event study)

Implemented in `causal/treatment.py`; the saved table is `results/treatment_assignment.csv`.

- **Never-treated states:** the effective minimum wage equals the federal minimum ($7.25) in every
  year from 2010 to 2022.
- **Treated states:** states with a first "large" increase in 2011 or later, where large means the
  effective minimum (annual average) rises by at least $0.75 and at least 8% over the prior year.
  The treatment year g is the first such year.
- **Dropped states:** states already above the federal minimum in 2010 with no discrete large jump
  afterwards. They have no clean pre-period and are excluded from the event study and synthetic
  control (they stay in the continuous two-way fixed effects regressions, which use the full
  minimum wage variation).
