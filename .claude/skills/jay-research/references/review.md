# Notes review

The coordinator reads this file only when notes review is on (see "Notes review" in SKILL.md), in step 6, after the notes checks and the records merge and before the report writer.

Two reviewers each read all the notes on their own and write their items (round 1). Then you resume each of them once with the path of the other's file, and each cross-checks the other's items (round 2). You pass file paths only. You never read the notes or the review files, and you never copy content from one reviewer to the other.

Fill in the placeholders as in step 4 of SKILL.md.

## Roles and budget

| Role | Looks for | File |
|---|---|---|
| conflicts | findings in different notes files that contradict each other; findings that rest on different assumptions; topics that should connect but do not | `_review conflicts.md` |
| evidence | important findings that rest on one weak source, outdated data, a preprint or press release presented as established, an inference presented as a finding, or an identifier that does not fit what the notes say it points to | `_review evidence.md` |

Tool-call budget per reviewer: 12 at Standard and Deep, 16 at Max, covering both rounds. Both files start with `_`, so check_notes.py skips them.

## a. Round 1: spawn both reviewers in one turn

Log `review start`, then make both calls in a single turn so they run in parallel, with `model` as in "Models per role":

```
Agent(
  run_in_background=false
  subagent_type="general-purpose",
  description="Review notes: {conflicts or evidence}",
  prompt="You are the {conflicts or evidence} reviewer, one of two reviewers checking the research notes in {absolute path of your working directory}/research_notes/{research title}/ before a report writer turns them into a report that answers: {the user's original question}. The other reviewer looks for {the other role's 'Looks for' text}, so leave that to it.

Your job: look for {the 'Looks for' text for your role}.

Research depth: {the level}
Tool-call budget: {12 or 16}, for this round and one later cross-check round together. Keep at least 3 calls for the cross-check.
Scientific evidence topic: {yes or no}
Your file: {absolute path of your working directory}/research_notes/{research title}/{your file name}

Rules:
- Work only from the notes files in that folder: every .md file except agents.md, files starting with "_", and files starting with "claims batch" or "verification batch". Do not search the web or use connectors. Never invent findings or sources.
- Read all the notes. Then write your file with a "## Items" section, one item per line in this form: "{C or E}{number} | {type} | {notes file}: {finding} | {the issue, one sentence} | {suggested handling}". Use C for the conflicts reviewer and E for the evidence reviewer. Types: contradiction, assumption, missing link (conflicts); weak source, outdated, inference as fact, identifier (evidence). At most 15 items, most important first. If you find nothing, write "none" under the heading.

Reply with exactly one line and nothing else: "{conflicts or evidence}: items {number}, tool calls {used} of {budget}"."
)
```

Keep each reviewer's agent ID or name, and add them to agents.md as two more lines (role, file path, agent ID or name), so they survive if your context is compacted.

## b. Round 2: cross-check

Once both have replied, send each reviewer the other's file path with SendMessage (load it with ToolSearch first if it is deferred), both in a single turn so they run in parallel:

```
Cross-check round. Read the other reviewer's file at {absolute path of the other review file}. Do not search for anything new.

In your own file, add a "## Cross-check" section with one line per item of theirs you have a view on: "{their item ID}: agree", "{their item ID}: disagree, {reason}" or "{their item ID}: duplicate of {your item ID}". Items you do not mention count as agreed. If their file convinced you to drop one of your own items, add a line "withdraw {your item ID}, {reason}". Change nothing else in your file.

Reply with exactly one line and nothing else: "{your role}: disagree {number}, duplicate {number}, withdrawn {number}".
```

This is the only round 2. Never send a third message to a reviewer, even if the two disagree: the report writer settles disagreements.

## c. Hand over

Check only that the review files exist, for example with `ls`, without opening them. Put the paths of the files that exist on the report writer's "Notes review" line, or "none" if neither does. Log `review end` with the numbers from the reviewers' replies.

## Failures

Handle each case once, never in a loop, and record it as SKILL.md's failure rule describes, with a `fallback` event:

- **A reviewer's round 1 reply is missing or its file was not saved:** pass on only the other file, skip round 2 for both, and log "cross-check none".
- **SendMessage is unavailable or fails in round 2:** spawn one new subagent per reviewer instead, with the round 2 message as its prompt plus the line "Your own file is at {its path}; its round 1 author is no longer available." Give each a budget of 4 tool calls.
- **A round 2 reply is missing, or it repeats the round 1 reply instead of reporting the cross-check:** keep that file as it is and log "cross-check partial". The report writer treats the other reviewer's items as agreed.
