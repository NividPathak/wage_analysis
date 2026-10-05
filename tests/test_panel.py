"""Structural checks on the state x year analysis panel."""

import numpy as np
import pandas as pd
import pytest

from causal.build_panel import OUTCOMES, PANEL_PARQUET


@pytest.fixture(scope="module")
def panel() -> pd.DataFrame:
    return pd.read_parquet(PANEL_PARQUET)


def test_one_row_per_state_year(panel: pd.DataFrame) -> None:
    assert not panel.duplicated(["state", "year"]).any()


def test_logs_finite_where_present(panel: pd.DataFrame) -> None:
    for col in ["log_mw", *OUTCOMES]:
        vals = panel[col].dropna()
        assert np.isfinite(vals).all(), col


def test_at_least_45_states_each_year(panel: pd.DataFrame) -> None:
    for col in OUTCOMES:
        per_year = panel.dropna(subset=[col]).groupby("year")["state"].nunique()
        assert (per_year >= 45).all(), col
        assert set(per_year.index) == set(range(2005, 2023))
