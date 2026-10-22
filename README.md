# jay-research

A personal [Claude Code](https://claude.com/claude-code) skill for multi-source research. It is a customised copy of the built-in `deep-research` skill. A coordinator agent splits a question into subtopics, runs parallel researcher subagents, and has a report-writer subagent turn their notes into a single cited Markdown report.

## How it works

1. **Clarify** – asks follow-up questions only when the answer would change the research (ambiguous terms, region, entities, or no depth level given).
2. **Title and folders** – picks a short sentence-case title (3–6 words, under 50 characters) and creates `research_notes/{title}/` and `reports/`.
3. **Decompose** – splits the question into independent subtopics, capped by the chosen depth level.
4. **Research** – spawns one foreground `general-purpose` researcher per subtopic, all in parallel, on Sonnet. Each saves notes to `research_notes/{title}/{topic}.md` and replies with a short status report only.
5. **Gap-fill (optional)** – at Deep and Exhaustive levels only, one extra round for critical gaps. Where it can, it continues the researcher that owns the gap (via `SendMessage`) instead of starting a new one, so sources are not re-read. It never runs a second time.
6. **Write** – a report-writer subagent, on the coordinator's model, synthesises the notes into `reports/{title}.md` and replies with a 3–5 sentence summary.
7. **Deliver** – the coordinator sends or copies the report and passes on that summary.

The coordinator never researches, writes files, or reads notes itself, which keeps its context clean. Subagents return fixed-format replies rather than their findings, for the same reason.

### Models

| Role | Model |
|---|---|
| Coordinator | whatever the session runs on |
| Researchers | Sonnet (faster, cheaper; the work is mostly search and reading) |
| Report writer | inherits the coordinator's model (the work is synthesis) |

Say "use Opus for everything" (or any model) in the request to override.

## Usage

```
/jay-research <question>
/jay-research deep: <question>
/jay-research dry-run: <question>
/jay-research dry-run deep: <question>
/jay-research help
```

If no level is named, the skill asks. If nobody answers, it uses Quick and says so at the top of the report.

### Depth levels

| Level | Researchers | Tool calls each | Extra round | Report |
|---|---|---|---|---|
| 1 Quick (default, ~5–10 min) | 1–2 | up to 6 | never | 1–2 pages, key findings |
| 2 Standard (~10–20 min) | 3 | up to 10 | never | 3–4 focused sections |
| 3 Deep (~20–35 min) | 4–5 | up to 15 | only for a critical gap | full report |
| 4 Exhaustive (40+ min) | 6+ | up to 20 | allowed | full report + complete reference list |

You can also say "level 1–4" instead of the name.

### Dry-run mode

Plans the research without running it: no folders, no subagents, no questions. It returns the scope, assumed answers to follow-ups, depth and title, a researcher table, the budget in subagents and tool calls, and the expected report shape. Reply "go" to run the plan as shown, or give changes.

## Sourcing rules

- **Connectors first.** Researchers search connected databases (PubMed, Amass, Consensus, ClinicalTrials.gov, bioRxiv) before the open web, and fetch web pages only for facts those databases cannot supply.
- **Every claim carries a source.** Unsourced findings go in a Gaps section and are left out of the report.
- **DOIs only for scientific and clinical topics.** The coordinator classifies each request. For topics that need scientific evidence, every journal article or preprint is cited with its DOI, or "DOI not found". DOIs are never invented. For market research, general research and product topics, no DOIs are collected and sources are cited by URL only.
- **Identifiers are hyperlinks.** DOIs, FDA numbers (510(k), PMA, NDA, BLA, ANDA, recall numbers) and clinical trial numbers (NCT IDs) always appear as links, for example `[NCT01234567](https://clinicaltrials.gov/study/NCT01234567)`, never as plain text. Links are never guessed.
- Other sources (news, company pages, registries) need only a URL.
- **Findings, inferences and gaps stay separate.** The report writer treats inferences as leads, not evidence.

## Output

```
research_notes/
  {title}/
    {topic}.md        # one file per researcher
reports/
  {title}.md          # final report
```

Reports use a BLUF opening paragraph, 3–5 narrative sections with signpost headers, and a short conclusion. The depth level appears directly under the title.

Follow-up requests on an earlier topic get a new title and a new folder. The earlier report and notes are passed to the report writer as background, and earlier folders are never overwritten.

## Repository layout

| File | Purpose |
|---|---|
| [SKILL.md](SKILL.md) | Coordinator instructions: modes, depth levels, process, subagent prompt templates |
| [references/researcher.md](references/researcher.md) | Instructions each researcher reads: search loop, source evaluation, note format |
| [references/report-writer.md](references/report-writer.md) | Instructions the report writer reads: structure, style, citations |

## Requirements

- A Claude Code environment with the `Agent` (or `Task`) tool for spawning subagents. Without it, research the question directly.
- Optional: a `model` parameter on the Agent tool (otherwise every role uses the session's model) and the `SendMessage` tool (otherwise gap-fill starts new researchers).
- Optional: connected research databases for better sourcing.

## Installation

Place this folder where Claude Code loads skills, for example `~/.claude/skills/jay-research/`, so that `SKILL.md` sits at the folder root.
