"""Load the raw BLS OEWS state files with the team's column alias map.

The alias map is copied from the team's ``notebooks/Data_cleaning.ipynb`` so column names line up
across the 2005-2024 file layouts (for example ``GROUP`` / ``OCC_GROUP`` / ``O_GROUP``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "data"
EXTERNAL_OEWS_DIR = REPO_ROOT / "data_external" / "oews"

# Copied from notebooks/Data_cleaning.ipynb (team code), extended with A_MEDIAN and area type.
COLUMN_ALIAS: dict[str, list[str]] = {
    "AREA": ["AREA"],
    "ST": ["ST", "PRIM_STATE"],
    "STATE": ["STATE", "AREA_TITLE", "area_title"],
    "AREA_TYPE": ["AREA_TYPE", "area_type"],
    "OCC_CODE": ["OCC_CODE", "occ_code"],
    "OCC_TITLE": ["OCC_TITLE", "occ_title"],
    "GROUP": ["GROUP", "OCC_GROUP", "o_group", "O_GROUP"],
    "TOT_EMP": ["TOT_EMP", "tot_emp"],
    "EMP_PRSE": ["EMP_PRSE", "emp_prse"],
    "MEAN_PRSE": ["MEAN_PRSE", "mean_prse"],
    "H_MEAN": ["H_MEAN", "h_mean"],
    "H_PCT10": ["H_PCT10", "h_pct10"],
    "H_PCT25": ["H_PCT25", "h_pct25"],
    "H_MEDIAN": ["H_MEDIAN", "h_median"],
    "H_PCT75": ["H_PCT75", "h_pct75"],
    "H_PCT90": ["H_PCT90", "h_pct90"],
    "A_MEAN": ["A_MEAN", "a_mean"],
    "A_PCT10": ["A_PCT10", "a_pct10"],
    "A_PCT25": ["A_PCT25", "a_pct25"],
    "A_MEDIAN": ["A_MEDIAN", "a_median"],
    "A_PCT75": ["A_PCT75", "a_pct75"],
    "A_PCT90": ["A_PCT90", "a_pct90"],
}
ALIAS_TO_KEY: dict[str, str] = {
    a.strip().lower(): key for key, aliases in COLUMN_ALIAS.items() for a in aliases
}
NUMERIC_COLS = [
    "TOT_EMP", "H_MEAN", "H_PCT10", "H_MEDIAN", "A_MEAN", "A_PCT10", "A_MEDIAN",
]
SUPPRESSION_MARKERS = ["*", "**", "#"]


def raw_state_files() -> dict[int, Path]:
    """Return {year: path} for every raw OEWS state workbook (repo data/ first, then downloads)."""
    files: dict[int, Path] = {}
    for base in (EXTERNAL_OEWS_DIR, RAW_DIR):
        for p in sorted(base.rglob("*.xls*")):
            m = re.search(r"oesm(\d{2})st", str(p))
            if m and "field" not in p.name.lower():
                files[2000 + int(m.group(1))] = p
    return dict(sorted(files.items()))


def harmonize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename year-specific column names to the canonical keys and keep only those."""
    rename = {c: ALIAS_TO_KEY[str(c).strip().lower()] for c in df.columns
              if str(c).strip().lower() in ALIAS_TO_KEY}
    out = df.rename(columns=rename)
    return out[[k for k in COLUMN_ALIAS if k in out.columns]]


def load_raw_year(path: Path) -> pd.DataFrame:
    """Read one raw workbook as strings with harmonized column names (suppression markers kept)."""
    return harmonize_columns(pd.read_excel(path, dtype=str))


def to_numeric(series: pd.Series) -> pd.Series:
    """Convert an OEWS value column to float; suppression markers (*, **, #) become NaN."""
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(),
                         errors="coerce")
