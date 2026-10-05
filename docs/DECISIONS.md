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

## Phase 4: treatment definition

- Dropped from the event study (above federal by 2010, no large jump in 2011+): MI, MT, OH, OR, VT. They remain in the continuous TWFE regressions, which do not need a discrete treatment date.
- The large-jump rule is applied to annual-average minimum wages, so a mid-year increase is split over two calendar years; a jump that is large in total but split evenly can fall below the threshold. Kept as written in the plan.
- Some treated states had small indexed increases before their first large jump (for example FL and AZ before g). Their pre-period is not perfectly clean; this biases event-study estimates toward zero. Kept as written in the plan and listed as a limitation.

## Phase 5: difference-in-differences

- `differences` 0.3.0 installed and used as the primary Callaway-Sant'Anna estimator (never-treated controls, universal base period so leads compare to g - 1 like the TWFE reference period, 999 multiplier-bootstrap draws, seed 42). Passing `cluster_var` crashes in this version, so its default unit-level bootstrap is used; units are states, so this is clustering by state.
- `causal/cs_did.py` was also written (plan's fallback design: 2x2 DiDs, cohort-size weights, 999 state-resampling bootstrap draws, seed 42). It supplies the CS pre-trend Wald test, because `differences` does not expose the joint covariance of the leads. Point estimates agree with `differences` to about 1e-16 (`cs_crosscheck_max_abs_diff` in `results/did_event_study.json`).
- CS 95% CIs are computed as ATT +/- 1.96 SE from the package's bootstrap SE (its own `lower`/`upper` columns mix pointwise and simultaneous bands across aggregations).
- TWFE event study built with explicit relative-time dummies (endpoints binned at -5 and +5, -1 omitted; never-treated states have all dummies zero) rather than `i()`, which needs a placeholder value for never-treated units.
- TWFE pre-trend test uses an F test (pyfixest `wald_test`, cluster-robust); the CS pre-trend test uses a chi-square Wald test with the bootstrap covariance.
- The event study also includes the placebo outcome `log_median_cs` so Phase 7 can report it under both 5a and 5b.
- Lagged-treatment regressions lose the first 1 or 2 years of the panel (N = 867 and 816) rather than extending the minimum wage series before 2005.
- Added (not in the plan): a pre-COVID robustness check, CS on years <= 2019 with cohorts g <= 2019. Reason: for the early cohorts, event times +4 and +5 fall in 2019-2022, where pandemic food-service job losses differed across states.
- Added: a static binary TWFE DiD (`post` dummy), which is the estimator reused in the Phase 7 power simulation.

## Phase 6: synthetic control

- Case selection reads "largest single-year percentage increase" as the jump in the state's treatment year g (the event the study is about). Result: AZ, g = 2017 (see `results/synth.json` for the jump size). Every treated cohort leaves at least 5 pre-years because the panel starts in 2005.
- `pysyncon` installed, so the scipy SLSQP fallback was not needed. V is optimized with Nelder-Mead from equal starting weights (package default).
- Outcome predictors: means of `log_p10_all` over three equal pre-period sub-windows, plus the pre-period mean of `log_emp_all`. Sub-windows rather than one overall mean so the fit tracks the pre-period path, a standard choice.
- Placebo-in-space: each never-treated donor is refit as the fake treated unit using the other 19 donors and the same treatment year. With 21 units, the smallest possible permutation p-value is 1/21.

## Phase 7: power and falsification

- There are fewer never-treated states (20) than real treated states (26), so the plan's "same number of states" is impossible. Each draw instead gives fake treatment to the same share of states as the real design (26 / 46, rounded to 11 of 20), with treatment years drawn with replacement from the real cohort-year distribution. The placebo panel is smaller than the real one, so the reported MDE is conservative (too large rather than too small).
- Each draw is fit once. Adding delta * post to y shifts the estimate by exactly delta and leaves the clustered SE unchanged (checked numerically), so power for every delta comes from the same 500 fits. p-values use t with G - 1 degrees of freedom, matching pyfixest's CRV1 inference.
- MDE is read off a 0.001-step grid from 0 to 0.2 in addition to the plan's six deltas.

## Phase 9: app, CI, polish

- `app.py` uses a sidebar radio, not `st.navigation`, so a `pages/` folder adds the new page through Streamlit's classic multipage mode without touching `app.py`.
- The page reads only `results/` and imports the same `causal.report` helpers that write RESULTS.md, so the app and the report cannot show different numbers.
- CI runs on Python 3.11 with `requirements-causal.txt`. Tests need only committed files: the minimum wage CSV, the panel parquet, `results/*.json`, RESULTS.md, and a 15-state fixture panel in `tests/fixtures/` that runs the estimators end to end.
- `.gitattributes` exemptions for the new output folders use `!filter !diff !merge` so JSON and CSV outputs are stored as plain git files (not LFS) and stay diffable; `*.png` and `*.parquet` are marked binary.
- `make all` creates `.venv` with `python3.11` (override with `make all PYTHON=python3.12`) if it does not exist.
- Learning notes are generated by `causal/learning_notes.py` (run by `make report`) so the interview answers quote numbers from `results/*.json` rather than hand-typed values.
