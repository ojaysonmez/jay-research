# Ideas not built yet

Ideas discussed but not implemented. Move one to `suggested-changes.md` (or build it) when you pick it up, and delete it from here.

## jay-decide (a separate skill)

A team of agents (moderator, devil's advocate, role-based members) debates a decision using the notes of a jay-research run, and produces a DOCX decision record.

- First test: a rehearsal of a 510(k) vs De Novo regulatory pathway decision.
- First check whether agent teams work in the environment at all.

## Report-matches-records check

A script that compares the report's comparison table with `_records.json`, so a value the report writer changed or dropped is caught mechanically. It would sit next to `scripts/check_report.py` and run in step 6 in structured mode.

## DOCX output for reports

Deliver the report as a DOCX as well as Markdown. DOCX is the preferred format.

## Copyright rule in the project repo's CLAUDE.md (other repo)

The project repo's `CLAUDE.md` bans storing copyrighted full texts. Suggested relaxation: allow storing open-licence and public-domain full texts (PMC open access, FDA and CMS documents); for paywalled papers store notes, short quotes and the DOI only. Not edited yet, and the change belongs in that repo, not this one.
