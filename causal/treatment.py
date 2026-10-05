"""Treatment assignment for the staggered event study.

- Never-treated: effective minimum equals the federal $7.25 in every year 2010-2022.
- Treated: first "large" increase in 2011 or later, where large means the effective minimum rises by
  at least $0.75 and at least 8% over the prior year. Treatment year g is that first year.
- Dropped: every other state (above the federal minimum by 2010 with no large jump afterwards).
"""

from __future__ import annotations

import pandas as pd

from causal.download_minwage import OUT_PATH as MW_PATH
from causal.oews_io import REPO_ROOT

TREATMENT_PATH = REPO_ROOT / "results" / "treatment_assignment.csv"
FEDERAL_MW = 7.25
MIN_ABS_JUMP = 0.75
MIN_PCT_JUMP = 0.08
FIRST_TREAT_YEAR = 2011


def assign_treatment(mw: pd.DataFrame) -> pd.DataFrame:
    """Return one row per state with columns state, group, g (treatment year or NA)."""
    mw = mw.sort_values(["state", "year"]).copy()
    mw["jump"] = mw.groupby("state")["effective_mw"].diff()
    mw["pct"] = mw.groupby("state")["effective_mw"].pct_change()
    mw["large"] = (mw["jump"] >= MIN_ABS_JUMP) & (mw["pct"] >= MIN_PCT_JUMP)
    rows = []
    for state, g in mw.groupby("state"):
        post2010 = g[g["year"] >= 2010]
        if (post2010["effective_mw"].round(2) == FEDERAL_MW).all():
            rows.append({"state": state, "group": "never_treated", "g": pd.NA})
            continue
        big = g[g["large"] & (g["year"] >= FIRST_TREAT_YEAR)]
        if big.empty:
            rows.append({"state": state, "group": "dropped", "g": pd.NA})
        else:
            first = big.iloc[0]
            rows.append({"state": state, "group": "treated", "g": int(first["year"]),
                         "jump_usd": round(float(first["jump"]), 4),
                         "jump_pct": round(float(first["pct"]), 4)})
    out = pd.DataFrame(rows)
    out["g"] = out["g"].astype("Int64")
    return out


def load_treatment() -> pd.DataFrame:
    """Read the saved treatment table."""
    t = pd.read_csv(TREATMENT_PATH)
    t["g"] = t["g"].astype("Int64")
    return t


def main() -> None:
    t = assign_treatment(pd.read_csv(MW_PATH))
    TREATMENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    t.to_csv(TREATMENT_PATH, index=False)
    print(t["group"].value_counts().to_string())
    print("cohorts:", t.dropna(subset=["g"]).groupby("g")["state"].apply(list).to_dict())


if __name__ == "__main__":
    main()
