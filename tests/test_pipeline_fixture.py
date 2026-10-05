"""Run the estimators end to end on a small committed fixture panel (no raw downloads needed)."""

from pathlib import Path

import pandas as pd
import pytest

from causal.cs_did import cs_did
from causal.did import LEADS, add_lags, binary_twfe, continuous_twfe, event_sample, twfe_event_study

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def fixture_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    panel = pd.read_csv(FIX / "panel_fixture.csv")
    treat = pd.read_csv(FIX / "treatment_fixture.csv")
    treat["g"] = treat["g"].astype("Int64")
    return add_lags(panel), treat


def test_continuous_twfe_runs(fixture_data) -> None:
    panel, _ = fixture_data
    rows = continuous_twfe(panel)
    base = [r for r in rows if r["spec"] == "baseline"]
    assert len(base) == 4
    for r in rows:
        assert r["ci_low"] <= r["estimate"] <= r["ci_high"]
        assert 0 <= r["p_value"] <= 1


def test_event_study_and_cs_run(fixture_data) -> None:
    panel, treat = fixture_data
    df = event_sample(panel, treat)
    assert set(df["group"]) <= {"treated", "never_treated"}
    tw = twfe_event_study(df, "log_p10_all")
    assert {c["e"] for c in tw["coefficients"]} == set(range(-5, 6))
    assert 0 <= tw["pretrend"]["p_value"] <= 1 and tw["pretrend"]["df"] == len(LEADS)
    res = cs_did(df, "log_p10_all", n_boot=49, seed=42)
    assert res.event.loc[res.event["e"] == -1, "att"].iloc[0] == 0
    assert binary_twfe(df, "log_p10_all")["n"] == len(df)
