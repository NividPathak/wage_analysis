"""Callaway and Sant'Anna (2021) DiD with never-treated controls, no covariates.

For cohort g and period t, ATT(g, t) is the 2x2 DiD of the mean change in y between t and g - 1
(universal base period) for cohort g versus never-treated units. Event-time effects average
ATT(g, g + e) across cohorts with cohort-size weights. Standard errors come from a bootstrap that
resamples units (states) with replacement. This is the transparent reference implementation used for
the pre-trend Wald test and as a cross-check on the ``differences`` package.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class CSResult:
    """Point estimates, bootstrap draws, and summaries for one outcome."""

    event: pd.DataFrame  # columns: e, att, se, ci_low, ci_high
    overall_att: float
    overall_se: float
    pretrend_wald: float
    pretrend_df: int
    pretrend_p: float


def _wide(df: pd.DataFrame, y: str, unit: str, time: str) -> tuple[np.ndarray, list, list]:
    w = df.pivot(index=unit, columns=time, values=y).sort_index()
    if w.isna().any().any():
        raise ValueError("cs_did requires a balanced panel with no missing outcomes")
    return w.to_numpy(), list(w.index), list(w.columns)


def _estimate(Y: np.ndarray, cohort: np.ndarray, w: np.ndarray, years: list,
              events: list[int]) -> tuple[np.ndarray, float]:
    """Return (event-time ATTs, simple overall ATT) for unit weights w (bootstrap counts)."""
    never = np.isnan(cohort)
    wn = w * never
    t_index = {yr: i for i, yr in enumerate(years)}
    att_e_num = np.zeros(len(events))
    att_e_den = np.zeros(len(events))
    overall_num = overall_den = 0.0
    for g in np.unique(cohort[~never]):
        base = t_index.get(int(g) - 1)
        if base is None:
            continue
        in_g = (cohort == g) * w
        n_g = in_g.sum()
        if n_g == 0 or wn.sum() == 0:
            continue
        D = Y - Y[:, [base]]
        att_gt = (in_g @ D) / n_g - (wn @ D) / wn.sum()
        for k, e in enumerate(events):
            ti = t_index.get(int(g) + e)
            if ti is not None:
                att_e_num[k] += n_g * att_gt[ti]
                att_e_den[k] += n_g
        post = [t_index[yr] for yr in years if yr >= g]
        overall_num += n_g * att_gt[post].sum()
        overall_den += n_g * len(post)
    with np.errstate(invalid="ignore", divide="ignore"):
        att_e = att_e_num / att_e_den
    return att_e, overall_num / overall_den


def cs_did(df: pd.DataFrame, y: str, unit: str = "state", time: str = "year",
           cohort_col: str = "g", events: range = range(-5, 6), leads: range = range(-5, -1),
           n_boot: int = 999, seed: int = 42) -> CSResult:
    """Estimate CS event-time effects and overall ATT with a unit bootstrap.

    ``df`` holds treated and never-treated units only; never-treated have NaN in ``cohort_col``.
    """
    Y, units, years = _wide(df, y, unit, time)
    cohort = (df.drop_duplicates(unit).set_index(unit).loc[units, cohort_col]
              .astype(float).to_numpy())
    events = list(events)
    att_e, overall = _estimate(Y, cohort, np.ones(len(units)), years, events)

    rng = np.random.default_rng(seed)
    draws_e = np.empty((n_boot, len(events)))
    draws_o = np.empty(n_boot)
    for b in range(n_boot):
        counts = np.bincount(rng.integers(0, len(units), len(units)), minlength=len(units))
        draws_e[b], draws_o[b] = _estimate(Y, cohort, counts.astype(float), years, events)

    se_e = np.nanstd(draws_e, axis=0, ddof=1)
    z = stats.norm.ppf(0.975)
    event = pd.DataFrame({"e": events, "att": att_e, "se": se_e,
                          "ci_low": att_e - z * se_e, "ci_high": att_e + z * se_e})
    event.loc[event["e"] == -1, ["se", "ci_low", "ci_high"]] = 0.0

    lead_idx = [events.index(e) for e in leads]
    b_lead = att_e[lead_idx]
    lead_draws = draws_e[:, lead_idx]
    lead_draws = lead_draws[~np.isnan(lead_draws).any(axis=1)]
    V = np.cov(lead_draws, rowvar=False)
    wald = float(b_lead @ np.linalg.solve(V, b_lead))
    return CSResult(event=event, overall_att=float(overall),
                    overall_se=float(np.std(draws_o, ddof=1)), pretrend_wald=wald,
                    pretrend_df=len(leads), pretrend_p=float(stats.chi2.sf(wald, len(leads))))


def simulate_panel(n_units: int = 60, years: range = range(2005, 2023), effect: float = 0.10,
                   seed: int = 0) -> pd.DataFrame:
    """Simulated staggered panel with unit and year effects and a constant treatment effect."""
    rng = np.random.default_rng(seed)
    yrs = list(years)
    cohorts = rng.choice([2012, 2015, 2018, np.nan], size=n_units, p=[0.2, 0.2, 0.2, 0.4])
    alpha = rng.normal(0, 1, n_units)
    gamma = {yr: 0.02 * (yr - yrs[0]) + rng.normal(0, 0.05) for yr in yrs}
    rows = []
    for i in range(n_units):
        for yr in yrs:
            treated = not np.isnan(cohorts[i]) and yr >= cohorts[i]
            y = alpha[i] + gamma[yr] + effect * treated + rng.normal(0, 0.02)
            rows.append({"state": f"S{i}", "year": yr, "g": cohorts[i], "y": y})
    return pd.DataFrame(rows)
