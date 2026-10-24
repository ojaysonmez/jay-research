#!/usr/bin/env python3
"""Score jay-research runs against known answers.

Usage:
  python3 score.py records <case id> <records.json | notes folder>
  python3 score.py verify  <seeded.json> <verification.md>

records  Checks a run's merged records (the _records.json that
         scripts/records.py merge writes) against the expected values for
         one case in cases.json. An expectation is matched to the record
         whose key field contains the item name (ignoring case). Each
         expectation is reported as PASS, WRONG (the record has a different
         value) or MISSING (no such record, or the value is null). Exit code
         0 if everything passes, 1 otherwise.
verify   Checks a verification file ('... verification.md', written by
         scripts/merge_verification.py) against the errors seeded into a
         report. A seeded error counts as caught when its marker text appears
         in the HIGH-WARN or MED-WARN claims. The outcome must also be FAIL.
         Exit code 0 if all are caught and the outcome is FAIL, 1 otherwise.

Uses only the standard library.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_record(records, item):
    item = item.lower()
    for record in records:
        key = next(iter(record.values()), "")
        if item in str(key).lower():
            return record
    return None


def check(expect, record):
    """Return (status, detail) for one expectation against one record."""
    if record is None:
        return "MISSING", "no record for this item"
    value = record.get(expect["field"])
    if value is None:
        return "MISSING", "value is null or the field is absent"
    if "number" in expect:
        try:
            number = float(re.search(r"-?\d+(?:\.\d+)?", str(value)).group())
        except (AttributeError, ValueError):
            return "WRONG", f"got {value!r}, not a number"
        tolerance = expect.get("tolerance", 0)
        if abs(number - expect["number"]) <= tolerance:
            return "PASS", f"{value}"
        return "WRONG", f"got {value}, expected {expect['number']} (tolerance {tolerance})"
    if "contains" in expect:
        if str(expect["contains"]).lower() in str(value).lower():
            return "PASS", f"{value}"
        return "WRONG", f"got {value!r}, expected it to contain {expect['contains']!r}"
    return "WRONG", "expectation has neither 'number' nor 'contains'"


def score_records(case_id, target):
    case = next((c for c in load(os.path.join(HERE, "cases.json"))["cases"] if c["id"] == case_id), None)
    if case is None:
        print(f"no case {case_id!r} in cases.json")
        return 2
    path = os.path.join(target, "_records.json") if os.path.isdir(target) else target
    try:
        records = load(path)
    except (OSError, ValueError) as error:
        print(f"cannot read records: {error}")
        return 2

    counts = {"PASS": 0, "WRONG": 0, "MISSING": 0}
    print(f"case {case_id} ({case['status']}), {len(case['expected'])} expectations")
    for expect in case["expected"]:
        status, detail = check(expect, find_record(records, expect["item"]))
        counts[status] += 1
        print(f"{status:7} {expect['item']} / {expect['field']}: {detail}")
    total = len(case["expected"])
    print(f"score: {counts['PASS']}/{total} pass, {counts['WRONG']} wrong, {counts['MISSING']} missing")
    if case["status"] != "confirmed":
        print("note: this case is a draft, so the expected values are not independently confirmed")
    return 0 if counts["PASS"] == total else 1


def flagged_text(text):
    """The text of the HIGH-WARN and MED-WARN claims in a merged verification file."""
    parts = []
    section = re.search(r"## High-risk claims.*?(?=\n## )", text, re.S)
    if section:
        parts.append(section.group())
    for row in text.splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if row.lstrip().startswith("|") and cells and cells[-1].upper() in ("HIGH-WARN", "MED-WARN"):
            parts.append(row)
    return "\n".join(parts).lower()


def score_verify(seeded_path, verification_path):
    try:
        seeded = load(seeded_path)
        with open(verification_path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, ValueError) as error:
        print(f"cannot read: {error}")
        return 2

    flagged = flagged_text(text)
    outcome = re.search(r"\*\*Outcome:\*\*\s*(\w+)", text)
    outcome = outcome.group(1) if outcome else "unknown"
    caught = 0
    for error in seeded["errors"]:
        hit = error["marker"].lower() in flagged
        caught += hit
        print(f"{'CAUGHT' if hit else 'MISSED':7} {error['id']} {error['what']} (seeded {error['wrong']!r}, right {error['right']!r})")
    total = len(seeded["errors"])
    print(f"outcome: {outcome} (expected FAIL)")
    print(f"score: {caught}/{total} seeded errors caught")
    return 0 if caught == total and outcome == "FAIL" else 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "records":
        return score_records(sys.argv[2], sys.argv[3])
    if len(sys.argv) == 4 and sys.argv[1] == "verify":
        return score_verify(sys.argv[2], sys.argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
