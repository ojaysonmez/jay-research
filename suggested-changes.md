# Suggested skill changes

Changes to the jay-research skill that test runs suggested. Nothing here has been applied. Pick items up when there is time, and change **Status** to `done` (with the commit) or `rejected` (with the reason).

Source runs: **R1** = "CGM MARD accuracy comparison" (Quick, 2026-10-24), **R2** = "CGM device comparison table" (Quick, structured mode, 2026-10-24). The raw text is in each run's `_run.md` (gitignored, lost when the container ends), so this file is the lasting record.

| # | Status | Where | Suggested change | Why | Seen in |
|---|--------|-------|------------------|-----|---------|
| 1 | open | `references/researcher.md` (Output) | State that a brief correction goes inside Cited Findings of the key question it belongs to, never as its own `## Brief corrections` section. | A researcher added a top-level section, `check_notes.py` rejected it as a key question with no sub-sections, and it cost a fix round. | R2 |
| 2 | open | `references/researcher.md`, `SKILL.md` step 5 | Have researchers report the tool calls for an answer or follow-up round separately from the original budget. | A researcher showed 7 of 6 because its answer round was counted against the original budget, which raised a `budget-hit` flag that was not a real overrun. | R2 |
| 3 | open | `SKILL.md` Research depth table | Consider raising the Quick budget from 6 to about 8 tool calls for device-accuracy and similar questions. | Both researchers used the whole budget and left a critical gap in R1, and one left a gap in R2. `budget-hit` appeared in 2 of 2 Quick runs. | R1, R2 |
| 4 | open | `references/researcher.md` (Sources) | Note that Consensus gives the best methodology reviews but returns no DOIs, so DOIs for scientific topics need a PubMed lookup. | The methods researcher marked every peer-reviewed paper "DOI not found". | R1 |
| 5 | open | `references/researcher.md` (Sources) | Note that the NyquistAI `usfda_device_search` needs a structured `request` argument, not a `query` string. | One researcher's FDA call failed on this. Another researcher's plain query worked, so the behavior is inconsistent. Worth re-checking before writing it down. | R1, R2 |
| 6 | open | `references/researcher.md` (Sources) | Note that PubMed search returns only PMIDs, and `get_article_metadata` on many PMIDs overflows, so fetch fewer PMIDs per call. | A researcher spent calls on extraction after an overflow. | R1 |
| 7 | open | `references/researcher.md` (Sources) | Note that Parallel `web_search` returns FDA SSED and decision PDFs from accessdata.fda.gov directly. | Two researchers got FDA documents this way when other routes failed. | R1, R2 |
| 8 | open | `scripts/check_notes.py` | Check whether a top-level bullet ending in a colon (a header-style line whose sources sit in its sub-bullets) should count as a finding without a source. | It flagged "iCGM measurement-related special controls (21 CFR 862.1355):", which looked like a false positive. Not tested yet. | R1 |
| 9 | open | `scripts/run_review.py` | Accept depth written as a level number (for example "level 1") when reading `run start`, so the history shows the depth instead of `?`. | In my script test the depth showed `?`. A real run wrote "Quick", so this is low priority. | script test |

Also noted, not a skill change: the run history was written to `research_notes/history.md` because `~/.jay-research/` does not exist in the cloud container. The skill's default location only persists on the user's own computer.
