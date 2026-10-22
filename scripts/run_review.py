#!/usr/bin/env python3
"""Review jay-research runs: abnormalities, feature screening and suggestions.

Usage:
  python3 run_review.py review   <notes folder>
  python3 run_review.py record   <notes folder> [--history PATH]
  python3 run_review.py patterns [--history PATH]

review    Reads the run log (<notes folder>/_run.md, written by run_log.py)
          and applies fixed thresholds. Prints "No abnormalities." or one
          "FLAG <kind>: <detail>" line per finding, then one line saying
          which skill features this run used and how they went.
record    Appends one line for this run to the history file (default
          ~/.jay-research/history.md, or the JAY_RESEARCH_HISTORY
          environment variable, or --history), including the features used
          and the suggestions the coordinator logged. Prints that line,
          then any recurring issues (PATTERN) and failing features
          (FAILING), so one call covers both. Untested features and lessons
          appear only in the full "patterns" output.
patterns  Reads the history file and reports: issues that recur (with the
          latest suggestion for each), features never exercised or that keep
          failing, and the latest lessons from runs.

The skill never edits its own files. Suggestions are for the user to apply.
The history file holds run titles and suggestions, so it may name
confidential topics: keep it out of any public repository.

Abnormality flags (review):
  budget-hit      a researcher used its whole tool-call budget and still
                  reported a critical gap (using the whole budget alone is
                  normal and is not flagged; the count is self-reported)
  slow-stage      a stage other than research (report, checks, verify) took
                  over 40% of a run of 10+ minutes
  unfinished      a stage was started but never ended
  check-unfixed   a check still reported problems after its fix round
  fallback        a fallback path ran (SendMessage, a script, the merger)
  doi-not-found   the DOI check found DOIs that do not exist
  brief-wrong     researchers reported brief corrections (a question issue,
                  not a skill issue; recorded for the patterns)

Features screened (each run: ok, failed, or not used):
  notes-check, report-check, doi-check   from "checks:" in the report end
                                         event, for example "checks: notes
                                         fixed, report OK, doi 2 not found 0
                                         remain". OK/fixed = ok; "N remain"
                                         (N > 0) = failed, because the fix
                                         round did not clear it; skipped = not
                                         used. Failed checks and DOIs not
                                         found are also flagged.
  gap-sendmessage   step 5 continued researchers ("gap round: N continued")
  verify            verify start and verify end both logged
  verify-merge      verify ran and the merge script did not fall back

The coordinator logs suggestions as one "observation" event, separated by
semicolons, each prefixed with its flag kind ("budget-hit: ...") or with
"lesson:" for experience from researchers ("lesson: site X blocks
fetching; use connector Y; consider adding to researcher.md").

Exit codes: 0 success (review: no flags), 1 review found flags, 2 bad usage
or file error. Uses only the standard library.
"""

import datetime
import os
import re
import sys

FMT = "%Y-%m-%dT%H:%M:%SZ"
DEPTHS = ["Quick", "Standard", "Deep", "Exhaustive"]
FEATURES = ["notes-check", "report-check", "doi-check", "gap-sendmessage", "verify", "verify-merge"]
HISTORY_HEADER = (
    "# jay-research run history\n\n"
    "One line per run, written by scripts/run_review.py. May name confidential "
    "topics: keep this file out of public repositories.\n\n"
    "| Date | Title | Depth | Minutes | Researchers | Budget hits | Flags | Features | Suggestions |\n"
    "|------|-------|-------|---------|-------------|-------------|-------|----------|-------------|\n"
)
TOOL_CALLS = re.compile(r"(\d+)\s*(?:of|/)\s*(\d+)")
CRITICAL_GAPS = re.compile(r"critical gaps?:\s*(none|\d+)", re.I)
REMAIN = re.compile(r"(\d+)\s+remain", re.I)
NOT_FOUND = re.compile(r"(\d+)\s+not found", re.I)
GAP_ROUND = re.compile(r"gap round:\s*(\d+)\s+continued", re.I)
CHECKS = re.compile(r"checks?:\s*(.*)$", re.I)
SHORT = {"ok": "ok", "failed": "fail", "not used": "-"}


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


def check_status(text):
    """Map one 'notes OK' / 'doi 2 remain' / 'report skipped' item to a status."""
    low = text.lower()
    if "skip" in low:
        return "not used"
    m = REMAIN.search(low)
    if m and int(m.group(1)) > 0:
        return "failed"
    if "ok" in low or "fixed" in low or "remain" in low or NOT_FOUND.search(low):
        return "ok"
    return None


def analyse(events):
    """Return (flags, facts) for one run. flags: list of (kind, detail)."""
    flags = []
    facts = {"researchers": 0, "budget_hits": 0, "depth": "?", "minutes": 0,
             "features": dict.fromkeys(FEATURES, "not used"), "suggestions": []}
    if not events:
        return flags, facts

    total = (events[-1][0] - events[0][0]).total_seconds()
    facts["minutes"] = round(total / 60)
    opened, timed = {}, []
    fallbacks = []
    verify_started = verify_ended = False

    for when, stage, detail in events:
        if stage == "run start":
            depth = next((d for d in DEPTHS if d.lower() in detail.lower()), None)
            facts["depth"] = depth or "?"
        if stage == "research end":
            # One segment per researcher: "{topic} {used} of {budget}, critical gaps: {n|none}".
            for segment in detail.split(";"):
                g = GAP_ROUND.search(segment)
                if g:
                    if int(g.group(1)) > 0:
                        facts["features"]["gap-sendmessage"] = "ok"
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
                c = CRITICAL_GAPS.search(segment)
                if c and c.group(1).lower() not in ("none", "0"):
                    flags.append(("budget-hit", f"{segment.strip()} (whole budget used, critical gap left)"))
        if stage == "report end":
            m = CHECKS.search(detail)
            if m:
                for item in m.group(1).split(","):
                    name = item.strip().split(" ")[0].lower()
                    feature = {"notes": "notes-check", "report": "report-check", "doi": "doi-check"}.get(name)
                    status = check_status(item)
                    if feature and status:
                        facts["features"][feature] = status
                    if feature and status == "failed":
                        flags.append(("check-unfixed", f"{name} check: {item.strip()}"))
                    nf = NOT_FOUND.search(item)
                    if feature == "doi-check" and nf and int(nf.group(1)) > 0:
                        flags.append(("doi-not-found", item.strip()))
        if stage == "verify start":
            verify_started = True
        if stage == "verify end":
            verify_ended = True
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
            fallbacks.append(detail.lower())
            flags.append(("fallback", detail))
        elif stage == "brief corrections":
            m = re.match(r"\s*(\d+)", detail)
            if not m or int(m.group(1)) > 0:
                flags.append(("brief-wrong", detail))
        elif stage == "observation":
            facts["suggestions"] += [s.strip() for s in detail.split(";") if s.strip()]

    if any("sendmessage" in f for f in fallbacks):
        facts["features"]["gap-sendmessage"] = "failed"
    if verify_started:
        facts["features"]["verify"] = "ok" if verify_ended else "failed"
        merge_failed = any("merge" in f for f in fallbacks)
        facts["features"]["verify-merge"] = "failed" if merge_failed else ("ok" if verify_ended else "not used")

    for name, seconds in timed:
        # Research normally takes most of a run, so only other stages count.
        if name not in ("run", "research") and total >= 600 and seconds > total * 0.4:
            flags.append(("slow-stage", f"{name} took {round(seconds / 60)} of {round(total / 60)} minutes"))
    for name in opened:
        if name != "run":
            flags.append(("unfinished", f"{name} was started but never ended"))
    return flags, facts


def features_text(features):
    return " ".join(f"{k}:{SHORT[v]}" for k, v in features.items())


def review(folder):
    flags, facts = analyse(read_events(folder))
    if not flags:
        print("No abnormalities.")
    for kind, detail in flags:
        print(f"FLAG {kind}: {detail}")
    print(f"Features: {features_text(facts['features'])}")
    return 1 if flags else 0


def clean(text, limit=None):
    text = text.replace("|", "/").replace("\n", " ").strip()
    return text if not limit or len(text) <= limit else text[: limit - 1] + "…"


def record(folder, path):
    events = read_events(folder)
    flags, facts = analyse(events)
    title = clean(os.path.basename(os.path.normpath(folder)))
    date = events[0][0].strftime("%Y-%m-%d") if events else datetime.date.today().isoformat()
    kinds = sorted({k for k, _ in flags})
    suggestions = "; ".join(clean(s, 200) for s in facts["suggestions"]) or "none"
    line = (f"| {date} | {title} | {facts['depth']} | {facts['minutes']} | {facts['researchers']} | "
            f"{facts['budget_hits']} | {', '.join(kinds) or 'none'} | {features_text(facts['features'])} | "
            f"{suggestions} |")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(HISTORY_HEADER)
        f.write(line + "\n")
    print(line)
    patterns(path, quiet=True)
    return 0


def read_history(path):
    runs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            parts = [p.strip() for p in line.strip().strip("|").split("|")]
            if len(parts) < 7 or not re.match(r"\d{4}-\d{2}-\d{2}$", parts[0]):
                continue
            features = {}
            if len(parts) >= 8:
                for item in parts[7].split():
                    if ":" in item:
                        k, v = item.split(":", 1)
                        features[k] = v
            suggestions = []
            if len(parts) >= 9 and parts[8] != "none":
                suggestions = [s.strip() for s in " | ".join(parts[8:]).split(";") if s.strip()]
            runs.append({
                "date": parts[0], "depth": parts[2],
                "kinds": [] if parts[6] == "none" else [k.strip() for k in parts[6].split(",")],
                "features": features, "suggestions": suggestions,
            })
    return runs


def patterns(path, quiet=False):
    """Print recurring issues, feature coverage and lessons. quiet: only findings."""
    runs = read_history(path)
    if not runs:
        if not quiet:
            print("No runs recorded yet.")
        return 0
    lines = []

    # Recurring issues, with the latest suggestion for each kind.
    latest = {}
    for r in runs:
        for s in r["suggestions"]:
            kind = s.split(":", 1)[0].strip().lower()
            latest[kind] = s.split(":", 1)[1].strip() if ":" in s else s
    for depth in DEPTHS + ["?"]:
        at_depth = [r for r in runs if r["depth"] == depth]
        counts = {}
        for r in at_depth:
            for k in set(r["kinds"]):
                counts[k] = counts.get(k, 0) + 1
        for kind, n in sorted(counts.items(), key=lambda kv: -kv[1]):
            if n >= 2 and n * 2 >= len(at_depth):
                hint = f" — latest suggestion: {latest[kind]}" if kind in latest else ""
                lines.append(f"PATTERN {kind}: {n} of {len(at_depth)} {depth} runs{hint}")

    # Feature coverage, from runs that recorded features.
    screened = [r for r in runs if r["features"]]
    for feature in FEATURES:
        used = [r["features"].get(feature) for r in screened if r["features"].get(feature) in ("ok", "fail")]
        failed = used.count("fail")
        # UNTESTED only in the full output: opt-in features (verify) and depth-
        # dependent ones (the gap round) would otherwise show after every run.
        if not quiet and screened and not used and len(screened) >= 3:
            lines.append(f"UNTESTED {feature}: not exercised in {len(screened)} screened runs")
        elif failed >= 2 and failed * 2 >= len(used):
            lines.append(f"FAILING {feature}: failed {failed} of {len(used)} times it was used")

    # Lessons from runs (latest five, newest first). Not repeated after each
    # run (quiet mode): the coordinator already has this run's lessons.
    lessons = [] if quiet else [s for r in reversed(runs) for s in r["suggestions"] if s.lower().startswith("lesson")]
    for s in lessons[:5]:
        lines.append(f"LESSON {s.split(':', 1)[1].strip() if ':' in s else s}")

    if quiet:
        for line in lines:
            print(line)
        return 0
    print(f"{len(runs)} run(s) recorded, {len(screened)} with feature screening.")
    if not lines:
        print("No recurring issues, untested or failing features, or lessons yet.")
    for line in lines:
        print(line)
    if screened:
        print("Feature use across screened runs:")
        for feature in FEATURES:
            values = [r["features"].get(feature, "-") for r in screened]
            print(f"- {feature}: ok {values.count('ok')}, failed {values.count('fail')}, "
                  f"not used {len(values) - values.count('ok') - values.count('fail')}")
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
