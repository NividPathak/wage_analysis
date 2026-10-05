"""Sanity checks on the state minimum wage panel."""

import pandas as pd
import pytest

from causal.download_minwage import OUT_PATH


@pytest.fixture(scope="module")
def mw() -> pd.DataFrame:
    return pd.read_csv(OUT_PATH)


def test_federal_minimum_2010_2022(mw: pd.DataFrame) -> None:
    fed = mw.loc[mw["year"].between(2010, 2022), "federal_mw"]
    assert (fed.round(2) == 7.25).all()


def test_effective_not_below_federal(mw: pd.DataFrame) -> None:
    assert (mw["effective_mw"] >= mw["federal_mw"] - 1e-9).all()


def test_shape_and_uniqueness(mw: pd.DataFrame) -> None:
    assert len(mw) == 51 * 18
    assert mw["state"].nunique() == 51
    assert not mw.duplicated(["state", "year"]).any()
