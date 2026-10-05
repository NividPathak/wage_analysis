"""Streamlit page: causal analysis of state minimum wage increases (solo extension).

Reads only the saved outputs in results/, so it never re-runs the analysis.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from causal.report import LABELS, five_numbers, fp, headline_rows, load  # noqa: E402

FIGS = ROOT / "results" / "figures"

st.set_page_config(page_title="Causal Analysis | Minimum Wage", layout="wide")
st.title("Did state minimum wage increases raise low-end wages and cut food-service jobs?")
st.caption("Solo extension by Nivid Pathak of the Group 7 project. Full write-up: RESULTS.md and "
           "docs/METHODS.md in the repository.")

twfe, es, synth, power = load()

st.header("Headline numbers")
for key, value in five_numbers(twfe, es, synth, power):
    st.markdown(f"- **{key}:** {value}")

st.header("Headline table")
rows = headline_rows(twfe, es, synth)
table = pd.DataFrame([{
    "Outcome": LABELS.get(r["outcome"], r["outcome"]), "Method": r["method"],
    "Estimate": round(r["estimate"], 3),
    "95% CI": (f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]" if r["ci_low"] is not None
               else "permutation test"),
    "p-value": fp(r["p_value"]), "N": r["n"]} for r in rows])
st.dataframe(table, hide_index=True, width="stretch")

st.header("Event studies")
outcome = st.selectbox("Outcome", list(LABELS), format_func=lambda k: LABELS[k])
o = es["outcomes"][outcome]
st.image(str(FIGS / o["figure"]))
c1, c2 = st.columns(2)
c1.metric("Pre-trend p-value (TWFE)", fp(o["twfe_event_study"]["pretrend"]["p_value"]))
c2.metric("Pre-trend p-value (Callaway-Sant'Anna)",
          fp(o["callaway_santanna"]["pretrend"]["p_value"]))

st.header(f"Synthetic control: {synth['case_state']} ({synth['treatment_year']})")
c1, c2 = st.columns(2)
c1.image(str(FIGS / "synth_paths.png"))
c2.image(str(FIGS / "synth_placebo_gaps.png"))
st.markdown(f"Permutation p-value **{fp(synth['permutation_p_value'])}** (rank "
            f"{synth['rank']} of {synth['n_units']}). Donor weights: "
            + ", ".join(f"{k} {v:.2f}" for k, v in sorted(synth["weights"].items(),
                                                       key=lambda kv: -kv[1]) if v >= 0.01))

st.header("Power")
st.image(str(FIGS / "power_curves.png"))
st.dataframe(pd.DataFrame({y: {"False positive rate": r["false_positive_rate"],
                               "MDE at 80% power": r["mde_80"]}
                           for y, r in power["outcomes"].items()}).T,
             width="stretch")

with st.expander("Raw results JSON"):
    st.json(json.loads((ROOT / "results" / "did_event_study.json").read_text())["sample"])
