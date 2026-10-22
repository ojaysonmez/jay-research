---
name: jay-research
description: Jay's own copy of deep-research. Use it instead of the built-in deep-research skill when the user asks for research, a report, or a literature or market scan that needs multiple sources synthesized into a report. Requires a tool for spawning subagents (Agent or Task); otherwise research the question directly.
---

# Coordinating Deep Research

## Your Role

You are acting as the **coordinator**. Your job is to analyze the user's question, spawn subagents, and manage output files. In order to keep your context clean, you should never conduct research or write files directly. The only file you write yourself is agents.md (step 4). For the same reason, you also should not read the researcher.md or report-writer.md files. The other files in references/ (modes.md, verify.md, follow-ups.md) are for you, and you read each one only when its feature is used. In these instructions, {path_to_skill} means this skill's base directory (the folder this SKILL.md was loaded from).

As you work, if you have a to-do or task-list tool (for example TodoWrite, or TaskCreate and TaskUpdate), use it to keep the user informed of your plan and progress. For clarity, don't reference subagents in those items. For example, you might say "Conduct research" instead of "Spawn research subagents".

## Help and dry-run modes

If the request is "help" (for example "/jay-research help"), or asks for a dry run (for example "/jay-research dry-run: <question>", "dry run" or "plan only"), read {path_to_skill}/references/modes.md and follow the section for that mode. Do no research in either mode.

## Verify mode

Verification is off unless the request turns it on. Turn it on when the word "verify" appears among the options before the question (for example "/jay-research verify: <question>", "/jay-research deep verify: <question>", "/jay-research dry-run deep verify: <question>"), or when the user asks in words for the finished report to be fact-checked. The word "verify" inside the question itself does not count.

When it is on, step 7 fact-checks the finished report with the user's verify-claims skill, using fresh subagents that never see the report. If no verify-claims skill is available, or you cannot find its SKILL.md, tell the user at the start that verification will be skipped and why, and run everything else as usual.

## Research depth

| Level | Researchers | Tool calls per researcher | Extra research round | Report |
|---|---|---|---|---|
| 1 Quick (default, ~5-10 min) | 1-2 | up to 6 | never | 1-2 pages, key findings only |
| 2 Standard (~10-20 min) | 3 | up to 10 | never | 3-4 focused sections |
| 3 Deep (~20-35 min) | 4-5 | up to 15 | only for a critical gap | full report |
| 4 Exhaustive (40+ min) | 6 or more | up to 20 | allowed | full report + complete reference list |

Take the level from the request ("quick", "standard", "deep", "exhaustive", or "level 1-4"). If none is named, ask with AskUserQuestion in step 1, with Quick listed first as the default. If nobody can answer, use Quick and say so at the top of the report. The level caps step 3 (researcher count) and step 5 (extra round). State the tool-call budget in every researcher prompt and the level in the report writer prompt.

## Models per role

By default every subagent (researchers, the report writer and any verification subagents) uses the same model as the main chat: leave the `model` parameter out of every Agent call so each one inherits it.

Only set `model` when the user's request names one. If they name a single model ("use Sonnet"), pass it to every subagent. If they name one per role ("Sonnet for researchers, Opus for the report"), pass each to its role. Use the Agent tool's own model names (for example "sonnet", "opus", "haiku"). If your Agent tool has no `model` parameter, leave it out and say in your first progress update that the requested model could not be applied.

## Sources: connectors first

When connected databases are available (for example PubMed, Amass, Consensus, ClinicalTrials.gov, bioRxiv), tell every researcher to search them before the open web, and to fetch web pages only for facts those databases cannot supply (company news, press releases, regulatory pages).

## Sources: identifiers and DOIs

Decide once, in step 2, whether the topic is **scientific or clinical**: research that needs scientific evidence, such as biomedical, clinical, pharmaceutical or other academic questions. Market research, general research and product topics are not. Pass the decision to every researcher and to the report writer as "Scientific evidence topic: yes" or "no".

- **Yes:** researchers cite peer-reviewed articles and preprints with their DOIs.
- **No:** researchers do not look for DOIs and the report does not list them. Sources are cited by URL only.

Whatever the topic, any DOI, FDA number (510(k), PMA, De Novo, NDA, BLA or ANDA application number, recall number) or clinical trial number (NCT or other registry ID) that appears in notes or in the report must be a hyperlink, never plain text. Say so in every researcher and report writer prompt.

## Process

1. [If necessary] Ask the user follow up questions
2. Choose a title for this research and create its directories
3. Decompose the user's query to determine subagent count
4. Spawn research subagents (in parallel)
5. [If absolutely necessary] Conduct one additional round of research
6. Spawn report writer subagent
7. [If verify is on] Fact-check the report
8. Deliver report to user

### 1. [If necessary] Ask the user follow up questions

Read the user's question and consider if there are any missing or ambiguous details that need to be clarified. Some examples include:
- Ambiguous terminology — Acronyms, jargon, or terms with multiple meanings across different fields
- Implicit geographic or jurisdictional context — Questions where the answer varies significantly by region but no region is specified
- Ambiguous entities — Company names, product names, or proper nouns that refer to multiple distinct entities

In order to avoid creating unnecessary friction with the user, follow ups should only be asked when they would meaningfully impact how research is conducted.

If you determine that you do need to ask follow up questions, do so with the AskUserQuestion tool.

If the request names no depth level, ask for one here as described in "Research depth" above.

### 2. Choose a title for this research and create its directories

First choose a title for this research. It names the folder that will hold this request's research notes and is also the filename of the report the user receives, where it is shown as the report's title, so make it a short, specific title for this research in the user's language and in sentence case: 3 to 6 words and under 50 characters (count them, and drop words rather than exceed either limit), using only letters, numbers and single spaces. Keep accented and non-Latin letters exactly as the user's language writes them (for example é, ñ, ü, 日本語) rather than converting them to plain ASCII, and use no hyphens, underscores, apostrophes or other punctuation. For example, a question about how the EU AI Act affects startups could use "EU AI Act startup obligations".

This research's folders go in the same directory you used for research earlier in this conversation, or, if this is the first research request here, in your current working directory (not /tmp or an uploads folder). Before settling on the title, recall the titles of any research reports you have already delivered earlier in this conversation, and, if a research_notes/ folder already exists in that directory, list it — each folder inside it holds the notes behind a report of the same name in reports/, possibly from an earlier conversation. Then pick the case that fits:
- New topic: choose a fresh title.
- Returning to, extending or updating an earlier topic: choose a title that still names the topic and says what this request adds or changes (for example "EU AI Act startup penalties", not just "Penalties"), or, if nothing distinguishes it from the earlier request, the earlier title with the next number added, dropping a word first if that would exceed the limits above (for example "EU AI Act startup obligations 2"). Note the path of the most recent earlier report on that topic and of its notes folder: you will pass them to the report writer in step 6 as background to build on. If that report or its notes folder is no longer on disk, pass on only what remains and research whatever is missing.
- The user asks for earlier research to be redone independently: choose a title as in the previous case, but do not pass the earlier material on.

In every case the title must differ from every report delivered earlier in this conversation and from every folder you see, so that this request's notes and report never mix with or replace an earlier one's. Never rename, move or write into an earlier request's folder.

Also decide here whether this is a scientific or clinical evidence topic (see "Sources: identifiers and DOIs").

Then create the folders research_notes/{research title}/ and reports/ in that directory. Quote these paths in shell commands, since the title contains spaces, and note the directory's absolute path — you will give the subagents absolute paths into these folders, and they will store their files there.

### 3. Decompose the user's query to determine subagent count

In order to effectively spawn and task subagents, determine if and how the user's question can be decomposed into independent subtopics. These subtopics should be mutually exclusive and collectively exhaustive. For each subtopic, then consider if the research requires (or would benefit from) multiple independent points of view.

| Researchers | Decomposition Strategy | Example |
|-------------|------------------------|---------|
| 1 | No meaningful decomposition — single factual question | "Who won the 2024 Super Bowl?" |
| 3 | Few natural angles or perspectives on a focused topic | "Effects of temperature on salmon migration" → (1) biological mechanisms, (2) observed population data, (3) climate projections |
| 4 | Distinct facets or evaluation criteria | "Compare CRM platforms for small businesses" → (1) pricing models, (2) feature comparison, (3) integrations ecosystem, (4) user reviews/sentiment |
| 5 | Multiple independent entities, regions, or domains | "AI regulation landscape" → (1) US federal, (2) EU/GDPR-AI Act, (3) China, (4) UK, (5) industry self-regulation |
| 6+ | Large enumerable set requiring systematic coverage | "Electric vehicle adoption rates by US state" → researchers assigned to regional clusters |

In the next step, you should spawn one subagent for each subtopic and independent point of view that you identified. The depth level caps the count: if the decomposition calls for more researchers than the level allows, merge subtopics rather than exceed it. If in step 2 you noted earlier research to build on, decompose only what this request adds or needs re-checked; the report writer will have the earlier material.

### 4. Spawn foreground research subagents (in parallel)

For each subtopic and independent point of view determined above, spawn a foreground research subagent.

To spawn research subagents, use the Agent tool (named Task in some versions) with subagent_type="general-purpose" and run_in_background=false, and add `model` only as described in "Models per role". Ensure that you provide **extremely clear, specific** instructions to each research subagent. Be sure to propagate constraints of the original question to the research subagent (e.g., temporal, geographical). In the prompts below, replace {path_to_skill} with this skill's base directory (the directory this SKILL.md was loaded from), {absolute path of your working directory} with the path you noted in step 2, and {research title} with the title you chose in step 2. Follow the exact format provided below:

```
Agent(
  run_in_background=false
  subagent_type="general-purpose",
  description="{3-5 words}",
  prompt="Research {specific narrow topic}.

Objective: {clear description of what's covered in the desired output}

Key questions:
- {Specific question 1}
- {Specific question 2}

Suggested sources:
- {Types of source to prioritize}

Constraints:
- {Any bounds from the initial user query, including temporal or geographic}

Other researchers in this run (do not research these): {one line per sibling researcher: its topic and what it covers, or "none"}

Tool-call budget: {the per-researcher limit for the chosen depth level}

Connected databases to search first: {the connected databases available, or "none"}

Scientific evidence topic: {yes or no}

Save your output notes to {absolute path of your working directory}/research_notes/{research title}/{topic}.md

**As a first step, you must read {path_to_skill}/references/researcher.md for instructions on how to conduct research.**"
)
```

Example of a good, clear, detailed prompt for a research subagent:

> Research the semiconductor supply chain crisis and its current status as of 2026.
>
> Objective: Compile a dense report of the facts, covering the current situation, ongoing solutions, and future outlook, with specific timelines and quantitative data where available.
>
> Key questions:
>  - What are current bottlenecks?
>  - What are the projected capacity increases from new fab construction?
>  - What are geopolitical factors affecting supply chains?
>  - When do experts predict supply will meet demand?
>
> Suggested sources:
> - Recent quarterly reports from major chip manufacturers like TSMC, Samsung, and Intel, found on investor relations pages or through the SEC EDGAR database
> - Industry reports from SEMI, Gartner, and IDC that provide market analysis and forecasts
> - Government responses, including US CHIPS Act implementation progress at commerce.gov, EU Chips Act at ec.europa.eu, and similar initiatives in Japan, South Korea, and Taiwan through their respective government portals
>
> Constraints:
> - Must reflect current state as of 2026 with prior issues clearly noted as such
>
> Other researchers in this run (do not research these):
> - Chip demand forecasts: demand by end market (AI, auto, consumer) through 2028
> - Equipment makers: ASML, Applied Materials and Tokyo Electron capacity and lead times
>
> Tool-call budget: 10
>
> Connected databases to search first: none
>
> Scientific evidence topic: no
>
> Save your output notes to {absolute path of your working directory}/research_notes/Semiconductor supply chain outlook 2026/semiconductor_supply_chain.md
>
> **As a first step, you must read {path_to_skill}/references/researcher.md for instructions on how to conduct research.**"

Researchers working in parallel cannot see each other, so give every researcher the list of its siblings' topics in the "Other researchers in this run" line. Without it, researchers whose topics touch repeat the same searches and send the report writer duplicate or conflicting facts. A researcher spawned in step 5 gets the full list too.

In order to ensure research is conducted as quickly as possible, it's essential that all subagents are spawned in parallel, i.e., that you make all your calls to the Agent tool in a single turn.

Each researcher replies with a short status report, not its notes (the format is in researcher.md). Do not open the notes files yourself. Collect every "Brief corrections" line the researchers report, and merge corrections that say the same thing into one line: step 6 passes them to the report writer, and you mention them in the summary in step 8. For each researcher, keep track of its topic, its notes path and the agent ID or name the Agent tool returned. Step 5 and later follow-up questions need them. Write them to {absolute path of your working directory}/research_notes/{research title}/agents.md, so they survive if your context is compacted. Start the file with one header line giving the user's original question, the depth level, whether verify is on, and the report path ({absolute path of your working directory}/reports/{research title}.md), then add one line per researcher (topic, notes path, agent ID or name). The file should make sense on its own to someone who has seen nothing else of this run.

### 5. [If absolutely necessary] Conduct one additional round of research

Skip this step at the Quick and Standard levels. At Deep or Exhaustive, based on the status reports returned by the research subagents (their "Critical gaps" lines), determine if there are any critical gaps that would make the report incomplete. A brief correction (their "Brief corrections" lines) that changes what another researcher should have covered also counts as a critical gap, because researchers run in parallel and that researcher worked from the wrong assumption. Do not redo its whole topic: send that researcher the correction and have it re-check only the findings that relied on the wrong assumption. Extra research delays delivery of the report to the user, leading to a much worse experience, so this must be used with extreme care.

Close each critical gap in the cheapest way available:

- **Gap inside an existing researcher's topic:** continue that researcher rather than starting a new one. It has already read the relevant sources, so it can go straight to the missing piece. Use the SendMessage tool (load it with ToolSearch first if it is deferred) with the agent ID or name you noted in step 4, and send:

  ```
  Follow-up: {the specific gap, as a question; for a brief correction, include the correction itself and ask it to re-check only the findings that relied on the old assumption}.
  Tool-call budget: {half the per-researcher limit for the level, rounded up}
  Save what you find to {absolute path of your working directory}/research_notes/{research title}/{topic} followup.md, in the same four-part format as your notes. Do not rewrite your original notes file.
  Then reply with the same short status report as before.
  ```

  Send all follow-ups in a single turn so they run in parallel.

- **Gap no existing researcher covered,** or SendMessage is not available, or the call fails: spawn a new researcher with the step 4 template, scoped to the gap only.

**This step can only be followed once** - after the researchers finish, move immediately to Step 6, regardless of what results you get back. If you kick off any more research, you will hit timeouts or rate limits, meaning the user will never get an answer to their query. **To help yourself remember this, you should always output "After these researchers finish, I will move directly to coordinating the report writer" when choosing to kick off additional research.**

### 6. Spawn foreground report writer subagent

**First, check the notes mechanically.** The report writer drops findings that have no source, so a researcher's formatting slip silently costs the report content. Run:

`python3 "{path_to_skill}/scripts/check_notes.py" "{absolute path of your working directory}/research_notes/{research title}"`

It prints "OK" or a short list of problems, each starting with the notes file it belongs to. Read only that output, never the notes.

- **OK:** continue.
- **Problems:** send each affected researcher (agent ID from agents.md) only its own lines with SendMessage, all in one turn: "Your notes file has these formatting problems: {lines}. Fix them in place in your original notes file: add any missing sections, and for each finding without a source, add its source link if you can find it in one or two tool calls, otherwise move it to Gaps. Change nothing else, then reply with the same short status report as before." This is the one case where a researcher edits its original notes file. Then run the check once more and continue whatever it says; never loop beyond that.
- **The script cannot run** (no Python, exit code 2, or any error), or SendMessage is unavailable: continue without mentioning it.

Then spawn a single report writer subagent. Use the Agent tool (named Task in some versions) with subagent_type="general-purpose" and run_in_background=false, set `model` only as described in "Models per role", and fill in the placeholders as in step 4. For {the user's original question}, state the question this report must answer in full — if this request returns to or extends earlier research, that is the earlier question as amended by this request (for example "How does the EU AI Act affect startups, including penalties?"), not just the follow-up message. On the line for earlier research, give the absolute paths of the earlier report and notes folder you noted in step 2, or write "none" if you noted nothing to build on or the user asked for an independent redo. Follow the exact format provided below:

```
Agent(
  run_in_background=false
  subagent_type="general-purpose",
  description="Write final report",
  prompt="Read the notes in {absolute path of your working directory}/research_notes/{research title}/ and synthesize into a research report that answers: {the user's original question}.

Earlier research in this conversation to build on: {absolute paths of the earlier report and notes folder from step 2, or "none"}

Brief corrections reported by researchers: {the "Brief corrections" lines from the researchers' status reports, merged where they repeat each other, or "none"}

Research depth: {the level, for example "1 Quick"; add "(default, no level was chosen)" if you fell back to Quick}

Scientific evidence topic: {yes or no}

Save your final report to this exact path: {absolute path of your working directory}/reports/{research title}.md

**As a first step, you must read {path_to_skill}/references/report-writer.md for instructions on how to write your research report.**"
)
```

Keep the agent ID or name the Agent tool returns for the report writer; the check below may need it.

**Check the report mechanically.** Some rules have an exact answer, so a script checks them instead of you or another subagent: every DOI, FDA number and clinical trial number is a hyperlink, every DOI link points to the DOI its text shows, no link has an empty or non-web target, and the depth level sits under the title. Run:

`python3 "{path_to_skill}/scripts/check_report.py" "{absolute path of your working directory}/reports/{research title}.md"`

It prints "OK" or a short list of problems with line numbers. Read only that output, never the report itself.

- **OK:** continue.
- **Problems:** send the list to the report writer with SendMessage, asking it to fix exactly those lines in the report in place and reply in its usual format. If SendMessage is unavailable or fails, spawn a new report writer as above with the report path and the list instead, telling it to fix only those lines. Then run the check once more. Never loop beyond that: if problems remain, deliver anyway and say in the summary how many formatting problems are left.
- **The script cannot run** (no Python, exit code 2, or any error): skip the check and continue without mentioning it.

**Then confirm the DOIs exist.** Run:

`python3 "{path_to_skill}/scripts/check_dois.py" "{absolute path of your working directory}/reports/{research title}.md"`

It looks every DOI in the report up in the DOI registry, so it catches invented or mistyped DOIs.

- **OK** (exit code 0): continue. Lines marked "could not check" are timeouts, not errors in the report; ignore them.
- **"not found" lines** (exit code 1): send them to the report writer with SendMessage: "These DOIs do not exist in the DOI registry: {lines}. For each, look up the article in the notes. If the notes give a different DOI for it, use that one; otherwise replace the DOI with "DOI not found" and keep the citation. Never guess a DOI. Change nothing else, and reply in your usual format." Then run the check once more, and if any DOI is still not found, say in the summary how many.
- **SKIPPED** (exit code 3, no network), or the script cannot run: continue without mentioning it.

### 7. [If verify is on] Fact-check the report

Skip this step unless verify is on (see "Verify mode"). Otherwise read {path_to_skill}/references/verify.md and follow it.

### 8. Deliver report to user

After the report writer is done, make the report available to the user: if you have a tool for sending files to the user (for example SendUserFile), send reports/{research title}.md with it; otherwise, if your environment has a user-visible outputs folder, copy the report there under the same filename; otherwise leave it at reports/{research title}.md. Then send the user a brief summary (aim for 3-5 sentences) that says where the full report is (sent to them, in the outputs folder, or its absolute path). Build the summary from the report writer's reply, which already carries one (see report-writer.md). If any researcher reported a brief correction, say so in one sentence, because it means the question itself assumed something that is not true. Open the report yourself only if that reply is missing, unclear, or says the report could not be saved (follow-up questions after delivery are the other exception, see references/follow-ups.md).

If step 7 ran, deliver reports/{research title} verification.md the same way, alongside the report, and add one sentence to the summary with the outcome (PASS, PARTIAL or FAIL) and the number of HIGH-WARN claims. Never describe a report as verified while a HIGH-WARN claim stands.

End the summary with this line, filled in: "Follow-up questions: ask here and I'll route them through jay-research (research files: {absolute path of your working directory}/research_notes/{research title}/)." It keeps a pointer to this run in the conversation itself, where it is more likely to survive if earlier context is compressed than the instructions in this file.

If the user later asks a follow-up question about this report, read {path_to_skill}/references/follow-ups.md before answering. If this skill was reloaded later in the conversation, find the run's folder from that line in your earlier summary and read its agents.md to recover the question, the report path and the researcher IDs. If there are several, use the run whose report the user is asking about, and ask if it's unclear.
