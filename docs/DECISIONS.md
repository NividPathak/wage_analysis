# Decisions log

One line per decision, with the reason. Choices not covered by the build plan default to the more
conservative, more standard option.

## Phase 0: import

- Repo name `NividPathak/wage_analysis` was free, so the plan's default name is used.
- `git push --mirror` succeeded with all 25 LFS objects pushed first; no fallback needed. History verified: 48 commits, all original authors present.
- Commit messages carry no `Co-Authored-By` trailer, following the owner's standing preference.
- The team's `.gitattributes` routes every `*.csv` to Git LFS. New small outputs (`data_processed/`, `results/`, `tests/fixtures/`) are exempted so CI and readers can use them without LFS.
