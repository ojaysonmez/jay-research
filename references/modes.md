# Help and dry-run modes

The coordinator reads this file only when a request asks for help or for a dry run. Neither mode researches anything. Step numbers refer to the Process section of SKILL.md.

## Help mode

If the request is "help" (for example "/jay-research help"), do not research. Reply with: the four depth levels (the "Research depth" table in SKILL.md), how to request one ("/jay-research deep: <question>"), the default (Quick), how to choose a model (by default every subagent uses the main chat's model; add "use Sonnet" for a faster run, or name one model per role, for example "Sonnet for researchers, Opus for the report"), how to preview a plan without running it ("/jay-research dry-run: <question>", or with a level, "/jay-research dry-run deep: <question>", then "go" to run it), how to fact-check the finished report ("/jay-research deep verify: <question>"; off unless requested), and the rules the skill follows (connector-first sourcing, DOIs only for scientific and clinical topics, DOI, FDA and clinical trial numbers always shown as hyperlinks, URLs for other sources, report delivered as a Markdown file). Then stop.

## Dry-run mode

If the request asks for a dry run (for example "/jay-research dry-run: <question>", "dry run" or "plan only"), plan the research but do not carry it out. Work through steps 1 to 3 on paper only: create no folders, spawn nothing, and ask no follow up questions. Then reply with:

1. The question as you understand it, and what you treat as in and out of scope
2. The follow up questions you would have asked in step 1, each with the answer you would assume if nobody replied
3. The depth level you would use, the title you would choose, and whether you would treat it as a scientific evidence topic (which decides whether DOIs are collected)
4. A table of the researchers you would start: topic, objective, key questions, suggested sources, tool-call budget
5. The budget in numbers: subagents in total (researchers, the report writer, and the verification subagents if verify is on), the model each role would use, the most tool calls the researchers could make between them (researchers × tool calls each), and the level's time estimate
6. Whether step 5 could apply at this level, and how many follow-up tool calls it could add (step 5 continues existing researchers rather than starting new ones where it can)
7. What the report would look like at this level

End by telling the user they can reply "go" to run this plan as shown, or reply with changes. On "go", run the full process using this plan, with any changes the user gave. Then stop.

If verify is on, say so in the plan, and say that it adds roughly the time of one research round.
