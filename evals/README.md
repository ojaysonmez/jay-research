# jay-research evals

Two checks that measure whether the skill gets things right, not only whether its output is well formed. Run them before and after a change to the skill, and compare the scores.

## 1. Known-answer questions (`cases.json`, `score.py records`)

Each case has a question, the options to run it with, and expected values for the merged records.

1. Run the case's question with its options, for example `/jay-research quick table: <question>`. The case must use structured mode, because the scorer reads `_records.json`.
2. Score the run: `python3 evals/score.py records <case id> "research_notes/<run title>"`
3. Each expectation is `PASS`, `WRONG` (different value) or `MISSING` (no record, or null). The exit code is 0 only if all pass.

A case with `"status": "draft"` has expected values that nobody has confirmed against an independent source, so a score on it only shows that two runs agree. Change the status to `confirmed` only after checking each value against the FDA label or other primary source.

**Cases**

| Case | Status | What it checks |
|---|---|---|
| `icd10-t2d-complications` | claude-confirmed | five E11 codes and whether each is billable (ICD-10 lookup, FY2027) |
| `glp1-trials-registry` | claude-confirmed | NCT number, sponsor, phase, enrollment and status of five named trials (ClinicalTrials.gov) |
| `cms-glucose-monitor-lcds` | claude-confirmed | eight Medicare LCDs in effect on 2026-10-24, with titles and contractors (CMS database) |
| `fda-nda-glp1` | claude-confirmed | NDA number, applicant and active ingredient for four GLP-1 products (Drugs@FDA) |
| `cgm-4-devices` | draft | built from values two runs agreed on; leaves out the disputed ones |

**Last results (2026-10-24, Quick, structured, one run each, no report written):** `icd10-t2d-complications` 10/10, `glp1-trials-registry` 25/25, `cms-glucose-monitor-lcds` 16/16, `fda-nda-glp1` 12/12.

**Reading the scores:** these four cases are registry lookups, and the researchers use the same registries that confirmed the answers, so a perfect score shows the pipeline carries registry facts through intact. It does not show that the skill handles conflicting sources, since none of these cases has a conflict. Cases that test that need an answer a person has confirmed against a primary source, such as the disputed CGM values (G7 and Libre 3 clearance numbers, G7 warm-up, Libre 3 MARD). The `claude-confirmed` status means Claude read the registry, so spot-check a few values.

The runs did show format problems the scores hide: a connector-only source with no URL fails the notes and records checks, and one researcher left out two note sub-sections (suggested-changes.md rows 13 and 14).

To add a case, copy the entry in `cases.json`. `expected` entries take `item` (matched against the first field of the record, ignoring case), `field`, and either `contains` (text) or `number` with an optional `tolerance`.

## 2. Seeded errors for verify mode (`verify-seeded/`, `score.py verify`)

`verify-seeded/report.md` is a copy of a real report with three errors planted (`seeded.json` lists them). Verify mode should flag each one and return FAIL.

1. Put the report at `reports/Verify seeded test.md` and run the verify step on it (`references/verify.md`), with notes in `research_notes/Verify seeded test/`.
2. Score the merged file: `python3 evals/score.py verify evals/verify-seeded/seeded.json "reports/Verify seeded test verification.md"`
3. A seeded error counts as caught when its marker text appears in a HIGH-WARN or MED-WARN claim. The outcome must also be FAIL.

**Last result (2026-10-24):** 3/3 caught, outcome FAIL, with 5 HIGH-WARN claims in all (the extra two cite a broken link that the seeded K241353 number created). The same verifier setup returned PASS on the unseeded report.

**Limits:** the planted errors can each be settled against a source the report cites, so they are the easy kind. Add harder ones: a number that drifts slightly (8.8% to 9.8%), or a claim that a cited page does not state. The scorer matches the marker text as a substring, so a marker that is a common number can match by chance. Pick markers that are unlikely to appear elsewhere.
