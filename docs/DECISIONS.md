# Decisions log

One line per decision, with the reason. Choices not covered by the build plan default to the more
conservative, more standard option.

## Phase 0: import

- Repo name `NividPathak/wage_analysis` was free, so the plan's default name is used.
- `git push --mirror` succeeded with all 25 LFS objects pushed first; no fallback needed. History verified: 48 commits, all original authors present.
- Commit messages carry no `Co-Authored-By` trailer, following the owner's standing preference.
- The team's `.gitattributes` routes every `*.csv` to Git LFS. New small outputs (`data_processed/`, `results/`, `tests/fixtures/`) are exempted so CI and readers can use them without LFS.

## Phase 1: environment and data audit

- Python 3.11 (`/opt/homebrew/bin/python3.11`) used for `.venv`; the system default is 3.14, which the plan does not target.
- `pandas` pinned below 3 (2.3.3) and `xlrd` upgraded to 2.x inside `.venv`: pandas 3 refuses the team's `xlrd==1.2.0` pin, and xlrd 2.x still reads `.xls`. The team's `requirements.txt` is unchanged; `app.py` only reads CSV/xlsx so it is unaffected.
- `pysyncon` and `differences` both installed, so the Phase 5 and Phase 6 primary paths are attempted first.
- Column alias map reused from the team's `notebooks/Data_cleaning.ipynb` (`column_alias`), copied into `causal/oews_io.py` and extended with `AREA_TYPE` and `A_MEDIAN`.
- The causal panel is built from the raw BLS workbooks in `data/`, not `cleaned_data/`: the cleaned CSVs drop the `00-0000` All Occupations rows that the wage-bite outcome needs.
- States are keyed on the `AREA` FIPS code in every year, because the 2019 file has no postal-code column.
- All 2005-2024 state workbooks are present with hourly percentiles, so the BLS download fallback (`causal/download_oews.py`) was written but not needed.

## Phase 2: minimum wage panel

- Source file: `mw_state_annual.xlsx` from the `mw_state_excel.zip` asset of Vaghul & Zipperer v1.4.0.
- Columns used: `Annual State Average` and `Annual Federal Average` (the annual average, as the plan prefers), keyed on `State FIPS Code` and `State Abbreviation`.
- `effective_mw = max(state_mw, federal_mw)`; no missing values in the 2005-2022 window for the 50 states plus DC.
