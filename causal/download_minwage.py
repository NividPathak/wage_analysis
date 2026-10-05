"""Download Vaghul & Zipperer (2022) v1.4.0 and build the state minimum wage panel 2005-2022.

Output: data_processed/state_minwage_2005_2022.csv with columns
state, fips, year, state_mw, federal_mw, effective_mw.
"""

from __future__ import annotations

import subprocess
import zipfile

import numpy as np
import pandas as pd

from causal.geo import STATES
from causal.oews_io import REPO_ROOT

MW_DIR = REPO_ROOT / "data_external" / "minwage"
OUT_PATH = REPO_ROOT / "data_processed" / "state_minwage_2005_2022.csv"
SOURCE_FILE = "mw_state_annual.xlsx"
YEARS = range(2005, 2023)


def download() -> None:
    """Fetch every release asset with the GitHub CLI and unzip them."""
    MW_DIR.mkdir(parents=True, exist_ok=True)
    if not (MW_DIR / SOURCE_FILE).exists():
        subprocess.run(["gh", "release", "download", "v1.4.0", "-R",
                        "benzipperer/historicalminwage", "-D", str(MW_DIR), "--clobber"],
                       check=True)
        for z in MW_DIR.glob("*.zip"):
            zipfile.ZipFile(z).extractall(MW_DIR)


def build() -> pd.DataFrame:
    """Return the 51-unit x 18-year panel using annual average state and federal minimums."""
    raw = pd.read_excel(MW_DIR / SOURCE_FILE)
    df = raw.rename(columns={"State FIPS Code": "fips", "State Abbreviation": "state",
                             "Year": "year", "Annual State Average": "state_mw",
                             "Annual Federal Average": "federal_mw"})
    df = df[df["fips"].isin(STATES) & df["year"].isin(YEARS)].copy()
    df["effective_mw"] = np.fmax(df["state_mw"], df["federal_mw"])
    df = df[["state", "fips", "year", "state_mw", "federal_mw", "effective_mw"]]
    return df.sort_values(["state", "year"]).reset_index(drop=True)


def main() -> None:
    download()
    df = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"wrote {OUT_PATH} ({len(df)} rows, {df['state'].nunique()} states)")


if __name__ == "__main__":
    main()
