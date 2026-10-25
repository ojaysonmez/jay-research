#!/usr/bin/env python3
"""Append one failure to the repository's failure-log.md.

Usage:
  python3 log_failure.py "<run title>" "<stage>" "<what failed>" "<what was done>" "<outcome>"

Adds a row (with today's date) to failure-log.md at the root of the repository
that holds this skill, four levels above this script. The row is
written the moment a failure happens, so a run that dies before its end-of-run
steps still leaves a record, once the file is committed. Pipes and newlines in
the text are escaped so the table stays intact.

If failure-log.md does not exist (the skill is installed somewhere else), it
prints "skipped" and exits 0, because logging must never hold up a run.
Exit codes: 0 success or skipped, 2 bad usage. Uses only the standard library.
"""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", "failure-log.md"))


def clean(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def main():
    if len(sys.argv) != 6:
        print(__doc__)
        return 2
    if not os.path.isfile(LOG):
        print("skipped: no failure-log.md at the repository root")
        return 0
    row = "| {} | {} |\n".format(
        datetime.date.today().isoformat(), " | ".join(clean(a) for a in sys.argv[1:]))
    try:
        with open(LOG, "rb") as f:
            data = f.read()
        needs_newline = bool(data) and not data.endswith(b"\n")
        with open(LOG, "a", encoding="utf-8") as f:
            if needs_newline:
                f.write("\n")
            f.write(row)
    except OSError as error:
        print(f"skipped: cannot write failure-log.md: {error}")
        return 0
    print("logged to failure-log.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
