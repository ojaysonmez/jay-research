#!/usr/bin/env python3
"""Gap registry for jay-research: one table of open research gaps per project.

Usage:
  python3 gaps.py add   <registry.md> "<run title>" "<topic>" "<type>" "<gap>" "<where to look>"
  python3 gaps.py close <registry.md> <gap ID> "<run title>"
  python3 gaps.py keep  <registry.md> <gap ID> "<run title>" "<what was tried>" [<new type>]
  python3 gaps.py list  <registry.md> [--open] [--topic "<words>"]

add    Appends a gap with the next ID (G1, G2, ...) and status "open", creating the
       registry with its header if it does not exist. <type> is searchable, blocked
       or unpublished. Prints the new ID. If an open row already has the same topic
       and gap text (ignoring case and spacing), adds nothing and prints that row's ID
       followed by "(already open)", so repeated runs do not pile up duplicates.
close  Marks a gap "closed" and records which run closed it.
keep   Leaves a gap open and records the run that tried it and what was tried.
       With a new type (searchable, blocked or unpublished), also changes its type, for
       example a blocked gap whose blocker is gone but that still has no answer.
list   Prints the rows (only open ones with --open; only rows whose topic or gap
       contains all the given words with --topic), or "No gaps." when there are none.

The registry is a Markdown table in the research directory (open-gaps.md next to
research_notes/ and reports/), so it belongs to the project and can be committed with
it. Pipes and newlines in the text are escaped so the table stays intact.
Exit codes: 0 success, 1 unknown gap ID, 2 bad usage or file error. Standard library only.
"""
import os
import re
import sys

HEADER = (
    "# Open research gaps\n\n"
    "Written by jay-research (scripts/gaps.py). One row per gap a report could not close. "
    "Type: searchable (more searching could close it), blocked (needs a person: a browser, a PDF, "
    "an email) or unpublished (the data may not exist yet). A run asked to close gaps starts from "
    "the open rows and marks each one closed or still open.\n\n"
    "| ID | Status | Type | Topic | Gap | Where to look | Opened by | Last run |\n"
    "|----|--------|------|-------|-----|---------------|-----------|----------|\n"
)
TYPES = ("searchable", "blocked", "unpublished")


def clean(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def norm(text):
    """Comparable form of a topic or gap: no escapes, case or spacing differences."""
    return " ".join(str(text).replace("\\|", "|").lower().split())


def cells(line):
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip())[1:-1]]


def read(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def rows(lines):
    return [(i, cells(l)) for i, l in enumerate(lines) if re.match(r"^\| G\d+ \|", l)]


def write(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip("\n") + "\n")


def add(path, run, topic, kind, gap, where):
    kind = kind.strip().lower()
    if kind not in TYPES:
        print(f"type must be one of: {', '.join(TYPES)}")
        return 2
    lines = read(path)
    if not lines:
        lines = HEADER.rstrip("\n").split("\n")
    key = (norm(topic), norm(gap))
    for _, c in rows(lines):
        if c[1] == "open" and (norm(c[3]), norm(c[4])) == key:
            print(f"{c[0]} (already open)")
            return 0
    numbers = [int(c[0][1:]) for _, c in rows(lines)]
    gap_id = f"G{max(numbers, default=0) + 1}"
    lines.append(f"| {gap_id} | open | {kind} | {clean(topic)} | {clean(gap)} | {clean(where)} | {clean(run)} | {clean(run)} |")
    write(path, lines)
    print(gap_id)
    return 0


def update(path, gap_id, run, status, note=None, kind=None):
    if kind is not None:
        kind = kind.strip().lower()
        if kind not in TYPES:
            print(f"type must be one of: {', '.join(TYPES)}")
            return 2
    lines = read(path)
    for i, c in rows(lines):
        if c[0] == gap_id.upper():
            c[1] = status
            if kind:
                c[2] = kind
            c[7] = clean(run) + (f" (tried: {clean(note)})" if note else "")
            lines[i] = "| " + " | ".join(c) + " |"
            write(path, lines)
            print(f"{c[0]} {status}")
            return 0
    print(f"no gap {gap_id} in {path}")
    return 1


def list_rows(path, only_open, words):
    found = []
    for _, c in rows(read(path)):
        if only_open and c[1] != "open":
            continue
        text = (c[3] + " " + c[4]).lower()
        if all(w.lower() in text for w in words):
            found.append("| " + " | ".join(c) + " |")
    print("\n".join(found) if found else "No gaps.")
    return 0


def main():
    a = sys.argv[1:]
    try:
        if len(a) == 7 and a[0] == "add":
            return add(*a[1:])
        if len(a) == 4 and a[0] == "close":
            return update(a[1], a[2], a[3], "closed")
        if len(a) in (5, 6) and a[0] == "keep":
            return update(a[1], a[2], a[3], "open", a[4], a[5] if len(a) == 6 else None)
        if len(a) >= 2 and a[0] == "list":
            words = []
            if "--topic" in a:
                i = a.index("--topic")
                words = a[i + 1].split() if i + 1 < len(a) else []
            return list_rows(a[1], "--open" in a, words)
    except OSError as error:
        print(f"gap registry error: {error}")
        return 2
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
