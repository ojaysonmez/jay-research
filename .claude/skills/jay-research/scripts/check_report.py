#!/usr/bin/env python3
"""Mechanical checks for a jay-research report.

Usage: python3 check_report.py <report.md>

Checks only rules that have an exact answer, so the coordinator does not
have to read the report or spend a subagent on them:

1. Every DOI, clinical trial number (NCT) and FDA number (510(k), PMA,
   De Novo, NDA, BLA, ANDA) appears inside a Markdown link, never as
   plain text. 510(k), PMA and De Novo numbers are only flagged on lines
   that also mention "510(k)", "PMA", "De Novo" or "FDA", so part numbers
   and SKUs are not mistaken for them.
2. Every DOI link points to the same DOI its text shows.
3. No link has an empty or non-web target.
4. The research depth is stated directly under the title.

Prints "OK" and exits 0 when nothing is wrong. Otherwise prints one line
per problem (line number, what is wrong, the text involved) and exits 1.
Exits 2 if the report cannot be read. Uses only the standard library.
"""

import re
import sys

MAX_PROBLEMS = 40

LINK = re.compile(r"\[([^\]]*)\]\(((?:[^()\s]|\([^()\s]*\))*)(?:\s+\"[^\"]*\")?\)")
BARE_URL = re.compile(r"<?https?://[^\s)>\]]+>?")
INLINE_CODE = re.compile(r"`[^`]*`")

IDENTIFIERS = [
    ("DOI", re.compile(r"\b10\.\d{4,9}/(?:[^\s\[\]()\"'<>,;]|\([^\s()]*\))+")),
    ("clinical trial number", re.compile(r"\bNCT\d{8}\b")),
    ("510(k) number", re.compile(r"\bK\d{6}\b")),
    ("De Novo number", re.compile(r"\bDEN\d{6}\b")),
    ("PMA number", re.compile(r"\bP\d{6}\b")),
    ("NDA/BLA/ANDA number", re.compile(r"\b(?:NDA|BLA|ANDA)[ -]?\d{6}\b")),
]

# K, P and DEN followed by six digits also match part numbers and SKUs, so
# these are only flagged on lines that also mention the FDA or the pathway.
FDA_CONTEXT_LABELS = {"510(k) number", "PMA number", "De Novo number"}
FDA_CONTEXT = re.compile(r"510\(k\)|\bPMA\b|De Novo|\bFDA\b", re.I)

DEPTH_WORDS = re.compile(r"\b(Light|Max|Quick|Standard|Deep|Exhaustive|level [1-4])\b", re.I)


def clean_doi(text):
    """Normalise a DOI for comparison: lower case, no trailing punctuation."""
    return text.rstrip(".:").lower()


def covered_spans(line):
    """Character ranges that are inside a link or a bare URL."""
    spans = [(m.start(), m.end()) for m in LINK.finditer(line)]
    spans += [(m.start(), m.end()) for m in BARE_URL.finditer(line)]
    spans += [(m.start(), m.end()) for m in INLINE_CODE.finditer(line)]
    return spans


def inside(pos, spans):
    return any(start <= pos < end for start, end in spans)


def check(lines):
    problems = []
    in_fence = False

    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        # 1. Identifiers written as plain text.
        spans = covered_spans(line)
        fda_line = bool(FDA_CONTEXT.search(line))
        for label, pattern in IDENTIFIERS:
            if label in FDA_CONTEXT_LABELS and not fda_line:
                continue
            for m in pattern.finditer(line):
                if not inside(m.start(), spans):
                    problems.append((number, f"{label} not hyperlinked", m.group(0).rstrip(".:")))

        for m in LINK.finditer(line):
            text, target = m.group(1), m.group(2)

            # 3. Empty or non-web link targets.
            if not target:
                problems.append((number, "link has no target", m.group(0)))
                continue
            if not re.match(r"https?://", target):
                problems.append((number, "link target is not a web address", m.group(0)))
                continue

            # 2. DOI link whose text and target disagree.
            if "doi.org/" in target:
                text_doi = IDENTIFIERS[0][1].search(text)
                target_doi = target.split("doi.org/", 1)[1]
                if text_doi and clean_doi(text_doi.group(0)) != clean_doi(target_doi):
                    problems.append((number, "DOI text and link target differ", m.group(0)))

    # 4. Depth level stated directly under the title.
    title_index = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    if title_index is None:
        problems.append((1, "no title line starting with '# '", ""))
    else:
        following = [l for l in lines[title_index + 1:title_index + 4] if l.strip()]
        if not following or not DEPTH_WORDS.search(following[0]):
            problems.append((title_index + 2, "depth level not stated directly under the title", ""))

    return problems


def main():
    if len(sys.argv) != 2:
        print("usage: check_report.py <report.md>")
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as error:
        print(f"cannot read report: {error}")
        return 2

    problems = check(lines)
    if not problems:
        print("OK")
        return 0

    print(f"{len(problems)} problem(s):")
    for number, what, text in problems[:MAX_PROBLEMS]:
        print(f"line {number}: {what}" + (f": {text}" if text else ""))
    if len(problems) > MAX_PROBLEMS:
        print(f"... and {len(problems) - MAX_PROBLEMS} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())
