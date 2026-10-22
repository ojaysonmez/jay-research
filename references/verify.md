# Fact-checking the report (step 7)

The coordinator reads this file only when verify is on (see "Verify mode" in SKILL.md), after the report writer has finished.

Keep your context clean here too: do not read the report or the claims yourself. In the prompts below, replace {path_to_verify_claims} with the verify-claims skill's base directory (the folder that holds its SKILL.md), and fill in the other placeholders as in step 4 of SKILL.md.

**a. Extract the claims.** Spawn one subagent (subagent_type="general-purpose", run_in_background=false, `model` as in "Models per role"):

```
Agent(
  run_in_background=false
  subagent_type="general-purpose",
  description="Extract report claims",
  prompt="Read {path_to_verify_claims}/SKILL.md and follow only its section "2. Extract claims", applied to the report at {absolute path of your working directory}/reports/{research title}.md. Treat every DOI, FDA number and clinical trial number in the report as a claim about what that identifier points to, and use the report's own inline citation for each claim as its source.

Write the claims in batches of up to 25 to {absolute path of your working directory}/research_notes/{research title}/claims batch {N}.md. Each claim gets its ID (C1, C2, ...), the claim, its source (or "no source given") and one verification question.

Then reply with exactly: the number of claims and the number of batch files, and nothing else."
)
```

**b. Verify each batch.** Spawn one verifier per batch file, all in a single turn so they run in parallel. Each must be a new subagent, never a fork of this conversation:

```
Agent(
  run_in_background=false
  subagent_type="general-purpose",
  description="Verify claims batch {N}",
  prompt="Read {path_to_verify_claims}/SKILL.md and follow only its section "Verifier protocol". Ignore the rest of that file, and do not open the report or any other file in {absolute path of your working directory}/reports/.

Your claims are in {absolute path of your working directory}/research_notes/{research title}/claims batch {N}.md.

Write your report, in the protocol's report format, to {absolute path of your working directory}/research_notes/{research title}/verification batch {N}.md.

Then reply with exactly: the outcome (PASS, PARTIAL or FAIL), the tier counts, and the IDs of any HIGH-WARN claims, and nothing else."
)
```

**c. Combine.** Merge the batch reports with the script, which counts tiers and lists the high-risk claims exactly:

`python3 "{path_to_skill}/scripts/merge_verification.py" "{absolute path of your working directory}/research_notes/{research title}" "{absolute path of your working directory}/reports/{research title} verification.md"`

On success (exit code 0) it prints one line with the overall outcome and the tier counts; use that line in step 8 and do not open the file. If it exits with code 2 or 4, or cannot run at all, fall back to a subagent: spawn one subagent to merge the batch reports into {absolute path of your working directory}/reports/{research title} verification.md, using verify-claims section "4. Report": overall outcome and tier counts first, then each HIGH-WARN claim with its evidence and the correct value from the source, then the claims that could not be verified and why. It must not edit the report itself. It replies with the overall outcome, the tier counts and the number of HIGH-WARN claims, and nothing else.

Do not correct the report automatically. The user decides which corrections to apply.
