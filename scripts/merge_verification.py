#!/usr/bin/env python3
"""Merge verify-claims batch reports into one verification file.

Usage: python3 merge_verification.py <notes folder> <output.md>

Reads every "verification batch N.md" in the notes folder (the format is the
verify-claims "Report format": tier counts line, a claims table, and
HIGH-WARN / MED-WARN / LOW-WARN sections), and writes one combined file with
the overall outcome first, then the high-risk claims, then the claims that
could not be verified, then the full claims table. Uses only the standard
library.

Prints one summary line and exits 0 on success. Exits 2 if a file cannot be
read or written, and 4 if no batch files are found or a batch does not
follow the expected format, so the caller can fall back to merging another
way.
"""

import glob
import os
import re
import sys

TIERS = ["HIGH-WARN", "MED-WARN", "LOW-WARN", "EXPLAINED"]
COUNTS_LINE = re.compile(
    r"HIGH-WARN:\s*(\d+)\s*\|\s*MED-WARN:\s*(\d+)\s*\|\s*LOW-WARN:\s*(\d+)\s*\|\s*EXPLAINED:\s*(\d+)"
)
SECTION = re.compile(r"^###\s+(HIGH-WARN|MED-WARN|LOW-WARN)\s*$", re.M)


def batch_number(path):
    m = re.search(r"verification batch (\d+)\.md$", path)
    return int(m.group(1)) if m else 0


def cells(row):
    return [c.strip() for c in row.strip().strip("|").split("|")]


def parse(text):
    """Return (header, rows, stated_counts, sections) for one batch report."""
    header, rows = None, []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        parts = cells(line)
        if parts and parts[0].lower() == "id":
            header = line.strip()
        elif set("".join(parts)) <= set("-: "):
            continue
        elif header:
            rows.append(line.strip())

    m = COUNTS_LINE.search(text)
    stated = dict(zip(TIERS, map(int, m.groups()))) if m else None

    sections = {}
    marks = list(SECTION.finditer(text))
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[mark.end():end]
        body = re.split(r"^#{1,3}\s", body, maxsplit=1, flags=re.M)[0].strip()
        if body:
            sections.setdefault(mark.group(1), []).append(body)
    return header, rows, stated, sections


def row_tier(row):
    last = cells(row)[-1].upper()
    return next((t for t in TIERS if t in last), None)


def main():
    if len(sys.argv) != 3:
        print("usage: merge_verification.py <notes folder> <output.md>")
        return 2
    folder, output = sys.argv[1], sys.argv[2]
    paths = sorted(glob.glob(os.path.join(folder, "verification batch *.md")), key=batch_number)
    if not paths:
        print(f"no 'verification batch N.md' files in {folder}")
        return 4

    header, all_rows = None, []
    counts = dict.fromkeys(TIERS, 0)
    high, unverified = [], []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as error:
            print(f"cannot read {path}: {error}")
            return 2
        batch_header, rows, stated, sections = parse(text)
        name = os.path.basename(path)
        if not rows and stated is None:
            print(f"{name} does not follow the verify-claims report format")
            return 4
        header = header or batch_header
        all_rows += rows
        if rows:
            for row in rows:
                tier = row_tier(row)
                if tier:
                    counts[tier] += 1
        else:
            for tier in TIERS:
                counts[tier] += stated[tier]
        label = f"*From {name[:-3]}:*"
        for body in sections.get("HIGH-WARN", []):
            high.append(f"{label}\n\n{body}")
        for tier in ("MED-WARN", "LOW-WARN"):
            for body in sections.get(tier, []):
                unverified.append(f"{label} ({tier})\n\n{body}")

    claims = len(all_rows) if all_rows else None
    if counts["HIGH-WARN"]:
        outcome = "FAIL"
    elif counts["MED-WARN"]:
        outcome = "PARTIAL"
    else:
        outcome = "PASS"
    tier_text = " | ".join(f"{t}: {counts[t]}" for t in TIERS)

    out = ["# Claim verification", ""]
    out.append(f"**Outcome:** {outcome}  ")
    if claims is not None:
        out.append(f"**Claims reviewed:** {claims}  ")
    out.append(f"**Tier counts:** {tier_text}  ")
    out.append(f"**Batches merged:** {len(paths)}")
    out.append("")
    if outcome == "FAIL":
        out.append("The report must not be described as verified while a HIGH-WARN claim stands.")
        out.append("")
    out.append("## High-risk claims (HIGH-WARN)")
    out.append("")
    if high:
        out.append("\n\n".join(high))
    elif counts["HIGH-WARN"]:
        out += [header or "", "|---|---|---|---|---|---|"] + [r for r in all_rows if row_tier(r) == "HIGH-WARN"]
    else:
        out.append("None.")
    out.append("")
    out.append("## Claims that could not be verified (MED-WARN and LOW-WARN)")
    out.append("")
    if unverified:
        out.append("\n\n".join(unverified))
    elif counts["MED-WARN"] or counts["LOW-WARN"]:
        out += [header or "", "|---|---|---|---|---|---|"] + [
            r for r in all_rows if row_tier(r) in ("MED-WARN", "LOW-WARN")]
    else:
        out.append("None.")
    if all_rows:
        out += ["", "## All claims", "", header or "| ID | Claim | Independent answer | Evidence | Match? | Tier |",
                "|----|-------|--------------------|----------|--------|------|"] + all_rows
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(out).rstrip() + "\n")
    except OSError as error:
        print(f"cannot write {output}: {error}")
        return 2

    claims_text = f"{claims} claims, " if claims is not None else ""
    print(f"{outcome}: {claims_text}{tier_text.replace(': ', ' ')} (written to {output})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
