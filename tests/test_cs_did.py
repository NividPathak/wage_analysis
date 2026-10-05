"""The CS estimator recovers a known effect on simulated data."""

import numpy as np

from causal.cs_did import cs_did, simulate_panel


def test_recovers_known_effect() -> None:
    df = simulate_panel(effect=0.10, seed=1)
    res = cs_did(df, "y", n_boot=199, seed=42)
    assert abs(res.overall_att - 0.10) < 0.03
    post = res.event[res.event["e"] >= 0]["att"].dropna()
    assert np.all(np.abs(post - 0.10) < 0.03)


def test_no_effect_no_pretrend() -> None:
    df = simulate_panel(effect=0.0, seed=2)
    res = cs_did(df, "y", n_boot=199, seed=42)
    assert abs(res.overall_att) < 0.03
    leads = res.event[res.event["e"] < -1]["att"]
    assert np.all(np.abs(leads) < 0.03)
