"""Difference-in-differences: continuous TWFE elasticities and staggered event studies.

Outputs
- results/did_twfe.json: continuous log-log TWFE estimates and robustness variants (5a)
- results/did_event_study.json: TWFE and Callaway-Sant'Anna event studies, pre-trend tests,
  overall ATTs, and a binary static TWFE DiD (5b)
- results/figures/event_study_<outcome>.png
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
from causal.cs_did import cs_did  # noqa: E402
from causal.oews_io import REPO_ROOT  # noqa: E402
from causal.treatment import load_treatment  # noqa: E402

RESULTS = REPO_ROOT / "results"
FIG_DIR = RESULTS / "figures"
TWFE_OUTCOMES = ["log_p10_all", "log_median_food", "log_emp_food", "log_median_cs"]
ES_OUTCOMES = ["log_p10_all", "log_emp_food", "log_median_food", "log_median_cs"]
EVENTS = list(range(-5, 6))
LEADS = [-5, -4, -3, -2]
SEED = 42
N_BOOT = 999


def summarize(fit, term: str, spec: str, outcome: str) -> dict:
    """Pull one coefficient's estimate, SE, 95% CI, p-value, N, and cluster count."""
    tidy = fit.tidy().loc[term]
    return {"outcome": outcome, "spec": spec, "term": term,
            "estimate": float(tidy["Estimate"]), "se": float(tidy["Std. Error"]),
            "ci_low": float(tidy["2.5%"]), "ci_high": float(tidy["97.5%"]),
            "p_value": float(tidy["Pr(>|t|)"]), "n": int(fit._N),
            "n_clusters": int(fit._G[0]) if hasattr(fit, "_G") else None}


def add_lags(panel: pd.DataFrame) -> pd.DataFrame:
    """Add 1- and 2-year lags of log_mw within state."""
    panel = panel.sort_values(["state", "year"]).copy()
    for k in (1, 2):
        panel[f"log_mw_lag{k}"] = panel.groupby("state")["log_mw"].shift(k)
    return panel


def continuous_twfe(panel: pd.DataFrame) -> list[dict]:
    """y = beta * log_mw + state FE + year FE, plus robustness variants; SEs clustered by state."""
    vcov = {"CRV1": "state"}
    out = []
    for y in TWFE_OUTCOMES:
        specs = [
            ("baseline", f"{y} ~ log_mw | state + year", "log_mw"),
            ("division_x_year_fe", f"{y} ~ log_mw | state + division^year", "log_mw"),
            ("lag1", f"{y} ~ log_mw_lag1 | state + year", "log_mw_lag1"),
            ("lag2", f"{y} ~ log_mw_lag2 | state + year", "log_mw_lag2"),
        ]
        if y == "log_emp_food":
            specs.append(("control_log_emp_all", f"{y} ~ log_mw + log_emp_all | state + year",
                          "log_mw"))
        for spec, fml, term in specs:
            fit = pf.feols(fml, data=panel, vcov=vcov)
            out.append(summarize(fit, term, spec, y))
    return out


def event_sample(panel: pd.DataFrame, treat: pd.DataFrame) -> pd.DataFrame:
    """Treated and never-treated states with binned relative-time dummies (ref = -1)."""
    df = panel.merge(treat[["state", "group", "g"]], on="state")
    df = df[df["group"] != "dropped"].copy()
    df["g"] = df["g"].astype(float)
    rel = (df["year"] - df["g"]).clip(lower=EVENTS[0], upper=EVENTS[-1])
    df["rel_time"] = rel
    for e in EVENTS:
        if e == -1:
            continue
        name = f"ev_m{abs(e)}" if e < 0 else f"ev_p{e}"
        df[name] = (rel == e).astype(float)  # never-treated: NaN == e is False -> all zeros
    df["post"] = ((df["g"].notna()) & (df["year"] >= df["g"])).astype(float)
    return df


def ev_name(e: int) -> str:
    return f"ev_m{abs(e)}" if e < 0 else f"ev_p{e}"


def twfe_event_study(df: pd.DataFrame, y: str) -> dict:
    """TWFE event study with binned endpoints and the joint pre-trend Wald test."""
    terms = [ev_name(e) for e in EVENTS if e != -1]
    fit = pf.feols(f"{y} ~ {' + '.join(terms)} | state + year", data=df,
                   vcov={"CRV1": "state"})
    tidy = fit.tidy()
    coefs = [{"e": -1, "estimate": 0.0, "se": 0.0, "ci_low": 0.0, "ci_high": 0.0}]
    for e in EVENTS:
        if e == -1:
            continue
        r = tidy.loc[ev_name(e)]
        coefs.append({"e": e, "estimate": float(r["Estimate"]), "se": float(r["Std. Error"]),
                      "ci_low": float(r["2.5%"]), "ci_high": float(r["97.5%"])})
    names = list(tidy.index)
    R = np.zeros((len(LEADS), len(names)))
    for i, e in enumerate(LEADS):
        R[i, names.index(ev_name(e))] = 1.0
    wald = fit.wald_test(R=R, distribution="F")
    return {"coefficients": sorted(coefs, key=lambda c: c["e"]), "n": int(fit._N),
            "pretrend": {"test": "joint F (Wald) test that leads -5..-2 are zero, "
                                 "cluster-robust by state",
                         "statistic": float(wald["statistic"]), "p_value": float(wald["pvalue"]),
                         "df": len(LEADS)}}


def differences_cs(df: pd.DataFrame, y: str) -> dict | None:
    """Callaway-Sant'Anna via the `differences` package (event and simple aggregations)."""
    try:
        from differences import ATTgt
    except ImportError:
        return None
    d = df[["fips", "year", "g", y]].rename(columns={"g": "cohort"}).set_index(["fips", "year"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        att = ATTgt(data=d, cohort_column="cohort", base_period="universal")
        att.fit(y, control_group="never_treated", boot_iterations=N_BOOT, random_state=SEED,
                progress_bar=False)
        ev = att.aggregate("event", boot_iterations=N_BOOT, random_state=SEED)
        simple = att.aggregate("simple", boot_iterations=N_BOOT, random_state=SEED)
    ev.columns = [c[-1] for c in ev.columns]
    simple.columns = [c[-1] for c in simple.columns]
    ev = ev.loc[[e for e in EVENTS if e in ev.index]]
    z = 1.959963984540054

    def row(att: float, se: float) -> dict:
        se = 0.0 if np.isnan(se) else float(se)
        pval = float(2 * stats.norm.sf(abs(att / se))) if se > 0 else None
        return {"estimate": float(att), "se": se, "ci_low": float(att - z * se),
                "ci_high": float(att + z * se), "p_value": pval}

    coefs = [{"e": int(e), **row(r["ATT"], r["std_error"])} for e, r in ev.iterrows()]
    s = simple.iloc[0]
    return {"coefficients": coefs,
            "overall_att": row(s["ATT"], s["std_error"]),
            "note": "differences 0.3.0 ATTgt, never-treated controls, universal base period, "
                    "multiplier bootstrap (999 draws, seed 42), pointwise 95% CIs = ATT +/- 1.96 SE"}


def own_cs(df: pd.DataFrame, y: str) -> dict:
    """Reference CS implementation with a state bootstrap and the pre-trend Wald test."""
    res = cs_did(df, y, unit="state", time="year", cohort_col="g", events=EVENTS,
                 leads=LEADS, n_boot=N_BOOT, seed=SEED)
    z = 1.959963984540054
    o, se = res.overall_att, res.overall_se
    p = float(2 * stats.norm.sf(abs(o / se)))
    event = res.event.rename(columns={"att": "estimate"})
    return {"coefficients": [{k: float(v) if k != "e" else int(v) for k, v in r.items()}
                             for r in event.to_dict("records")],
            "overall_att": {"estimate": o, "se": se, "ci_low": o - z * se, "ci_high": o + z * se,
                            "p_value": p},
            "pretrend": {"test": "Wald chi-square test that CS leads -5..-2 are zero, "
                                 "state-bootstrap covariance",
                         "statistic": res.pretrend_wald, "df": res.pretrend_df,
                         "p_value": res.pretrend_p}}


def pre_covid_cs(df: pd.DataFrame, y: str, last_year: int = 2019) -> dict:
    """Robustness: CS overall ATT on years <= 2019, keeping cohorts treated by then."""
    sub = df[(df["year"] <= last_year) & ~(df["g"] > last_year)]
    res = cs_did(sub, y, unit="state", time="year", cohort_col="g", events=EVENTS,
                 leads=LEADS, n_boot=N_BOOT, seed=SEED)
    z = 1.959963984540054
    o, se = res.overall_att, res.overall_se
    return {"estimate": o, "se": se, "ci_low": o - z * se, "ci_high": o + z * se,
            "p_value": float(2 * stats.norm.sf(abs(o / se))),
            "treated_states": int(sub.loc[sub["g"].notna(), "state"].nunique()),
            "note": f"causal/cs_did.py, years <= {last_year}, cohorts g <= {last_year}"}


def binary_twfe(df: pd.DataFrame, y: str) -> dict:
    """Static binary DiD: y = beta * post + state FE + year FE (used again in the power study)."""
    fit = pf.feols(f"{y} ~ post | state + year", data=df, vcov={"CRV1": "state"})
    return summarize(fit, "post", "binary_static_twfe", y)


def plot_event_study(y: str, twfe: dict, cs: dict, label: str) -> str:
    """Overlay TWFE and CS event-study estimates with 95% CIs."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for res, name, off, color in [(twfe, "TWFE event study", -0.1, "#6e7781"),
                                  (cs, label, 0.1, "#1f6feb")]:
        c = pd.DataFrame(res["coefficients"])
        ax.errorbar(c["e"] + off, c["estimate"],
                    yerr=[c["estimate"] - c["ci_low"], c["ci_high"] - c["estimate"]],
                    fmt="o", capsize=3, label=name, color=color)
    ax.axhline(0, color="black", lw=0.8)
    ax.axvline(-0.5, color="black", lw=0.8, ls="--")
    ax.set_xlabel("Years relative to first large minimum wage increase (endpoints binned for "
                  "TWFE)")
    ax.set_ylabel(f"Effect on {y}")
    ax.set_title(f"Event study: {y}")
    ax.legend()
    fig.tight_layout()
    name = f"event_study_{y}.png"
    fig.savefig(FIG_DIR / name, dpi=150)
    plt.close(fig)
    return name


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    panel = add_lags(pd.read_parquet(PANEL_PARQUET))
    treat = load_treatment()

    twfe = continuous_twfe(panel)
    (RESULTS / "did_twfe.json").write_text(json.dumps(twfe, indent=2))

    df = event_sample(panel, treat)
    es: dict = {"sample": {"treated_states": int(df.loc[df["g"].notna(), "state"].nunique()),
                           "never_treated_states": int(df.loc[df["g"].isna(), "state"].nunique()),
                           "years": [int(df["year"].min()), int(df["year"].max())]},
                "outcomes": {}}
    for y in ES_OUTCOMES:
        tw = twfe_event_study(df, y)
        own = own_cs(df, y)
        pkg = differences_cs(df, y)
        cs_main = pkg if pkg is not None else own
        label = ("Callaway-Sant'Anna (differences)" if pkg is not None
                 else "Callaway-Sant'Anna (causal/cs_did.py)")
        entry = {"twfe_event_study": tw, "callaway_santanna": cs_main,
                 "cs_reference_implementation": own, "binary_twfe": binary_twfe(df, y),
                 "cs_pre_covid": pre_covid_cs(df, y),
                 "figure": plot_event_study(y, tw, cs_main, label)}
        if pkg is not None:
            a = {c["e"]: c["estimate"] for c in pkg["coefficients"]}
            b = {c["e"]: c["estimate"] for c in own["coefficients"]}
            entry["cs_crosscheck_max_abs_diff"] = max(abs(a[e] - b[e]) for e in a if e in b)
            entry["callaway_santanna"]["pretrend"] = own["pretrend"]
        es["outcomes"][y] = entry
        print(y, "CS overall ATT", round(cs_main["overall_att"]["estimate"], 4),
              "pretrend p (TWFE, CS):", round(tw["pretrend"]["p_value"], 3),
              round(own["pretrend"]["p_value"], 3))
    (RESULTS / "did_event_study.json").write_text(json.dumps(es, indent=2))
    for r in twfe:
        print(f"{r['outcome']:16s} {r['spec']:22s} {r['estimate']:+.4f} "
              f"({r['se']:.4f}) p={r['p_value']:.3f} N={r['n']}")


if __name__ == "__main__":
    main()
