"""Simulation power analysis for the binary staggered DiD, plus placebo-outcome falsification.

Each draw uses only never-treated states, assigns fake treatment years to a random subset (same
treated share and cohort-year distribution as the real design), adds a known effect delta to the
post-treatment outcome, and estimates y = beta * post + state FE + year FE with state-clustered SEs.

Adding delta * post to y shifts the OLS estimate by exactly delta and leaves residuals and the
clustered SE unchanged, so each draw is fit once on the raw outcome and every delta is evaluated
from that fit: reject if |beta_0 + delta| / se > t_{0.975, G-1}. This is algebraically identical to
refitting per delta.
"""

from __future__ import annotations

import json
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyfixest as pf  # noqa: E402
from scipy import stats  # noqa: E402

from causal.build_panel import PANEL_PARQUET  # noqa: E402
from causal.oews_io import REPO_ROOT  # noqa: E402
from causal.treatment import load_treatment  # noqa: E402

RESULTS = REPO_ROOT / "results"
FIG_DIR = RESULTS / "figures"
OUTCOMES = ["log_emp_food", "log_p10_all"]
DELTAS = [0.00, 0.01, 0.02, 0.03, 0.05, 0.08]
FINE_DELTAS = np.round(np.arange(0, 0.2001, 0.001), 3)
N_SIMS = 500
SEED = 42
TARGET_POWER = 0.80


def placebo_draws(panel: pd.DataFrame, never: list[str], cohort_years: np.ndarray, n_fake: int,
                  y: str, rng: np.random.Generator) -> pd.DataFrame:
    """Fit the binary DiD on N_SIMS random placebo assignments; return estimate, se, df."""
    base = panel[panel["state"].isin(never)].reset_index(drop=True)
    rows = []
    for _ in range(N_SIMS):
        fake = rng.choice(never, size=n_fake, replace=False)
        years = rng.choice(cohort_years, size=n_fake, replace=True)
        g = base["state"].map(dict(zip(fake, years)))
        df = base.assign(post=((base["year"] >= g) & g.notna()).astype(float))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = pf.feols(f"{y} ~ post | state + year", data=df, vcov={"CRV1": "state"})
        r = fit.tidy().loc["post"]
        rows.append({"estimate": float(r["Estimate"]), "se": float(r["Std. Error"]),
                     "df": int(fit._G[0]) - 1})
    return pd.DataFrame(rows)


def power_at(draws: pd.DataFrame, delta: float) -> float:
    """Share of draws rejecting beta = 0 at 5% when the true effect is delta."""
    crit = stats.t.ppf(0.975, draws["df"])
    return float((np.abs(draws["estimate"] + delta) / draws["se"] > crit).mean())


def mde(draws: pd.DataFrame) -> float | None:
    """Smallest positive delta on a 0.001 grid with power >= 80% (None if not reached by 0.2)."""
    for d in FINE_DELTAS:
        if d > 0 and power_at(draws, d) >= TARGET_POWER:
            return float(d)
    return None


def placebo_outcome_summary() -> dict:
    """Collect every estimate for the placebo outcome log_median_cs from Phase 5 outputs."""
    twfe = json.loads((RESULTS / "did_twfe.json").read_text())
    es = json.loads((RESULTS / "did_event_study.json").read_text())["outcomes"]["log_median_cs"]
    rows = [{"method": f"continuous TWFE ({r['spec']})", "estimate": r["estimate"],
             "ci_low": r["ci_low"], "ci_high": r["ci_high"], "p_value": r["p_value"]}
            for r in twfe if r["outcome"] == "log_median_cs"]
    cs = es["callaway_santanna"]["overall_att"]
    rows.append({"method": "Callaway-Sant'Anna overall ATT", **{k: cs[k] for k in
                 ("estimate", "ci_low", "ci_high", "p_value")}})
    b = es["binary_twfe"]
    rows.append({"method": "binary static TWFE", **{k: b[k] for k in
                 ("estimate", "ci_low", "ci_high", "p_value")}})
    pc = es["cs_pre_covid"]
    rows.append({"method": "Callaway-Sant'Anna overall ATT, pre-COVID", **{k: pc[k] for k in
                 ("estimate", "ci_low", "ci_high", "p_value")}})
    n_sig = sum(r["p_value"] < 0.05 for r in rows)
    return {"outcome": "log_median_cs", "estimates": rows, "n_significant_at_5pct": n_sig,
            "n_estimates": len(rows),
            "event_study_pretrend_p_twfe": es["twfe_event_study"]["pretrend"]["p_value"],
            "event_study_pretrend_p_cs": es["callaway_santanna"]["pretrend"]["p_value"]}


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(PANEL_PARQUET)
    treat = load_treatment()
    never = sorted(treat.loc[treat["group"] == "never_treated", "state"])
    treated = treat[treat["group"] == "treated"]
    share = len(treated) / (len(treated) + len(never))
    n_fake = int(round(share * len(never)))
    cohort_years = treated["g"].astype(int).to_numpy()
    rng = np.random.default_rng(SEED)

    out: dict = {"design": {"n_never_treated": len(never), "n_real_treated": len(treated),
                            "treated_share": share, "n_fake_treated_per_draw": n_fake,
                            "n_sims": N_SIMS, "seed": SEED,
                            "estimator": "binary static TWFE, state + year FE, CRV1 by state",
                            "cohort_years_sampled_from": sorted(cohort_years.tolist())},
                 "outcomes": {}}
    fig, ax = plt.subplots(figsize=(8, 5))
    for y in OUTCOMES:
        draws = placebo_draws(panel, never, cohort_years, n_fake, y, rng)
        grid = {f"{d:.2f}": power_at(draws, d) for d in DELTAS}
        out["outcomes"][y] = {"power_by_delta": grid, "false_positive_rate": grid["0.00"],
                              "mde_80": mde(draws),
                              "placebo_estimate_sd": float(draws["estimate"].std(ddof=1)),
                              "mean_se": float(draws["se"].mean())}
        ax.plot(FINE_DELTAS, [power_at(draws, d) for d in FINE_DELTAS], label=y)
        ax.scatter(DELTAS, list(grid.values()))
        print(y, out["outcomes"][y])
    ax.axhline(TARGET_POWER, color="black", lw=0.8, ls="--", label="80% power")
    ax.axhline(0.05, color="grey", lw=0.8, ls=":", label="5% nominal size")
    ax.set_xlabel("True effect delta (log points)")
    ax.set_ylabel("Share of simulations with p < 0.05")
    ax.set_title("Simulated power of the staggered binary DiD (never-treated placebo draws)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / "power_curves.png", dpi=150)
    plt.close(fig)
    out["placebo_outcome"] = placebo_outcome_summary()
    out["figure"] = "power_curves.png"
    (RESULTS / "power.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out["placebo_outcome"], indent=1))


if __name__ == "__main__":
    main()
