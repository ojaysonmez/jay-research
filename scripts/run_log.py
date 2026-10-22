#!/usr/bin/env python3
"""Keep a timestamped run log for a jay-research run.

Usage:
  python3 run_log.py <notes folder> event "<stage>" "<detail>"
  python3 run_log.py <notes folder> summary

"event" appends one line to <notes folder>/_run.md with the current UTC time,
so timestamps come from the clock rather than being written by a model.
Stages that should be timed come in pairs named "<name> start" and
"<name> end" (for example "research start" / "research end"). Any other
stage name is logged as a single event.

"summary" prints the duration of every start/end pair, the total time from
the first event to the last, and the single events in order. Durations are
computed here because models get time arithmetic wrong.

Exit codes: 0 success, 2 bad usage or file error. Uses only the standard
library.
"""

import datetime
import os
import sys

HEADER = (
    "# Run log\n\n"
    "Written by scripts/run_log.py. Times are UTC.\n\n"
    "| Time | Stage | Detail |\n"
    "|------|-------|--------|\n"
)
FMT = "%Y-%m-%dT%H:%M:%SZ"


def log_path(folder):
    return os.path.join(folder, "_run.md")


def add_event(folder, stage, detail):
    path = log_path(folder)
    now = datetime.datetime.now(datetime.timezone.utc).strftime(FMT)
    clean = lambda text: text.replace("|", "/").replace("\n", " ").strip()
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(HEADER)
        f.write(f"| {now} | {clean(stage)} | {clean(detail)} |\n")
    print(f"logged {now} {stage}")


def read_events(folder):
    events = []
    with open(log_path(folder), encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 3:
                continue
            try:
                when = datetime.datetime.strptime(parts[0], FMT)
            except ValueError:
                continue
            events.append((when, parts[1], " | ".join(parts[2:])))
    return events


def minutes(delta):
    seconds = int(delta.total_seconds())
    return f"{seconds // 60}m {seconds % 60:02d}s"


def summary(folder):
    events = read_events(folder)
    if not events:
        print("no events logged")
        return
    opened = {}
    timed, single = [], []
    for when, stage, detail in events:
        low = stage.lower()
        if low.endswith(" start"):
            opened[low[:-6]] = (when, stage[:-6])
        elif low.endswith(" end") and low[:-4] in opened:
            start, name = opened.pop(low[:-4])
            timed.append((start, name, when - start, detail))
        else:
            single.append((when, stage, detail))

    total = events[-1][0] - events[0][0]
    print(f"Total: {minutes(total)} ({events[0][0].strftime(FMT)} to {events[-1][0].strftime(FMT)})")
    if timed:
        print("Timed stages:")
        for start, name, delta, detail in sorted(timed):
            share = f", {delta / total:.0%} of total" if total.total_seconds() else ""
            print(f"- {name}: {minutes(delta)}{share}" + (f" ({detail})" if detail else ""))
    for name, (start, label) in opened.items():
        print(f"- {label}: started {start.strftime(FMT)}, no end logged")
    if single:
        print("Events:")
        for when, stage, detail in single:
            print(f"- {when.strftime('%H:%M:%S')} {stage}" + (f": {detail}" if detail else ""))


def main():
    args = sys.argv[1:]
    try:
        if len(args) == 4 and args[1] == "event":
            add_event(args[0], args[2], args[3])
        elif len(args) == 2 and args[1] == "summary":
            summary(args[0])
        else:
            print(__doc__.split("\n\n")[1])
            return 2
    except OSError as error:
        print(f"run log error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
