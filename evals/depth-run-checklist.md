# Depth run checklist

What to look for when a real run uses Standard, Deep or Max. Light, structured mode, verify mode, help, dry-run and follow-ups have been tested in earlier runs (see `README.md`); the depths below have not. Mark each item pass, fail or not exercised, and keep the evidence: the run's `_run.md`, the end-of-run summary, and `research_notes/history.md`.

Light was called Quick and Max was called Exhaustive in earlier runs, and the old names still work.

Run the skill by its repo name (`/jay-research deep: <question>`), commit `suggested-changes.md` afterwards, and keep the same session for follow-up questions.

## All three depths

- [ ] **Depth is recorded.** `_run.md` says the depth in `run start`, and the history line shows it (not `?`).
- [ ] **Researchers start in parallel,** each with the sibling topics list and its tool-call budget.
- [ ] **Budgets match the level.** Researcher counts and calls per researcher are within the table below. A `budget-hit` flag with a critical gap is a finding about the level, not a failure.
- [ ] **Checks ran:** the notes, report and DOI checks (and records, if `table:`) appear on the `report end` line, each as OK or fixed.
- [ ] **No loops.** Each fix round ran once at most.
- [ ] **The summary** gives where the report is, run time, suggested changes, the `suggested-changes.md` row line, and the follow-up pointer.
- [ ] **Failures are logged.** If any agent failed, the run log has a `fallback` event, `failure-log.md` has a row for it (commit that file), and the summary names any topic not covered (see "Failures and time limits" in `SKILL.md`, which has not been exercised by a real failure yet).

| Level | Researchers | Calls each | Step 5 (extra round) | Report |
|---|---|---|---|---|
| Standard | 3 | up to 12 | never, except open questions | 3-4 focused sections |
| Deep | 4-5 | up to 15 | only for a critical gap | full report |
| Max | 6 or more | up to 20 (25 for scientific or clinical topics) | only for a critical gap, also allowed to run | full report plus complete reference list |

## Standard

- [ ] Exactly 3 researchers, and no gap round even if a researcher reports a critical gap.
- [ ] An open question, if any, still triggers the one answer round.

## Deep

- [ ] 4 or 5 researchers.
- [ ] **Gap round, if a researcher reported a critical gap:** the coordinator says "After these researchers finish, I will move directly to coordinating the report writer", continues the owning researcher with `SendMessage` at half the budget, and the follow-up file is named `{topic} followup.md`. `_run.md` ends the research with `gap round: N continued, M spawned`.
- [ ] **Only one gap round,** whatever its results.
- [ ] If no researcher reported a critical gap, mark the gap round "not exercised". It cannot be forced.
- [ ] Run time is inside the 20 to 35 minute estimate, or the summary explains why not.

## Max

- [ ] 6 or more researchers started in one turn, with no rate-limit or timeout errors. This is the main new risk: more parallel agents than any earlier run.
- [ ] Up to 20 calls each, or 25 for a scientific or clinical topic.
- [ ] The report ends with a complete reference list, and every identifier in it is a hyperlink.
- [ ] The coordinator's context stays manageable: it still reads only the short replies and script output.
- [ ] Time check: if the run passed 60 minutes before step 5, the coordinator skipped step 5 and said so.

## Afterwards

Commit `suggested-changes.md` (the run appends its rows there) and send Claude the final summary and `_run.md`; `research_notes/` is gitignored, so it will not be in the commit. Score the run against this list. If the question has an answer you can confirm against a primary source, add it to `cases.json` as a `confirmed` case.
