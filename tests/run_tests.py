#!/usr/bin/env python3
"""Tests for the jay-research scripts. No model and no network needed.

Usage (from the repository root):
  python3 tests/run_tests.py

Each test runs a script from .claude/skills/jay-research/scripts on small
fixed inputs in a temporary folder and checks its output and exit code.
Standard library only. check_dois.py is tested for DOI extraction only,
because its lookups need the network.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, ".claude", "skills", "jay-research", "scripts")

GOOD_NOTES = """# Topic

## Question one

### Takeaway
A short summary.

### Cited Findings
- A sourced finding. [Source](https://example.com/a)
  - Detail under it with no link of its own.

### Inferences
- An inference.

### Gaps
- A gap.
"""


def run(script, *args):
    """Run a script and return (exit code, stdout)."""
    result = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *map(str, args)],
                            capture_output=True, text=True, encoding="utf-8")
    return result.returncode, result.stdout


def load(script):
    spec = importlib.util.spec_from_file_location(script[:-3], os.path.join(SCRIPTS, script))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="jay_research_test_")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path


class CheckReport(TempDirCase):
    def test_clean_report_passes(self):
        path = self.write("r.md", "# Title\n\nStandard\n\nSee [10.1000/abc](https://doi.org/10.1000/abc) and "
                                  "[NCT01234567](https://clinicaltrials.gov/study/NCT01234567).\n")
        code, out = run("check_report.py", path)
        self.assertEqual((code, out.strip()), (0, "OK"))

    def test_plain_identifiers_mismatch_and_bad_links_are_flagged(self):
        path = self.write("r.md", "# Title\n\nStandard\n\nPlain 10.1000/abc and NCT01234567.\n\n"
                                  "[10.1000/abc](https://doi.org/10.1000/xyz) [x]() [rel](foo.md)\n")
        code, out = run("check_report.py", path)
        self.assertEqual(code, 1)
        for text in ("DOI not hyperlinked", "clinical trial number not hyperlinked",
                     "DOI text and link target differ", "link has no target", "not a web address"):
            self.assertIn(text, out)

    def test_fda_numbers_need_fda_context(self):
        path = self.write("r.md", "# Title\n\nStandard\n\nSKU K123456 and part P654321.\n\n"
                                  "FDA-cleared as K231234.\n")
        code, out = run("check_report.py", path)
        self.assertEqual(code, 1)
        self.assertIn("K231234", out)
        self.assertNotIn("K123456", out)
        self.assertNotIn("P654321", out)

    def test_missing_depth_line_is_flagged(self):
        path = self.write("r.md", "# Title\n\nThe report starts here.\n")
        code, out = run("check_report.py", path)
        self.assertEqual(code, 1)
        self.assertIn("depth level not stated", out)

    def test_unreadable_report_exits_2(self):
        code, _ = run("check_report.py", os.path.join(self.tmp, "missing.md"))
        self.assertEqual(code, 2)


class CheckNotes(TempDirCase):
    def test_good_notes_pass_and_nested_detail_is_ignored(self):
        self.write("topic.md", GOOD_NOTES)
        code, out = run("check_notes.py", self.tmp)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("OK"))

    def test_unsourced_top_level_finding_and_lead_are_flagged(self):
        self.write("topic.md", GOOD_NOTES.replace("- A sourced finding. [Source](https://example.com/a)",
                                                  "- An unsourced finding.")
                   + "\n## Leads for other topics\n- A lead with no link\n")
        code, out = run("check_notes.py", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("finding without a source link: An unsourced finding.", out)
        self.assertIn("lead without a source link", out)

    def test_missing_sections_are_flagged(self):
        self.write("topic.md", "# Topic\n\n## Question one\n\n### Takeaway\nx\n")
        code, out = run("check_notes.py", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("missing", out)

    def test_researcher_that_saved_no_notes_is_noticed(self):
        sep = os.sep
        listed = lambda name: f"C:{sep}w{sep}research_notes{sep}Title{sep}{name}"
        self.write("agents.md", "Question; Standard; report path\n"
                                f"- Seg A | {listed('seg_a.md')} | agent-1\n"
                                f"- Seg B | {listed('seg_b.md')} | agent-2\n")
        self.write("seg_a.md", GOOD_NOTES)
        code, out = run("check_notes.py", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("seg_b.md: no notes saved", out)
        self.assertNotIn("seg_a.md: no notes saved", out)


class Records(TempDirCase):
    def init(self):
        code, out = run("records.py", "init", self.tmp, "company", "FDA status, clearance number")
        self.assertEqual(code, 0, out)
        self.assertIn("Fields: company, FDA status, clearance number, sources", out)

    def test_identifier_must_appear_in_notes(self):
        self.init()
        self.write("seg.md", "# T\n\n## Q\n\n### Cited Findings\n- Acme cleared K123456 [S](https://a.com)\n")
        self.write("seg.records.json",
                   '[{"company":"Acme","FDA status":"cleared","clearance number":"K123456","sources":["https://a.com"]},'
                   '{"company":"Beta","FDA status":"cleared","clearance number":"K999999","sources":["https://b.com"]}]')
        code, out = run("records.py", "check", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("K999999 in 'Beta' does not appear in your notes", out)
        self.assertNotIn("K123456", out)

    def test_missing_field_and_missing_sources_are_flagged(self):
        self.init()
        self.write("seg.md", "# T\n")
        self.write("seg.records.json", '[{"company":"Acme","FDA status":"cleared","sources":[]}]')
        code, out = run("records.py", "check", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("missing: clearance number", out)
        self.assertIn("has no sources", out)

    def test_merge_matches_suffixes_and_keeps_conflicts(self):
        self.init()
        self.write("a.records.json",
                   '[{"company":"Acme Inc","FDA status":"cleared","clearance number":null,"sources":["https://a.com"]}]')
        self.write("b.records.json",
                   '[{"company":"ACME Corp.","FDA status":"pending","clearance number":"K111111","sources":["https://b.com"]}]')
        out_file = os.path.join(self.tmp, "_records.md")
        code, out = run("records.py", "merge", self.tmp, out_file)
        self.assertEqual(code, 0, out)
        self.assertIn("1 items from 2 records", out)
        self.assertIn("1 duplicates merged", out)
        self.assertIn("1 conflicts", out)
        with open(out_file, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("K111111", text)  # filled the gap left by the other researcher
        self.assertIn("cleared / pending", text)  # conflicting values kept side by side

    def test_no_fields_json_exits_4(self):
        code, _ = run("records.py", "check", self.tmp)
        self.assertEqual(code, 4)


class MergeVerification(TempDirCase):
    BATCH = ("## Claim verification report\n\n**Claims reviewed:** 2\n**Outcome:** FAIL (1 HIGH)\n"
             "**Tier counts:** HIGH-WARN: 1 | MED-WARN: 0 | LOW-WARN: 1 | EXPLAINED: 0\n\n"
             "| ID | Claim | Independent answer | Evidence | Match? | Tier |\n"
             "|----|-------|--------------------|----------|--------|------|\n"
             "| C1 | a | b | e | no | HIGH-WARN |\n"
             "| C2 | c | d | f | cannot-verify | LOW-WARN |\n\n"
             "### HIGH-WARN\nC1: wrong year.\n### MED-WARN\n### LOW-WARN\nC2: paywalled.\n")

    def test_merge_sets_outcome_and_lists_high_risk_first(self):
        self.write("verification batch 1.md", self.BATCH)
        out_file = os.path.join(self.tmp, "merged.md")
        code, out = run("merge_verification.py", self.tmp, out_file)
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("FAIL: 2 claims"))
        with open(out_file, encoding="utf-8") as f:
            text = f.read()
        self.assertLess(text.index("C1: wrong year."), text.index("C2: paywalled."))

    def test_no_batch_files_exits_4(self):
        code, _ = run("merge_verification.py", self.tmp, os.path.join(self.tmp, "merged.md"))
        self.assertEqual(code, 4)


class Gaps(TempDirCase):
    def test_add_dedupe_keep_retype_close_and_list(self):
        reg = os.path.join(self.tmp, "open-gaps.md")
        self.assertEqual(run("gaps.py", "add", reg, "Run A", "Topic X", "blocked", "Missing figure", "journal"),
                         (0, "G1\n"))
        code, out = run("gaps.py", "add", reg, "Run B", "topic  x", "blocked", "missing   FIGURE", "journal")
        self.assertEqual((code, out.strip()), (0, "G1 (already open)"))
        self.assertEqual(run("gaps.py", "add", reg, "Run B", "Topic Y", "searchable", "Other gap", "registry")[1], "G2\n")
        self.assertEqual(run("gaps.py", "keep", reg, "G1", "Run B", "tried PubMed", "searchable")[0], 0)
        code, out = run("gaps.py", "keep", reg, "G1", "Run B", "x", "bogus")
        self.assertEqual(code, 2)
        self.assertIn("type must be one of", out)
        self.assertEqual(run("gaps.py", "close", reg, "G2", "Run B")[0], 0)
        code, out = run("gaps.py", "list", reg, "--open")
        self.assertIn("| G1 | open | searchable |", out)
        self.assertNotIn("G2", out)

    def test_closing_an_unknown_gap_fails(self):
        reg = os.path.join(self.tmp, "open-gaps.md")
        code, out = run("gaps.py", "close", reg, "G9", "Run A")
        self.assertNotEqual(code, 0)


class RunLogAndReview(TempDirCase):
    def log(self, stage, detail):
        code, out = run("run_log.py", self.tmp, "event", stage, detail)
        self.assertEqual(code, 0, out)

    def clean_run(self, research_end):
        self.log("run start", "Question, Standard, verify off")
        self.log("research start", "3 researchers")
        self.log("research end", research_end)
        self.log("report start", "")
        self.log("report end", "saved; checks: notes OK, report fixed, doi 0 not found")
        self.log("run end", "")

    def test_budget_hit_is_flagged_only_with_a_critical_gap(self):
        self.clean_run("A 8 of 10, critical gaps: none; B 10 of 10, critical gaps: none")
        code, out = run("run_review.py", "review", self.tmp)
        self.assertEqual(code, 0, out)
        self.assertIn("No abnormalities.", out)
        self.assertIn("notes-check:ok", out)

    def test_budget_hit_with_critical_gap_is_flagged(self):
        self.clean_run("A 8 of 10, critical gaps: none; B 10 of 10, critical gaps: 1")
        code, out = run("run_review.py", "review", self.tmp)
        self.assertEqual(code, 1)
        self.assertIn("FLAG budget-hit: B 10 of 10", out)

    def test_summary_reports_timed_stages(self):
        self.clean_run("A 8 of 10, critical gaps: none")
        code, out = run("run_log.py", self.tmp, "summary")
        self.assertEqual(code, 0)
        self.assertIn("Total:", out)
        self.assertIn("- research:", out)
        self.assertIn("- report:", out)

    def test_record_appends_history_and_reads_back(self):
        self.clean_run("A 8 of 10, critical gaps: none")
        history = os.path.join(self.tmp, "history.md")
        code, out = run("run_review.py", "record", self.tmp, "--history", history)
        self.assertEqual(code, 0, out)
        with open(history, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("Standard", text)
        code, out = run("run_review.py", "patterns", "--history", history)
        self.assertEqual(code, 0)
        self.assertIn("1 run(s) recorded", out)


class LogFailure(TempDirCase):
    def install(self):
        """Copy log_failure.py into a fake repository, four levels below its root."""
        folder = os.path.join(self.tmp, ".claude", "skills", "jay-research", "scripts")
        os.makedirs(folder)
        shutil.copy(os.path.join(SCRIPTS, "log_failure.py"), folder)
        return os.path.join(folder, "log_failure.py")

    def test_row_is_appended_with_pipes_escaped(self):
        script = self.install()
        log = self.write("failure-log.md", "| Date | Run | Stage | What failed | What | Outcome |\n|---|---|---|---|---|---|\n")
        result = subprocess.run([sys.executable, script, "Run A", "research", "tool | timed out", "retried", "ok"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stdout)
        with open(log, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("tool \\| timed out", text)

    def test_skipped_when_there_is_no_failure_log(self):
        script = self.install()
        result = subprocess.run([sys.executable, script, "Run A", "research", "x", "y", "z"],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0)
        self.assertIn("skipped", result.stdout)


class CheckDoisExtraction(unittest.TestCase):
    def test_collect_finds_each_doi_once_with_line_numbers(self):
        module = load("check_dois.py")
        lines = ["See [10.1038/Nature14539](https://doi.org/10.1038/nature14539).",
                 "```", "10.9999/in-a-code-fence", "```",
                 "Again 10.1038/nature14539, and 10.1000/xyz123."]
        found = module.collect(lines)
        self.assertEqual(found["10.1038/nature14539"], [1, 5])
        self.assertEqual(found["10.1000/xyz123"], [5])
        self.assertNotIn("10.9999/in-a-code-fence", found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
