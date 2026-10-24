# Structured mode: comparison records

The coordinator reads this file only when structured mode is on (see "Structured mode" in SKILL.md). Placeholders and step numbers refer to SKILL.md.

In structured mode, researchers keep writing their normal notes, and also write one structured record per item they cover: one company, product, device, paper, trial or person. A script checks the records and merges them into one comparison table for the report writer. The notes keep everything that does not fit a field.

## 1. Choose the fields (step 3)

Choose one key field and up to 8 other fields, the same for every researcher.

- **Key field:** the item's name, for example "company", "device" or "trial".
- **Other fields:** the facts the user needs to compare the items. Prefer facts that can be checked against a source (status, identifiers, dates, amounts, yes/no answers) over opinions. Put the unit in the field name ("funding USD", "enrolment n"). Allow at most one judgement field, such as a fit score, and state its scale and rule in its name ("fit 1-5").
- **Identifiers** (DOI, FDA number, NCT number) go in their own fields as plain text. The report writer turns them into links.
- **"sources"** is always added: every record lists the links that support it.

Then record the fields with:

`python3 "{path_to_skill}/scripts/records.py" init "{absolute path of your working directory}/research_notes/{research title}" "<key field>" "<field>, <field>, ..."`

It prints the final field list. Use that exact list in the briefs. In dry-run mode, show the proposed fields in the plan and do not run the script.

## 2. Brief the researchers (step 4)

Only researchers whose topic covers items get records. For them, fill the brief's "Structured records" line with the field list and the path {absolute path of your working directory}/research_notes/{research title}/{topic}.records.json. For the others (for example a researcher on regulation or reimbursement in general), write "none".

## 3. Check and merge (step 6, after the notes check)

Run:

`python3 "{path_to_skill}/scripts/records.py" check "{absolute path of your working directory}/research_notes/{research title}"`

It prints "OK" or a short list of problems, each starting with the records file it belongs to. Read only that output.

- **OK:** continue.
- **Problems:** send each affected researcher only its own lines with SendMessage, all in one turn: "Your records file has these problems: {lines}. Fix them in place: add missing fields, using null where you searched and found nothing, and give each record its source links. For an identifier that does not appear in your notes, add it to your notes with its source, or set the value to null; never keep an identifier you cannot source. If a value cannot be found in one or two tool calls, set it to null. Change nothing else, then reply with the same short status report as before." Run the check once more and continue whatever it says.
- **An identifier "does not appear in your notes":** treat it like the other problems. The researcher either adds the identifier to its notes with the source it came from, or sets the value to null. This keeps a number that has no source behind it out of the table.
- **The OK line names researchers with "no records file for: …":** if it names a researcher you briefed with a records path, ask that researcher with SendMessage to write the file, then run the check again. Researchers you briefed with "none" are expected there.
- **The script cannot run**, or exits with code 4 (no records): continue without records.

Then merge:

`python3 "{path_to_skill}/scripts/records.py" merge "{absolute path of your working directory}/research_notes/{research title}" "{absolute path of your working directory}/research_notes/{research title}/_records.md"`

It matches items that two researchers both covered, fills gaps from either, keeps conflicting values side by side, and prints one summary line. Give the report writer the path of `_records.md` on its "Comparison records" line. Log the check result as "records {result}" in the `report end` event, as for the other checks.

If merging fails, give the report writer "none" and continue.

## 4. Later

The records stay in the notes folder. For a follow-up question that compares items ("which partners have a CGM input?"), search `_records.md` first, the same way as the report.
