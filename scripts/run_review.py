#!/usr/bin/env python3
"""Spot abnormalities in a jay-research run, and patterns across runs.

Usage:
  python3 run_review.py review   <notes folder>
  python3 run_review.py record   <notes folder> [--history PATH]
  python3 run_review.py patterns [--history PATH]

review    Reads the run log (<notes folder>/_run.md, written by run_log.py;
          researcher results come from the single "research end" event)
          and applies fixed thresholds. Prints "No abnormalities." or one
          "FLAG <kind>: <detail>" line per finding. The coordinator turns
          each flag into a suggested change to the skill; it never edits
          the skill itself.
record    Appends one line for this run to the history file (default
          ~/.jay-research/history.md, or the JAY_RESEARCH_HISTORY
          environment variable, or --history) and prints that line.
patterns  Reads the history file and reports flags that keep recurring:
          a flag kind is reported when it appears in at least 2 runs and in
          at least half of the runs at that depth level.

The history file holds run titles, so it may name confidential topics.
Keep it out of any public repository.

Thresholds (review):
  budget-hit      a researcher used its whole tool-call budget and still
                  reported a critical gap (using the whole budget alone is
                  normal and is not flagged; the count is self-reported)
  slow-stage      a stage other than research (report, checks, gap round,
                  verify) took over 40% of a run of 10+ minutes
  unfinished      a stage was started but never ended
  check-unfixed   a check still reported problems after its fix round
  fallback        a fallback path ran (SendMessage, a script, the merger)
  doi-not-found   the DOI check found DOIs that do not exist
  brief-wrong     researchers reported brief corrections (a question issue,
                  not a skill issue; recorded for the patterns)

Exit codes: 0 success (review: no flags), 1 review found flags, 2 bad usage
or file error. Uses only the standard library.
"""

import datetime
import os
import re
import sys

FMT = "%Y-%m-%dT%H:%M:%SZ"
DEPTHS = ["Quick", "Standard", "Deep", "Exhaustive"]
HISTORY_HEADER = (
    "# jay-research run history\n\n"
    "One line per run, written by scripts/run_review.py. May name confidential "
    "topics: keep this file out of public repositories.\n\n"
    "| Date | Title | Depth | Minutes | Researchers | Budget hits | Flags |\n"
    "|------|-------|-------|---------|-------------|-------------|-------|\n"
)
TOOL_CALLS = re.compile(r"(\d+)\s*(?:of|/)\s*(\d+)")
CRITICAL_GAPS = re.compile(r"critical gaps?:\s*(none|\d+)", re.I)
REMAIN = re.compile(r"(\d+)\s+remain", re.I)
NOT_FOUND = re.compile(r"(\d+)\s+not found", re.I)


def history_path(args):
    if "--history" in args:
        i = args.index("--history")
        if i + 1 < len(args):
            return os.path.expanduser(args[i + 1])
    return os.path.expanduser(os.environ.get("JAY_RESEARCH_HISTORY", "~/.jay-research/history.md"))


def read_events(folder):
    events = []
    with open(os.path.join(folder, "_run.md"), encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 3:
                continue
            try:
                when = datetime.datetime.strptime(parts[0], FMT)
            except ValueError:
                continue
            events.append((when, parts[1].lower(), " | ".join(parts[2:])))
    return events


def analyse(events):
    """Return (flags, facts) for one run. flags: list of (kind, detail)."""
    flags = []
    facts = {"researchers": 0, "budget_hits": 0, "depth": "?", "minutes": 0}
    if not events:
        return flags, facts

    total = (events[-1][0] - events[0][0]).total_seconds()
    facts["minutes"] = round(total / 60)
    opened, timed = {}, []

    for when, stage, detail in events:
        if stage == "run start":
            depth = next((d for d in DEPTHS if d.lower() in detail.lower()), None)
            facts["depth"] = depth or "?"
        if stage == "research end":
            # One segment per researcher: "{topic} {used} of {budget}, critical gaps: {n|none}".
            for segment in detail.split(";"):
                if segment.strip().lower().startswith("gap round"):
                    continue
                m = TOOL_CALLS.search(segment)
                if not m:
                    continue
                facts["researchers"] += 1
                used, budget = int(m.group(1)), int(m.group(2))
                if used < budget:
                    continue
                facts["budget_hits"] += 1
                # Using the whole budget is normal; it only matters when the
                # researcher also says something critical is still missing.
                g = CRITICAL_GAPS.search(segment)
                if g and g.group(1).lower() not in ("none", "0"):
                    flags.append(("budget-hit", f"{segment.strip()} (whole budget used, critical gap left)"))
        if stage.endswith(" start"):
            opened[stage[:-6]] = when
        elif stage.endswith(" end") and stage[:-4] in opened:
            timed.append((stage[:-4], (when - opened.pop(stage[:-4])).total_seconds()))
        if stage.endswith(" check"):
            m = REMAIN.search(detail)
            if m and int(m.group(1)) > 0:
                flags.append(("check-unfixed", f"{stage}: {detail}"))
            if stage == "doi check":
                m = NOT_FOUND.search(detail)
                if m and int(m.group(1)) > 0:
                    flags.append(("doi-not-found", detail))
        elif stage == "fallback":
            flags.append(("fallback", detail))
        elif stage == "brief corrections":
            m = re.match(r"\s*(\d+)", detail)
            if not m or int(m.group(1)) > 0:
                flags.append(("brief-wrong", detail))

    for name, seconds in timed:
        # Research normally takes most of a run, so only other stages count.
        if name not in ("run", "research") and total >= 600 and seconds > total * 0.4:
            flags.append(("slow-stage", f"{name} took {round(seconds / 60)} of {round(total / 60)} minutes"))
    for name in opened:
        if name != "run":
            flags.append(("unfinished", f"{name} was started but never ended"))
    return flags, facts


def review(folder):
    flags, _ = analyse(read_events(folder))
    if not flags:
        print("No abnormalities.")
        return 0
    for kind, detail in flags:
        print(f"FLAG {kind}: {detail}")
    return 1


def record(folder, path):
    events = read_events(folder)
    flags, facts = analyse(events)
    title = os.path.basename(os.path.normpath(folder)).replace("|", "/")
    date = events[0][0].strftime("%Y-%m-%d") if events else datetime.date.today().isoformat()
    kinds = sorted({k for k, _ in flags})
    line = (f"| {date} | {title} | {facts['depth']} | {facts['minutes']} | {facts['researchers']} | "
            f"{facts['budget_hits']} | {', '.join(kinds) or 'none'} |")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(HISTORY_HEADER)
        f.write(line + "\n")
    print(line)
    return 0


def patterns(path):
    runs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) != 7 or not re.match(r"\d{4}-\d{2}-\d{2}$", parts[0]):
                continue
            kinds = [] if parts[6] == "none" else [k.strip() for k in parts[6].split(",")]
            runs.append({"depth": parts[2], "minutes": parts[3], "kinds": kinds})
    if not runs:
        print("No runs recorded yet.")
        return 0

    print(f"{len(runs)} run(s) recorded.")
    found = False
    for depth in DEPTHS + ["?"]:
        at_depth = [r for r in runs if r["depth"] == depth]
        if not at_depth:
            continue
        counts = {}
        for r in at_depth:
            for k in set(r["kinds"]):
                counts[k] = counts.get(k, 0) + 1
        for kind, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            if n >= 2 and n * 2 >= len(at_depth):
                found = True
                print(f"PATTERN {kind}: {n} of {len(at_depth)} {depth} runs")
    if not found:
        print("No recurring issues (a pattern needs at least 2 runs and half of the runs at one depth).")
    return 0


def main():
    args = sys.argv[1:]
    try:
        if len(args) >= 2 and args[0] == "review":
            return review(args[1])
        if len(args) >= 2 and args[0] == "record":
            return record(args[1], history_path(args))
        if args and args[0] == "patterns":
            path = history_path(args)
            if not os.path.exists(path):
                print(f"No history file at {path} yet.")
                return 0
            return patterns(path)
    except OSError as error:
        print(f"run review error: {error}")
        return 2
    print(__doc__.split("\n\n")[1])
    return 2


if __name__ == "__main__":
    sys.exit(main())
