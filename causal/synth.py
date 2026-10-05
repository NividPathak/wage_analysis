"""Synthetic control case study for log_p10_all with placebo-in-space inference.

Case selection: among treated states, the one with the largest percentage jump in its treatment
year that still leaves at least 5 pre-treatment years in the panel. Donors: never-treated states.
Predictors: pre-period averages of the outcome (three sub-windows) and of log_emp_all.
"""

from __future__ import annotations

import json
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from pysyncon import Dataprep, Synth  # noqa: E402

from causal.build_panel import PANEL_PARQUET  # noqa: E402
from causal.oews_io import REPO_ROOT  # noqa: E402
from causal.treatment import load_treatment  # noqa: E402

RESULTS = REPO_ROOT / "results"
FIG_DIR = RESULTS / "figures"
OUTCOME = "log_p10_all"
FIRST_YEAR, LAST_YEAR = 2005, 2022
MIN_PRE_YEARS = 5


def pick_case(treat: pd.DataFrame) -> pd.Series:
    """Largest treatment-year % jump among treated states with >= 5 pre-treatment years."""
    t = treat[(treat["group"] == "treated") & (treat["g"] - FIRST_YEAR >= MIN_PRE_YEARS)]
    return t.sort_values("jump_pct", ascending=False).iloc[0]


def fit_synth(panel: pd.DataFrame, treated: str, donors: list[str], g: int) -> dict:
    """Fit pysyncon Synth for one treated unit; return weights, paths, and RMSPEs."""
    pre = list(range(FIRST_YEAR, g))
    thirds = np.array_split(pre, 3)
    dp = Dataprep(
        foo=panel, predictors=["log_emp_all"], predictors_op="mean", dependent=OUTCOME,
        unit_variable="state", time_variable="year", treatment_identifier=treated,
        controls_identifier=donors, time_predictors_prior=pre, time_optimize_ssr=pre,
        special_predictors=[(OUTCOME, list(map(int, w)), "mean") for w in thirds])
    synth = Synth()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        synth.fit(dataprep=dp, optim_method="Nelder-Mead", optim_initial="equal")
    w = synth.weights(round=6)
    wide = panel.pivot(index="year", columns="state", values=OUTCOME)
    actual = wide[treated]
    synthetic = wide[w.index] @ w.values
    gap = actual - synthetic
    pre_mask = gap.index < g
    pre_rmspe = float(np.sqrt((gap[pre_mask] ** 2).mean()))
    post_rmspe = float(np.sqrt((gap[~pre_mask] ** 2).mean()))
    return {"weights": {k: float(v) for k, v in w.items() if v > 1e-4},
            "actual": actual.tolist(), "synthetic": synthetic.tolist(), "gap": gap.tolist(),
            "years": [int(y) for y in gap.index], "pre_rmspe": pre_rmspe,
            "post_rmspe": post_rmspe, "ratio": post_rmspe / pre_rmspe,
            "avg_post_gap": float(gap[~pre_mask].mean())}


def plot(case: str, g: int, main: dict, placebos: dict[str, dict]) -> tuple[str, str]:
    """Treated vs synthetic paths, and treated gap over placebo gaps."""
    years = main["years"]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(years, main["actual"], label=case, color="#1f6feb", lw=2)
    ax.plot(years, main["synthetic"], label=f"Synthetic {case}", color="#6e7781", ls="--", lw=2)
    ax.axvline(g - 0.5, color="black", lw=0.8, ls=":")
    ax.set_xticks(years[::2])
    ax.set_xlabel("Year")
    ax.set_ylabel("log 10th percentile hourly wage")
    ax.set_title(f"Synthetic control: {case} (first large increase {g})")
    ax.legend()
    fig.tight_layout()
    f1 = "synth_paths.png"
    fig.savefig(FIG_DIR / f1, dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    for res in placebos.values():
        ax.plot(years, res["gap"], color="#c9d1d9", lw=1)
    ax.plot(years, main["gap"], color="#1f6feb", lw=2.5, label=f"{case} (treated)")
    ax.plot([], [], color="#c9d1d9", label="Never-treated placebos")
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(g - 0.5, color="black", lw=0.8, ls=":")
    ax.set_xticks(years[::2])
    ax.set_xlabel("Year")
    ax.set_ylabel("Gap: actual minus synthetic")
    ax.set_title("Placebo-in-space gaps")
    ax.legend()
    fig.tight_layout()
    f2 = "synth_placebo_gaps.png"
    fig.savefig(FIG_DIR / f2, dpi=150)
    plt.close(fig)
    return f1, f2


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = pd.read_parquet(PANEL_PARQUET)
    treat = load_treatment()
    case = pick_case(treat)
    state, g = case["state"], int(case["g"])
    donors = sorted(treat.loc[treat["group"] == "never_treated", "state"])
    main_fit = fit_synth(panel, state, donors, g)
    placebos = {d: fit_synth(panel, d, [x for x in donors if x != d], g) for d in donors}
    ratios = {state: main_fit["ratio"], **{d: r["ratio"] for d, r in placebos.items()}}
    ranked = sorted(ratios, key=ratios.get, reverse=True)
    rank = ranked.index(state) + 1
    f1, f2 = plot(state, g, main_fit, placebos)
    out = {"case_state": state, "treatment_year": g, "jump_usd": float(case["jump_usd"]),
           "jump_pct": float(case["jump_pct"]), "outcome": OUTCOME, "donors": donors,
           "weights": main_fit["weights"], "pre_rmspe": main_fit["pre_rmspe"],
           "post_rmspe": main_fit["post_rmspe"], "rmspe_ratio": main_fit["ratio"],
           "avg_post_gap": main_fit["avg_post_gap"], "years": main_fit["years"],
           "actual": main_fit["actual"], "synthetic": main_fit["synthetic"],
           "gap": main_fit["gap"], "placebo_ratios": ratios, "rank": rank,
           "n_units": len(ratios), "permutation_p_value": rank / len(ratios),
           "figures": [f1, f2]}
    (RESULTS / "synth.json").write_text(json.dumps(out, indent=2))
    print(f"{state} g={g}: avg post gap {out['avg_post_gap']:.4f}, ratio {out['rmspe_ratio']:.2f},"
          f" rank {rank}/{len(ratios)}, p={out['permutation_p_value']:.3f}")
    print("weights:", out["weights"])


if __name__ == "__main__":
    main()
