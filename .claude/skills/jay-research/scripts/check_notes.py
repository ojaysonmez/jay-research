#!/usr/bin/env python3
"""Check researchers' notes files before the report writer reads them.

Usage: python3 check_notes.py <notes folder>

For every notes file in the folder (the researchers' {topic}.md and
{topic} followup.md files; agents.md, files starting with "_" such as the
run log, and the claims / verification batch files are skipped), checks the
rules in researcher.md that have an exact answer:

1. The file has at least one key-question section ("## ...").
2. Each key-question section has the four sub-sections: Takeaway, Cited
   Findings, Inferences and Gaps.
3. Every researcher that agents.md lists has a notes file in the folder
   (reported as "no notes saved" otherwise).
4. Every top-level finding under "Cited Findings", and every top-level line
   under the optional "## Leads for other topics", carries a source link (a
   Markdown link to a web address). Indented sub-bullets are detail under a
   finding and are not checked.

The report writer drops findings without a source, so a missing link here
silently costs the report content. Prints "OK: N notes files checked" and
exits 0, or prints one line per problem, grouped by file, and exits 1.
Exits 2 if the folder cannot be read. Uses only the standard library.
"""

import os
import re
import sys

REQUIRED = ["Takeaway", "Cited Findings", "Inferences", "Gaps"]
LEADS = "leads for other topics"
# agents.md, the run log (_run.md), the merged records table (_records.md) and
# the verify-mode batch files are not researcher notes.
SKIP = re.compile(r"^(_.*|agents|claims batch \d+|verification batch \d+)\.md$", re.I)
SOURCE_LINK = re.compile(r"\[[^\]]+\]\(https?://[^)\s]+")
# Only top-level bullets are findings. Indented sub-bullets are detail under a
# finding, and the source link belongs on the finding itself.
BULLET = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.*)$")
MAX_LINES = 40


NOTES_PATH = re.compile(r"research_notes[/\\][^/\\\n]+[/\\]([^/\\\n`|]*?\.md)", re.I)


def expected_notes(folder):
    """File names of the notes agents.md lists, so a researcher that saved
    nothing (budget hit, crash, cut-off reply) is noticed. The first line of
    agents.md is the run header, not a researcher. Returns [] if agents.md is
    missing or lists no notes paths."""
    try:
        with open(os.path.join(folder, "agents.md"), encoding="utf-8") as f:
            lines = f.read().splitlines()[1:]
    except OSError:
        return []
    found = []
    for line in lines:
        for name in NOTES_PATH.findall(line):
            if not SKIP.match(name) and name not in found:
                found.append(name)
    return found


def shorten(text, limit=80):
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def sourced(lines, i):
    """True if the top-level bullet at lines[i] carries a source link, either
    on its own line or, for a header-style bullet ending in a colon, on one of
    the indented sub-bullets that follow it."""
    if SOURCE_LINK.search(lines[i]):
        return True
    if not lines[i].rstrip().endswith(":"):
        return False
    for line in lines[i + 1:]:
        if line[:1] not in (" ", "\t"):
            break
        if SOURCE_LINK.search(line):
            return True
    return False


def check_file(path):
    """Return a list of problem strings for one notes file."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    problems = []
    questions = []  # (title, {subsection: [lines]})
    leads = None
    current_q = None
    current_sub = None
    in_fence = False

    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            title = line[3:].strip()
            if title.lower() == LEADS:
                leads, current_q, current_sub = [], None, None
            else:
                current_q = (title, {})
                questions.append(current_q)
                leads, current_sub = None, None
            continue
        if line.startswith("### ") and current_q is not None:
            name = line[4:].strip()
            match = next((r for r in REQUIRED if name.lower().startswith(r.lower())), None)
            current_sub = match
            if match:
                current_q[1].setdefault(match, [])
            continue
        if leads is not None:
            leads.append(line)
        elif current_q is not None and current_sub:
            current_q[1][current_sub].append(line)

    if not questions:
        problems.append("no key-question sections ('## ...') found")

    for title, subs in questions:
        missing = [r for r in REQUIRED if r not in subs]
        if missing:
            problems.append(f"'{shorten(title, 60)}' is missing: {', '.join(missing)}")
        findings = subs.get("Cited Findings", [])
        for i, line in enumerate(findings):
            m = BULLET.match(line)
            if m and not sourced(findings, i):
                problems.append(f"'{shorten(title, 40)}' finding without a source link: {shorten(m.group(1))}")

    leads = leads or []
    for i, line in enumerate(leads):
        m = BULLET.match(line)
        if m and not sourced(leads, i):
            problems.append(f"lead without a source link: {shorten(m.group(1))}")

    return problems


def main():
    if len(sys.argv) != 2:
        print("usage: check_notes.py <notes folder>")
        return 2
    folder = sys.argv[1]
    try:
        names = sorted(n for n in os.listdir(folder) if n.endswith(".md") and not SKIP.match(n))
    except OSError as error:
        print(f"cannot read folder: {error}")
        return 2

    report = [f"{name}: no notes saved (listed in agents.md, file not found)"
              for name in expected_notes(folder) if name not in names]
    if not names and not report:
        print(f"no notes files in {folder}")
        return 1

    for name in names:
        try:
            problems = check_file(os.path.join(folder, name))
        except OSError as error:
            problems = [f"cannot read: {error}"]
        report += [f"{name}: {p}" for p in problems]

    if not report:
        print(f"OK: {len(names)} notes files checked")
        return 0
    print(f"{len(report)} problem(s) in {len(names)} notes files:")
    for line in report[:MAX_LINES]:
        print(line)
    if len(report) > MAX_LINES:
        print(f"... and {len(report) - MAX_LINES} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
