#!/usr/bin/env python3
"""Confirm that every DOI in a jay-research report actually exists.

Usage: python3 check_dois.py <report.md>

Looks each distinct DOI up in the DOI registry (the doi.org handle API) and
flags any that the registry does not know. That catches invented or
mistyped DOIs before the report reaches the user. Uses only the standard
library.

Output and exit codes:
  0  "OK: N DOIs checked, all found" (or "OK: no DOIs in the report")
  1  one line per DOI the registry does not know, with its line numbers
  2  the report cannot be read
  3  "SKIPPED: ..." when doi.org cannot be reached at all (no network)

A DOI that cannot be checked because of a timeout or server error is listed
as "could not check", never as missing.
"""

import concurrent.futures
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://doi.org/api/handles/"
TIMEOUT = 10
WORKERS = 8
MAX_LINES = 40

DOI = re.compile(r"\b10\.\d{4,9}/(?:[^\s\[\]()\"'<>,;]|\([^\s()]*\))+")


def collect(lines):
    """Map each DOI (lower case, no trailing punctuation) to its line numbers."""
    found = {}
    in_fence = False
    for number, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in DOI.finditer(line):
            doi = urllib.parse.unquote(m.group(0)).rstrip(".:").lower()
            numbers = found.setdefault(doi, [])
            if number not in numbers:
                numbers.append(number)
    return found


def lookup(doi):
    """Return 'found', 'missing' or 'error: <reason>' for one DOI."""
    url = API + urllib.parse.quote(doi, safe="/")
    request = urllib.request.Request(url, headers={"User-Agent": "jay-research-check/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            code = json.load(response).get("responseCode")
            return "found" if code == 1 else "missing"
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return "missing"
        return f"error: HTTP {error.code}"
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return f"error: {getattr(error, 'reason', error)}"


def main():
    if len(sys.argv) != 2:
        print("usage: check_dois.py <report.md>")
        return 2
    try:
        with open(sys.argv[1], encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError as error:
        print(f"cannot read report: {error}")
        return 2

    dois = collect(lines)
    if not dois:
        print("OK: no DOIs in the report")
        return 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = dict(zip(dois, pool.map(lookup, dois)))

    errors = {d: r for d, r in results.items() if r.startswith("error")}
    if len(errors) == len(results):
        print(f"SKIPPED: could not reach doi.org ({next(iter(errors.values()))})")
        return 3

    missing = [d for d, r in results.items() if r == "missing"]
    if not missing and not errors:
        print(f"OK: {len(dois)} DOIs checked, all found")
        return 0

    out = []
    for doi in missing:
        out.append(f"not found: {doi} (line {', '.join(map(str, dois[doi]))})")
    for doi, reason in errors.items():
        out.append(f"could not check: {doi} ({reason})")
    print(f"{len(dois)} DOIs checked, {len(missing)} not found, {len(errors)} could not be checked:")
    for line in out[:MAX_LINES]:
        print(line)
    if len(out) > MAX_LINES:
        print(f"... and {len(out) - MAX_LINES} more")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
