# Failure log

Failures during real runs of the jay-research skill, recorded the moment they happen (`scripts/log_failure.py`, called from the "Failures and time limits" section of `SKILL.md`). One row per failure. This file is committed, so a run that dies before its end-of-run steps still leaves a record. Use it to decide what to fix: when a row repeats, add a row to `suggested-changes.md`.

Not for suggestions. A suggestion goes in `suggested-changes.md`; this file is the evidence behind it.

| Date | Run | Stage | What failed | What the coordinator did | Outcome |
|------|-----|-------|-------------|--------------------------|---------|
