"""Generate RESULTS.md from results/*.json. Every number in the file is inserted by this code."""

from __future__ import annotations

import json
import math

from causal.geo import POSTAL_TO_DIVISION
from causal.oews_io import REPO_ROOT

RESULTS = REPO_ROOT / "results"
OUT = REPO_ROOT / "RESULTS.md"
LABELS = {
    "log_p10_all": "10th pct hourly wage, all occupations",
    "log_median_food": "Median hourly wage, food prep and serving",
    "log_emp_food": "Employment, food prep and serving",
    "log_median_cs": "Median hourly wage, computer and math (placebo)",
}


def f3(x: float) -> str:
    return f"{x:.3f}"


def fp(p: float | None) -> str:
    if p is None:
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def pct(x: float) -> str:
    """Log points to an approximate percent change."""
    return f"{100 * (math.exp(x) - 1):.1f}%"


def load() -> tuple[list, dict, dict, dict]:
    twfe = json.loads((RESULTS / "did_twfe.json").read_text())
    es = json.loads((RESULTS / "did_event_study.json").read_text())
    synth = json.loads((RESULTS / "synth.json").read_text())
    power = json.loads((RESULTS / "power.json").read_text())
    return twfe, es, synth, power


def twfe_row(twfe: list, outcome: str, spec: str = "baseline") -> dict:
    return next(r for r in twfe if r["outcome"] == outcome and r["spec"] == spec)


def headline_rows(twfe: list, es: dict, synth: dict) -> list[dict]:
    """Rows of the headline table: (outcome, method, estimate, ci, p, n)."""
    rows = []
    for y in LABELS:
        t = twfe_row(twfe, y)
        rows.append({"outcome": y, "method": "Continuous TWFE elasticity (log MW)",
                     "estimate": t["estimate"], "ci_low": t["ci_low"], "ci_high": t["ci_high"],
                     "p_value": t["p_value"], "n": t["n"]})
        o = es["outcomes"][y]
        cs = o["callaway_santanna"]["overall_att"]
        rows.append({"outcome": y, "method": "Callaway-Sant'Anna overall ATT",
                     "estimate": cs["estimate"], "ci_low": cs["ci_low"],
                     "ci_high": cs["ci_high"], "p_value": cs["p_value"],
                     "n": o["twfe_event_study"]["n"]})
    rows.append({"outcome": "log_p10_all", "method": f"Synthetic control, {synth['case_state']} "
                 "average post-period gap", "estimate": synth["avg_post_gap"], "ci_low": None,
                 "ci_high": None, "p_value": synth["permutation_p_value"],
                 "n": len(synth["years"])})
    return rows


def table(rows: list[dict]) -> list[str]:
    lines = ["| outcome | method | estimate | 95% CI | p-value | N |", "|---|---|---|---|---|---|"]
    for r in rows:
        ci = (f"[{f3(r['ci_low'])}, {f3(r['ci_high'])}]" if r["ci_low"] is not None
              else "permutation test")
        lines.append(f"| {r['outcome']} | {r['method']} | {f3(r['estimate'])} | {ci} | "
                     f"{fp(r['p_value'])} | {r['n']} |")
    return lines


def five_numbers(twfe: list, es: dict, synth: dict, power: dict) -> list[tuple[str, str]]:
    """The five headline numbers quoted in the README and the final checklist."""
    p10 = es["outcomes"]["log_p10_all"]["callaway_santanna"]["overall_att"]
    emp = es["outcomes"]["log_emp_food"]["callaway_santanna"]["overall_att"]
    emp_pc = es["outcomes"]["log_emp_food"]["cs_pre_covid"]
    el = twfe_row(twfe, "log_p10_all")
    return [
        ("10th percentile wage, CS overall ATT",
         f"{f3(p10['estimate'])} log points (about {pct(p10['estimate'])}), "
         f"95% CI [{f3(p10['ci_low'])}, {f3(p10['ci_high'])}], p {fp(p10['p_value'])}"),
        ("10th percentile wage elasticity to the minimum wage (TWFE)",
         f"{f3(el['estimate'])}, 95% CI [{f3(el['ci_low'])}, {f3(el['ci_high'])}]"),
        ("Food-service employment, CS overall ATT (2005-2022)",
         f"{f3(emp['estimate'])}, 95% CI [{f3(emp['ci_low'])}, {f3(emp['ci_high'])}], "
         f"p {fp(emp['p_value'])}; pre-COVID (through 2019): {f3(emp_pc['estimate'])}, "
         f"p {fp(emp_pc['p_value'])}"),
        (f"Synthetic control, {synth['case_state']} {synth['treatment_year']}",
         f"average post gap {f3(synth['avg_post_gap'])} log points, permutation p "
         f"{fp(synth['permutation_p_value'])} (rank {synth['rank']} of {synth['n_units']})"),
        ("Minimum detectable effect at 80% power, food-service employment",
         f"{f3(power['outcomes']['log_emp_food']['mde_80'])} log points"),
    ]


def summary(twfe: list, es: dict, synth: dict, power: dict) -> str:
    """Plain-English summary whose wording depends on the numbers."""
    o = es["outcomes"]
    p10 = o["log_p10_all"]["callaway_santanna"]
    emp = o["log_emp_food"]["callaway_santanna"]["overall_att"]
    emp_pc = o["log_emp_food"]["cs_pre_covid"]
    cs_pl = o["log_median_cs"]["callaway_santanna"]["overall_att"]
    pl = power["placebo_outcome"]
    el = twfe_row(twfe, "log_p10_all")
    s = []
    s.append(f"States that made a large minimum wage increase saw their 10th percentile hourly "
             f"wage rise by about {pct(p10['overall_att']['estimate'])} relative to states that "
             f"stayed at $7.25 (Callaway-Sant'Anna ATT {f3(p10['overall_att']['estimate'])}, "
             f"p {fp(p10['overall_att']['p_value'])}), and the continuous estimate implies a "
             f"10% higher minimum wage goes with a {10 * el['estimate']:.1f}% higher 10th "
             f"percentile wage.")
    pt = p10["pretrend"]["p_value"]
    max_lead = max(abs(c["estimate"]) for c in p10["coefficients"] if c["e"] < -1)
    synth_agrees = synth["avg_post_gap"] > 0 and synth["permutation_p_value"] < 0.1
    if pt < 0.05:
        extra = []
        if max_lead < 0.25 * p10["overall_att"]["estimate"]:
            extra.append(f"the largest lead ({f3(max_lead)}) is small next to the overall "
                         f"effect")
        if synth_agrees:
            extra.append(f"the synthetic control for {synth['case_state']} (permutation p "
                         f"{fp(synth['permutation_p_value'])}) points the same way")
        tail = (", although " + " and ".join(extra)) if extra else ""
        s.append(f"The pre-trend test rejects parallel trends for this outcome (p {fp(pt)}), so "
                 f"the size of the wage effect should be treated as approximate{tail}.")
    else:
        s.append(f"The pre-trend test does not reject parallel trends (p {fp(pt)}).")
    emp_sig = emp["p_value"] < 0.05
    pc_sig = emp_pc["p_value"] < 0.05
    if emp_sig and not pc_sig:
        s.append(f"Food-service employment changes by {f3(emp['estimate'])} log points over the "
                 f"full 2005-2022 window (p {fp(emp['p_value'])}), but the estimate is "
                 f"{f3(emp_pc['estimate'])} (p {fp(emp_pc['p_value'])}) when the sample ends in "
                 f"2019, so the full-sample result depends on the 2020-2022 data, when pandemic "
                 f"restrictions hit food service unevenly across states, and is not robust "
                 f"evidence that the minimum wage changed food-service employment.")
    elif emp_sig and pc_sig:
        s.append(f"Food-service employment changes by {f3(emp['estimate'])} log points "
                 f"(p {fp(emp['p_value'])}), and the decline survives ending the sample in 2019 "
                 f"({f3(emp_pc['estimate'])}, p {fp(emp_pc['p_value'])}).")
    else:
        s.append(f"There is no statistically significant change in food-service employment "
                 f"({f3(emp['estimate'])}, p {fp(emp['p_value'])}).")
    s.append(f"The design only has 80% power for food employment effects of about "
             f"{f3(power['outcomes']['log_emp_food']['mde_80'])} log points or larger, so smaller "
             f"job losses or gains cannot be ruled out.")
    sig = [r for r in pl["estimates"] if r["p_value"] < 0.05]
    if not sig:
        s.append(f"The placebo outcome (computer and math wages) shows no significant effect in "
                 f"any of the {pl['n_estimates']} specifications (CS ATT {f3(cs_pl['estimate'])},"
                 f" p {fp(cs_pl['p_value'])}).")
    else:
        only_twfe = all(r["method"].startswith("continuous TWFE") for r in sig)
        div = next(r for r in pl["estimates"] if "division_x_year" in r["method"])
        where = ("all from the continuous TWFE" if only_twfe else "including event-study designs")
        tail = ""
        if only_twfe and div["p_value"] >= 0.05:
            tail = (f"; the effect disappears with division-by-year fixed effects (p "
                    f"{fp(div['p_value'])}), which suggests the baseline TWFE partly picks up "
                    f"regional wage growth")
        s.append(f"The placebo outcome (computer and math wages) shows no effect in the CS "
                 f"design (ATT {f3(cs_pl['estimate'])}, p {fp(cs_pl['p_value'])}), but "
                 f"{len(sig)} of {pl['n_estimates']} placebo estimates are significant at 5%, "
                 f"{where}{tail}.")
    return " ".join(s)


def observational_note(es: dict, synth: dict) -> str:
    """Limitation text with the regional mix of controls and the failed pre-trend tests."""
    south = {"South Atlantic", "East South Central", "West South Central"}
    n_south = sum(POSTAL_TO_DIVISION[d] in south for d in synth["donors"])
    failed = [y for y, v in es["outcomes"].items()
              if v["callaway_santanna"]["pretrend"]["p_value"] < 0.05]
    pre = (f"the CS pre-trend test rejects for {', '.join(failed)}" if failed
           else "no CS pre-trend test rejects")
    return (f"- **Observational design.** States chose to raise their minimums. {n_south} of the "
            f"{len(synth['donors'])} never-treated states are in the Census South, and {pre}, so "
            f"the estimates rely on assumptions that are only partly testable.")


def main() -> None:
    twfe, es, synth, power = load()
    o = es["outcomes"]
    L = ["# Results: state minimum wage increases, 2011-2022", "",
         "_Generated by `python -m causal.report` from `results/*.json`. Do not edit by hand._", "",
         "## Question", "",
         "Did state minimum wage increases from 2011 to 2022 raise low-end wages, and did they "
         "reduce employment in food service jobs?", "",
         "## Data and design", "",
         f"State x year panel, 2005-2022, built from BLS OEWS state estimates and the Vaghul and "
         f"Zipperer (2022) minimum wage series. The event study compares "
         f"{es['sample']['treated_states']} states with a first large increase (at least $0.75 "
         f"and 8%) in 2011 or later against {es['sample']['never_treated_states']} states that "
         f"stayed at the federal $7.25. Estimators: continuous two-way fixed effects, a TWFE "
         f"event study, Callaway and Sant'Anna (2021), and a synthetic control case study. Full "
         f"details in [docs/METHODS.md](docs/METHODS.md); every judgment call is in "
         f"[docs/DECISIONS.md](docs/DECISIONS.md).", "",
         "## Five headline numbers", ""]
    L += [f"{i}. **{k}:** {v}" for i, (k, v) in
          enumerate(five_numbers(twfe, es, synth, power), 1)]
    L += ["", "## Headline table", "",
          "Estimates are in log points. TWFE rows are elasticities with respect to the log "
          "effective minimum wage (all 51 units); CS rows are average effects of a large "
          "increase (46 units). Standard errors are clustered by state (TWFE) or bootstrapped "
          "over states (CS).", ""]
    L += table(headline_rows(twfe, es, synth))
    L += ["", "## Robustness (continuous TWFE)", "",
          "| outcome | specification | estimate | 95% CI | p-value | N |",
          "|---|---|---|---|---|---|"]
    for r in twfe:
        L.append(f"| {r['outcome']} | {r['spec']} | {f3(r['estimate'])} | "
                 f"[{f3(r['ci_low'])}, {f3(r['ci_high'])}] | {fp(r['p_value'])} | {r['n']} |")
    L += ["", "## Robustness (event-study designs)", "",
          "| outcome | binary static TWFE | CS overall ATT | CS pre-COVID (through 2019) |",
          "|---|---|---|---|"]
    for y in LABELS:
        b, c, pc = (o[y]["binary_twfe"], o[y]["callaway_santanna"]["overall_att"],
                    o[y]["cs_pre_covid"])
        L.append(f"| {y} | {f3(b['estimate'])} (p {fp(b['p_value'])}) | {f3(c['estimate'])} "
                 f"(p {fp(c['p_value'])}) | {f3(pc['estimate'])} (p {fp(pc['p_value'])}) |")
    L += ["", "## Event studies", "",
          "Grey: TWFE event study (endpoints binned). Blue: Callaway and Sant'Anna. Event time 0 "
          "is the first year of the large increase; -1 is the reference year.", ""]
    for y in LABELS:
        L += [f"### {LABELS[y]} (`{y}`)", "", f"![{y}](results/figures/{o[y]['figure']})", ""]
    L += ["## Pre-trend tests", "",
          "Joint test that the event-study leads -5 to -2 are zero.", "",
          "| outcome | TWFE Wald chi-square | TWFE p-value | CS Wald chi-square | CS p-value |",
          "|---|---|---|---|---|"]
    for y in LABELS:
        tw, cs = o[y]["twfe_event_study"]["pretrend"], o[y]["callaway_santanna"]["pretrend"]
        L.append(f"| {y} | {f3(tw['statistic'])} | {fp(tw['p_value'])} | "
                 f"{f3(cs['statistic'])} | {fp(cs['p_value'])} |")
    w = ", ".join(f"{k} {v:.3f}" for k, v in
                  sorted(synth["weights"].items(), key=lambda kv: -kv[1]) if v >= 0.01)
    L += ["", "## Synthetic control", "",
          f"Case: **{synth['case_state']}**, first large increase in {synth['treatment_year']} "
          f"(+${synth['jump_usd']:.2f}, {100 * synth['jump_pct']:.1f}%). Outcome: `log_p10_all`."
          f" Donor weights of at least 0.01: {w}.", "",
          f"- Pre-period RMSPE: {synth['pre_rmspe']:.4f}",
          f"- Post-period RMSPE: {synth['post_rmspe']:.4f}",
          f"- Post/pre RMSPE ratio: {synth['rmspe_ratio']:.2f}, rank {synth['rank']} of "
          f"{synth['n_units']} units",
          f"- Permutation p-value: {fp(synth['permutation_p_value'])} (the smallest possible "
          f"value with {synth['n_units']} units is {fp(1 / synth['n_units'])})",
          f"- Average post-period gap: {f3(synth['avg_post_gap'])} log points", "",
          "![synthetic control](results/figures/synth_paths.png)", "",
          "![placebo gaps](results/figures/synth_placebo_gaps.png)", "",
          "## Power", ""]
    d = power["design"]
    L += [f"{d['n_sims']} placebo draws on the {d['n_never_treated']} never-treated states "
          f"({d['n_fake_treated_per_draw']} given fake treatment per draw), binary static TWFE, "
          f"seed {d['seed']}.", "",
          "| outcome | false positive rate (delta = 0) | MDE at 80% power |", "|---|---|---|"]
    for y, r in power["outcomes"].items():
        L.append(f"| {y} | {r['false_positive_rate']:.3f} | {f3(r['mde_80'])} |")
    L += ["", "![power curves](results/figures/power_curves.png)", "",
          "## Placebo outcome", "",
          "Computer and math median wages should not respond to the minimum wage.", "",
          "| method | estimate | 95% CI | p-value |", "|---|---|---|---|"]
    for r in power["placebo_outcome"]["estimates"]:
        L.append(f"| {r['method']} | {f3(r['estimate'])} | [{f3(r['ci_low'])}, "
                 f"{f3(r['ci_high'])}] | {fp(r['p_value'])} |")
    L += ["", "## Limitations", "",
          "- **OEWS three-year pooling.** Each OEWS estimate pools six semiannual panels over "
          "three years, which smooths changes, biases effects toward zero, and spreads them over "
          "several years.",
          "- **State-level aggregation.** Effects are averaged over whole states; local minimum "
          "wages (for example in cities) and within-state heterogeneity are not modeled.",
          "- **SOC changes.** Occupation codes were revised in 2010 and 2018. Major groups "
          "(00-0000, 35-0000, 15-0000) are used because they are stable, but composition within "
          "them can shift.",
          "- **Minimum wage data ends in 2022**, so the panel stops in 2022 and the latest "
          "cohorts have only one or two post-treatment years.",
          "- **COVID-19.** 2020-2022 food-service employment moved with state-specific "
          "pandemic restrictions, which overlap with the later event times of the early cohorts.",
          observational_note(es, synth),
          "", "## Plain-English summary", "", summary(twfe, es, synth, power), ""]
    OUT.write_text("\n".join(L))
    print(f"wrote {OUT}")
    for k, v in five_numbers(twfe, es, synth, power):
        print(f"- {k}: {v}")


if __name__ == "__main__":
    main()
