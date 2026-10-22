# Follow-up questions after delivery

The coordinator reads this file only when the user asks a follow-up question about a report already delivered in this conversation. Placeholders and step numbers refer to SKILL.md.

After a report has been delivered in this conversation, the user may ask about it ("why did X rank first?", "dig deeper into Y"). Route each follow-up to the cheapest path that can answer it:

0. **It is about the run itself** (how long it took, which stage was slowest, how many tool calls were used, whether a check fired or a fix round ran). Run `python3 "{path_to_skill}/scripts/run_log.py" "{the run's notes folder}" summary` and answer from its output, reading _run.md in that folder for anything the summary leaves out. Never compute durations yourself: the summary already gives each stage's time and share of the total. If there is no _run.md, say the run was not logged. For abnormalities and suggested skill changes, run `python3 "{path_to_skill}/scripts/run_review.py" review "{the run's notes folder}"` and include the run log's `observation` events.

   Questions across runs ("what keeps going wrong?", "is the skill getting faster?") are answered from the run history: run `python3 "{path_to_skill}/scripts/run_review.py" patterns` and answer from its output. For each PATTERN line, suggest one concrete change to the skill, but do not edit it; the user decides.

1. **The report already answers it.** Answer directly, without subagents. Search the report (and, if needed, the notes of the one topic involved) for the relevant passage rather than reading everything, and cite the sources the report cites. If you are not sure whether the user wants new research, answer from the report first and offer to dig deeper.

2. **It needs more research inside one or more existing researchers' topics.** Continue those researchers instead of starting new ones, since they have already read the relevant sources. Choose a title as in step 2's "returning to an earlier topic" case and create its notes folder (never write into the earlier folder). Then send each researcher, via SendMessage with the agent ID or name from the agents.md file you wrote in step 4 of SKILL.md (read it back first; if you no longer have the research folder path, take it from the "research files:" line in your earlier summary), all in one turn:

   ```
   Follow-up: {the user's question, as it applies to your topic}.
   Tool-call budget: {half the per-researcher limit for the original level, rounded up}
   Save what you find to {absolute path of your working directory}/research_notes/{new research title}/{topic} followup.md, in the same four-part format as your notes.
   Then reply with the same short status report as before.
   ```

   Answer the user from those follow-up files, with their sources, and offer an updated report. If they want one, spawn the report writer as in step 6 with the new title, passing the earlier report and notes folder as earlier research to build on. Verification (step 7) runs on that updated report only if the user asks for it again.

3. **It needs a topic no researcher covered, this is a different conversation, or SendMessage is unavailable or fails.** Run the full process as an extension of the earlier research (step 2's "returning to an earlier topic" case), at the original depth level unless the user names another.

Continuing a researcher only works within the conversation where it was spawned, because only that conversation holds its agent ID.
