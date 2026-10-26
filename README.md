# jay-research

A personal [Claude Code](https://claude.com/claude-code) skill for multi-source research. It is a customised copy of the built-in `deep-research` skill. A coordinator agent splits a question into subtopics, runs parallel researcher subagents, and has a report-writer subagent turn their notes into a single cited Markdown report.

## How it works

1. **Clarify** – asks follow-up questions only when the answer would change the research (ambiguous terms, region, entities, or no depth level given).
2. **Title and folders** – picks a short sentence-case title (3–6 words, under 50 characters) and creates `research_notes/{title}/` and `reports/`.
3. **Decompose** – splits the question into independent subtopics, capped by the chosen depth level. For comparison scans (many companies, products, papers or trials compared on the same criteria) it also turns on **structured mode**: researchers return one record per item with a fixed set of fields, and a script merges them into one comparison table for the report. Add `table:` or `no table:` to the request to force it on or off; dry-run shows the proposed fields so you can change them first.
4. **Research** – spawns one foreground `general-purpose` researcher per subtopic, all in parallel. Each saves notes to `research_notes/{title}/{topic}.md` and replies with a short status report only.
5. **Gap-fill (optional)** – at Deep and Max levels only, one extra round for critical gaps. Where it can, it continues the researcher that owns the gap (via `SendMessage`) instead of starting a new one, so sources are not re-read. It never runs a second time.
6. **Write** – a report-writer subagent synthesises the notes into `reports/{title}.md` and replies with a 3–5 sentence summary, then a script checks the report's links and identifiers, and the writer fixes any flagged lines. Scripts also check the researchers' notes before the report is written and confirm that every DOI exists in the DOI registry.
7. **Verify (optional)** – only when requested with `verify`. Fresh subagents fact-check the report's claims, DOIs and registry numbers with the [verify-claims](#verify-mode) skill and write `reports/{title} verification.md`. The report itself is never edited automatically.
8. **Deliver** – the coordinator sends or copies the report (and the verification file, if any) and passes on the summary.

During a run, the coordinator never researches, writes files, or reads notes itself, which keeps its context clean. Only when answering a follow-up question after delivery does it search the report, and at most one topic's notes, for the relevant passage. Subagents return fixed-format replies rather than their findings, for the same reason.

### Models

Every subagent uses the main chat's model unless the request names one. Say "use Sonnet" to run every subagent on Sonnet, or "Sonnet for researchers, Opus for the report" to set them per role.

## Usage

```
/jay-research <question>
/jay-research deep: <question>
/jay-research dry-run: <question>
/jay-research dry-run deep: <question>
/jay-research deep verify: <question>
/jay-research deep table: <question>
/jay-research help
```

The skill only runs when you invoke it by name; for other research questions it suggests itself in one sentence.

If no level is named, the skill asks. If nobody answers, it uses Light and says so at the top of the report.

### Depth levels

| Level | Researchers | Tool calls each | Extra round | Report |
|---|---|---|---|---|
| 1 Light (default, ~5–10 min) | 1–2 | up to 8 | never | 1–2 pages, key findings |
| 2 Standard (~10–20 min) | 3 | up to 10 | never | 3–4 focused sections |
| 3 Deep (~20–35 min) | 4–5 | up to 15 | only for a critical gap | full report |
| 4 Max (40+ min) | 6+ | up to 20 (25 for scientific or clinical topics) | allowed | full report + complete reference list |

You can also say "level 1–4" instead of the name.

### Verify mode

Add `verify` before the colon (for example `/jay-research deep verify: <question>`) to fact-check the finished report. A claim extractor pulls every factual claim, DOI, FDA number and trial number from the report; fresh verifier subagents, which never see the report, check each one against its source in batches of up to 25; the results are merged into `reports/{title} verification.md` with an overall PASS, PARTIAL or FAIL. Expect it to add about one research round of time. It needs a `verify-claims` skill installed; without one, the step is skipped with a note.

### Dry-run mode

Plans the research without running it: no folders, no subagents, no questions. It returns the scope, assumed answers to follow-ups, depth and title, a researcher table, the budget in subagents and tool calls, and the expected report shape. Reply "go" to run the plan as shown, or give changes.

## Sourcing rules

- **Connectors first.** Researchers search connected databases (PubMed, Amass, Consensus, ClinicalTrials.gov, bioRxiv) before the open web, and fetch web pages only for facts those databases cannot supply.
- **Every claim carries a source.** Unsourced findings go in a Gaps section and are left out of the report.
- **DOIs only for scientific and clinical topics.** The coordinator classifies each request. For topics that need scientific evidence, every journal article or preprint is cited with its DOI, or "DOI not found". DOIs are never invented. For market research, general research and product topics, no DOIs are collected and sources are cited by URL only.
- **Identifiers are hyperlinks.** DOIs, FDA numbers (510(k), PMA, NDA, BLA, ANDA, recall numbers) and clinical trial numbers (NCT IDs) always appear as links, for example `[NCT01234567](https://clinicaltrials.gov/study/NCT01234567)`, never as plain text. Links are never guessed.
- Other sources (news, company pages, registries) need only a URL.
- **The brief is checked, not trusted.** Researchers confirm the facts the question takes for granted (codes, company status, product names). A wrong one is researched correctly, reported as a brief correction, and stated openly in the report.
- **Findings, inferences and gaps stay separate.** The report writer treats inferences as leads, not evidence.

## Output

```
research_notes/
  {title}/
    {topic}.md        # one file per researcher
    agents.md         # the run's question, depth, report path and researcher IDs
    _run.md           # timestamped run log
reports/
  {title}.md          # final report
```

Ask "how long did that take?" or "which stage was slowest?" after a run and the coordinator answers from the run log, with durations computed by the script.

After each run, a script checks the run log for abnormalities (a researcher using its whole budget while still reporting a critical gap, a slow non-research stage, a check still failing after its fix round, a fallback path, DOIs that do not exist). The coordinator logs one suggested change to the skill per abnormality and mentions them in one line; it never edits the skill itself. Each run also adds one line to a private run history (`~/.jay-research/history.md`, or the path in `JAY_RESEARCH_HISTORY`). Every run also screens the skill itself: the history records which features the run used (the notes, report and DOI checks, the SendMessage gap round, verify and its merge script) and whether each worked, so ordinary runs double as tests. Researchers report source tips (a site that blocks fetching, a connector that worked better), which become suggested lessons. Ask "what keeps going wrong?" or "which features are proven?" and the coordinator reports recurring issues with the latest suggestion for each, features never exercised or that keep failing, and recent lessons. The skill never edits its own files; every change is yours to make. The history names run titles, so keep it out of public repositories; `.gitignore` excludes the usual places.

Reports use a BLUF opening paragraph, 3–5 narrative sections with signpost headers, and a short conclusion. The depth level appears directly under the title.

Follow-up questions after a report are routed to the cheapest path. If the report already answers it, the main chat answers from it, with no new folder. If it needs more digging inside an existing topic in the same conversation, the researcher that covered it is continued via `SendMessage`, the new notes go in a new folder, and an updated report is offered (verification is off unless requested again). Anything else becomes a new run with a new title and folder, and the earlier report and notes are passed to the report writer as background. Earlier folders are never overwritten.

## Repository layout

| File | Purpose |
|---|---|
| [SKILL.md](.claude/skills/jay-research/SKILL.md) | Coordinator instructions: depth levels, models, sourcing rules, process, subagent prompt templates |
| [references/researcher.md](.claude/skills/jay-research/references/researcher.md) | Instructions each researcher reads: search loop, source evaluation, note format |
| [references/report-writer.md](.claude/skills/jay-research/references/report-writer.md) | Instructions the report writer reads: structure, style, citations |
| [references/modes.md](.claude/skills/jay-research/references/modes.md) | Help and dry-run modes, read by the coordinator only when requested |
| [references/verify.md](.claude/skills/jay-research/references/verify.md) | The optional fact-check step, read only when `verify` is on |
| [references/records.md](.claude/skills/jay-research/references/records.md) | Structured mode for comparison scans: choosing fields, briefing researchers, checking and merging records |
| [references/follow-ups.md](.claude/skills/jay-research/references/follow-ups.md) | Routing for follow-up questions after a report is delivered |
| [scripts/check_notes.py](.claude/skills/jay-research/scripts/check_notes.py) | Checks researchers' notes before the report is written (four sections per question, a source link on every finding) |
| [scripts/check_dois.py](.claude/skills/jay-research/scripts/check_dois.py) | Looks every DOI in the report up in the DOI registry and flags any that do not exist; skipped without network |
| [scripts/records.py](.claude/skills/jay-research/scripts/records.py) | Structured mode: records the field list, checks each researcher's records, merges them into one comparison table with duplicates and conflicts handled |
| [scripts/run_review.py](.claude/skills/jay-research/scripts/run_review.py) | Flags abnormalities in a run against fixed thresholds, records one line per run in a private history file, and reports issues that recur across runs |
| [scripts/gaps.py](.claude/skills/jay-research/scripts/gaps.py) | Keeps the project's gap registry (`open-gaps.md` next to `research_notes/`): the report writer adds each run's open gaps and marks gaps a run closed; a gap-closing run starts from the open ones |
| [scripts/log_failure.py](.claude/skills/jay-research/scripts/log_failure.py) | Appends one row per agent failure to `failure-log.md` the moment it happens, so a run that dies early still leaves a committed record |
| [scripts/run_log.py](.claude/skills/jay-research/scripts/run_log.py) | Writes the timestamped run log (`research_notes/{title}/_run.md`) and prints a per-stage time summary |
| [scripts/merge_verification.py](.claude/skills/jay-research/scripts/merge_verification.py) | Merges the verify-mode batch reports into one verification file, replacing a subagent |
| [scripts/check_report.py](.claude/skills/jay-research/scripts/check_report.py) | Mechanical checks on the finished report (identifiers hyperlinked, DOI links match, link targets, depth line); standard library only |

## Requirements

- A Claude Code environment with the `Agent` (or `Task`) tool for spawning subagents. Without it, research the question directly.
- Optional: a `verify-claims` skill, for verify mode.
- Optional: a `model` parameter on the Agent tool (needed only when a request names a model) and the `SendMessage` tool (otherwise gap-fill starts new researchers).
- Optional: connected research databases for better sourcing.

## Installation

The skill lives in `.claude/skills/jay-research/` inside this repository, so a session opened on a clone of the repo (including a cloud session) loads it as a project skill with no setup.

To use it from other folders, link or copy `.claude/skills/jay-research/` to `~/.claude/skills/jay-research/`, so that `SKILL.md` sits at the root of that folder. On Windows, a junction keeps it in sync:

```
mklink /J "%USERPROFILE%\.claude\skills\jay-research" "<path to this repo>\.claude\skills\jay-research"
```
