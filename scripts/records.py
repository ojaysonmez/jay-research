#!/usr/bin/env python3
"""Structured records for comparison scans in jay-research.

Usage:
  python3 records.py init  <notes folder> "<key field>" "<field>, <field>, ..."
  python3 records.py check <notes folder>
  python3 records.py merge <notes folder> <output.md>

init   Writes <notes folder>/fields.json: the key field (the item's name,
       for example "company"), up to 8 other fields, and "sources", which is
       always added. Prints the field list to use in every researcher brief.
check  Validates every *.records.json in the folder against fields.json:
       each file is a JSON array of objects; each object has the key field
       (not empty) and every field (null allowed, meaning "searched, not
       found"); "sources" is a non-empty list of web links; and every
       identifier in a value (DOI, NCT, K/P/DEN plus six digits,
       NDA/BLA/ANDA) also appears in that researcher's notes. Prints "OK"
       or one line per problem, grouped by file.
merge  Combines all records into one comparison table (write it to
       _records.md in the notes folder: the checks skip names starting
       with "_"). Items are matched by
       their key field, ignoring case, punctuation and company suffixes
       (Inc, LLC, Corp, Ltd, GmbH). For a matched item, a field found by one
       researcher fills a gap left by another; two different values are kept
       side by side and listed as a conflict. Sources are combined. Writes
       <output.md> (a Markdown table plus the conflict list) and a
       .json file next to it, and prints one summary line.

Exit codes: 0 success, 1 check found problems, 2 bad usage or file error,
4 no fields.json or no records files (structured mode was not used).
Uses only the standard library.
"""

import glob
import json
import os
import re
import sys

MAX_FIELDS = 8
MAX_LINES = 40
SUFFIXES = re.compile(r"\b(inc|llc|corp|corporation|ltd|limited|gmbh|co|company|plc|sa|ag)\b\.?", re.I)
URL = re.compile(r"^https?://\S+$")
# Identifiers a record may hold. Each one found in a record value must also
# appear in the researcher's own notes, so an invented number cannot reach
# the comparison table unnoticed.
IDENTIFIERS = re.compile(
    r"\b10\.\d{4,9}/(?:[^\s\[\]()\"'<>,;]|\([^\s()]*\))+"
    r"|\bNCT\d{8}\b"
    r"|\b(?:K|P|DEN)\d{6}\b"
    r"|\b(?:NDA|BLA|ANDA)[ -]?\d{6}\b",
    re.I,
)


def fields_path(folder):
    return os.path.join(folder, "fields.json")


def load_fields(folder):
    with open(fields_path(folder), encoding="utf-8") as f:
        spec = json.load(f)
    return spec["key"], spec["fields"]


def record_files(folder):
    return sorted(glob.glob(os.path.join(folder, "*.records.json")))


def init(folder, key, field_text):
    key = key.strip()
    others = [f.strip() for f in field_text.split(",") if f.strip()]
    others = [f for f in others if f.lower() not in (key.lower(), "sources")]
    if not key:
        print("the key field cannot be empty")
        return 2
    if len(others) > MAX_FIELDS:
        print(f"too many fields ({len(others)}); use at most {MAX_FIELDS} besides the key")
        return 2
    fields = [key] + others + ["sources"]
    os.makedirs(folder, exist_ok=True)
    with open(fields_path(folder), "w", encoding="utf-8") as f:
        json.dump({"key": key, "fields": fields}, f, indent=2)
    print("Fields: " + ", ".join(fields))
    return 0


def squash(text):
    """Lower case without spaces or hyphens, so "NDA 012345" matches "NDA-012345"."""
    return re.sub(r"[\s-]", "", text.lower())


def notes_text(folder, records_name):
    """Text of the notes that belong to a records file, or None if there are none."""
    base = records_name[: -len(".records.json")]
    stem = base[: -len(" followup")] if base.lower().endswith(" followup") else base
    texts = []
    for name in {f"{stem}.md", f"{stem} followup.md", f"{base}.md"}:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                texts.append(f.read())
    return squash("\n".join(texts)) if texts else None


def check(folder):
    key, fields = load_fields(folder)
    files = record_files(folder)
    if not files:
        print("no records files")
        return 4
    report, items = [], 0
    for path in files:
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as error:
            report.append(f"{name}: not valid JSON ({error})")
            continue
        if not isinstance(data, list):
            report.append(f"{name}: must be a JSON array of records")
            continue
        notes = notes_text(folder, name)
        if notes is None:
            report.append(f"{name}: no matching notes file, so its identifiers cannot be checked")
        for i, rec in enumerate(data, start=1):
            if not isinstance(rec, dict):
                report.append(f"{name}: record {i} is not an object")
                continue
            items += 1
            label = rec.get(key) or f"record {i}"
            if not rec.get(key):
                report.append(f"{name}: record {i} has no {key}")
            missing = [f for f in fields if f not in rec and not (f == key and not rec.get(key))]
            if missing:
                report.append(f"{name}: '{label}' is missing: {', '.join(missing)} (use null if not found)")
            if notes is not None:
                for field, value in rec.items():
                    if field == "sources" or not isinstance(value, str):
                        continue
                    for m in IDENTIFIERS.finditer(value):
                        ident = m.group(0).rstrip(".:")
                        if squash(ident) not in notes:
                            report.append(f"{name}: {ident} in '{label}' does not appear in your notes")
            sources = rec.get("sources")
            if not isinstance(sources, list) or not sources:
                report.append(f"{name}: '{label}' has no sources")
            elif not all(isinstance(s, str) and URL.match(s) for s in sources):
                report.append(f"{name}: '{label}' has a source that is not a web link")

    notes = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(folder, "*.md"))}
    with_records = {os.path.basename(p)[: -len(".records.json")] for p in files}
    skip = re.compile(r"^(_|agents$|claims batch \d+$|verification batch \d+$)|followup$", re.I)
    without = sorted(n for n in notes - with_records if not skip.search(n))

    if not report:
        line = f"OK: {items} records in {len(files)} files"
        if without:
            line += f" (no records file for: {', '.join(without)})"
        print(line)
        return 0
    print(f"{len(report)} problem(s) in {len(files)} records files:")
    for line in report[:MAX_LINES]:
        print(line)
    if len(report) > MAX_LINES:
        print(f"... and {len(report) - MAX_LINES} more")
    return 1


def normalise(name):
    text = SUFFIXES.sub(" ", str(name).lower())
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def cell(value):
    if value is None:
        return "not found"
    return str(value).replace("|", "/").replace("\n", " ").strip()


def merge(folder, output):
    key, fields = load_fields(folder)
    files = record_files(folder)
    if not files:
        print("no records files")
        return 4

    merged, order, conflicts = {}, [], []
    total = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        for rec in data if isinstance(data, list) else []:
            if not isinstance(rec, dict) or not rec.get(key):
                continue
            total += 1
            norm = normalise(rec[key])
            if norm not in merged:
                merged[norm] = {f: rec.get(f) for f in fields}
                merged[norm]["sources"] = list(rec.get("sources") or [])
                order.append(norm)
                continue
            base = merged[norm]
            for f in fields:
                if f in (key, "sources"):
                    continue
                new, old = rec.get(f), base.get(f)
                if new is None or new == old:
                    continue
                if old is None:
                    base[f] = new
                elif str(new).strip().lower() != str(old).strip().lower():
                    base[f] = f"{old} / {new}"
                    conflicts.append(f"{base[key]}: {f} is \"{old}\" in one source set and \"{new}\" in another")
            for s in rec.get("sources") or []:
                if s not in base["sources"]:
                    base["sources"].append(s)

    rows = [merged[n] for n in order]
    shown = [f for f in fields if f != "sources"]
    lines = [
        "# Comparison records",
        "",
        f"{len(rows)} items, merged from {len(files)} records files. \"not found\" means the researchers searched and found nothing.",
        "",
        "| " + " | ".join(shown + ["sources"]) + " |",
        "|" + "---|" * (len(shown) + 1),
    ]
    for r in rows:
        links = " ".join(f"[{i}]({s})" for i, s in enumerate(r["sources"], start=1))
        lines.append("| " + " | ".join(cell(r.get(f)) for f in shown) + f" | {links} |")
    lines += ["", "## Conflicts", ""]
    lines += [f"- {c}" for c in conflicts] or ["None."]
    try:
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with open(os.path.splitext(output)[0] + ".json", "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)
    except OSError as error:
        print(f"cannot write {output}: {error}")
        return 2
    print(f"{len(rows)} items from {total} records in {len(files)} files, "
          f"{total - len(rows)} duplicates merged, {len(conflicts)} conflicts (written to {output})")
    return 0


def main():
    a = sys.argv[1:]
    try:
        if len(a) == 4 and a[0] == "init":
            return init(a[1], a[2], a[3])
        if len(a) == 2 and a[0] == "check":
            return check(a[1])
        if len(a) == 3 and a[0] == "merge":
            return merge(a[1], a[2])
    except FileNotFoundError:
        print("no fields.json: structured mode was not set up for this run")
        return 4
    except (OSError, ValueError, KeyError) as error:
        print(f"records error: {error}")
        return 2
    print(__doc__.split("\n\n")[1])
    return 2


if __name__ == "__main__":
    sys.exit(main())
