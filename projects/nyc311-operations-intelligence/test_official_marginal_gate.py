"""Synthetic-only candidate/official-public-marginal release-gate regression tests."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from release_privacy_gate import inspect_official_marginal_receipt
from test_official_marginal_receipt import receipt


def source():
    data = receipt()
    data["queries"]["cohort"]["rows"] = [{"records": "20", "distinct_keys": "20"}]
    for dimension, counts in (("borough", (8, 12)), ("agency", (7, 13)),
                              ("status", (9, 11))):
        for row, n in zip(data["queries"][dimension]["rows"], counts):
            row["records"] = str(n)
    return data


def candidate(n=12, month="2026-09", snapshot="2026-10-26"):
    return {
        "schema_version": "nyc311-review-candidate-v1",
        "dataset_id": "erm2-nwe9",
        "snapshot_as_of": snapshot,
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10},
        "aggregates": [{
            "month": month, "borough": "QUEENS", "agency": "DOT",
            "problem": "SYNTHETIC-FICTIONAL", "requests": n,
            "closed_with_valid_interval": 0
        }]
    }


class PublicMarginalGateTests(unittest.TestCase):
    def test_clean_receipt_still_holds_not_release_approval(self):
        result = inspect_official_marginal_receipt(candidate(), source())
        self.assertIn("official_marginal_receipt_candidate_source_not_authenticated", result)
        self.assertIn("source_queries_not_atomic", result)
        self.assertIn("official_csv_origin_not_authenticated", result)
        self.assertNotIn("official_marginal_receipt_candidate_month_mismatch", result)

    def test_wrong_candidate_month(self):
        self.assertIn("official_marginal_receipt_candidate_month_mismatch",
                      inspect_official_marginal_receipt(candidate(month="2026-08"), source()))

    def test_mixed_candidate_months(self):
        p = candidate()
        p["aggregates"].append(dict(p["aggregates"][0], month="2026-10", problem="ANOTHER"))
        self.assertIn("official_marginal_receipt_candidate_month_mismatch",
                      inspect_official_marginal_receipt(p, source()))

    def test_empty_candidate_cannot_be_bound(self):
        p = candidate()
        p["aggregates"] = []
        self.assertIn("official_marginal_receipt_candidate_month_mismatch",
                      inspect_official_marginal_receipt(p, source()))

    def test_candidate_snapshot_before_month_end(self):
        self.assertIn("official_marginal_receipt_candidate_before_month_end",
                      inspect_official_marginal_receipt(candidate(snapshot="2026-09-29"), source()))

    def test_candidate_snapshot_on_month_end_is_not_early(self):
        self.assertNotIn("official_marginal_receipt_candidate_before_month_end",
                         inspect_official_marginal_receipt(candidate(snapshot="2026-09-30"), source()))

    def test_visible_candidate_above_official_cohort(self):
        self.assertIn("official_marginal_receipt_visible_candidate_exceeds_source",
                      inspect_official_marginal_receipt(candidate(n=21), source()))

    def test_visible_candidate_equal_to_cohort_not_disclosure_clearance(self):
        result = inspect_official_marginal_receipt(candidate(n=20), source())
        self.assertNotIn("official_marginal_receipt_visible_candidate_exceeds_source", result)
        self.assertIn("official_marginal_receipt_candidate_source_not_authenticated", result)

    def test_invalid_source_receipt_cannot_support_upper_bound(self):
        s = source()
        s["queries"]["status"]["rows"][0]["records"] = "999"
        result = inspect_official_marginal_receipt(candidate(n=21), s)
        self.assertIn("mismatched_status_marginal", result)
        self.assertNotIn("official_marginal_receipt_visible_candidate_exceeds_source", result)

    def test_missing_source_dimensions_fail_closed(self):
        s = source()
        del s["queries"]["borough"]
        self.assertIn("invalid_receipt_schema",
                      inspect_official_marginal_receipt(candidate(), s))

    def test_invalid_month_does_not_crash(self):
        s = source()
        s["reporting_month"] = "2026-13"
        result = inspect_official_marginal_receipt(candidate(), s)
        self.assertIn("official_marginal_receipt_invalid_month_or_snapshot", result)

    def test_missing_candidate_schema(self):
        p = candidate()
        del p["schema_version"]
        self.assertIn("official_marginal_receipt_requires_review_candidate",
                      inspect_official_marginal_receipt(p, source()))

    def test_invalid_candidate_snapshot(self):
        self.assertIn("official_marginal_receipt_invalid_month_or_snapshot",
                      inspect_official_marginal_receipt(candidate(snapshot="not-a-date"), source()))

    def test_non_object_receipt(self):
        self.assertIn("invalid_receipt_schema",
                      inspect_official_marginal_receipt(candidate(), ["not", "a", "receipt"]))

    def test_cli_rejects_unreadable_receipt_and_never_approves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c = root / "candidate.json"
            c.write_text(json.dumps(candidate()))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")),
                                  str(c), "--official-marginal-receipt", str(root / "absent.json")],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            output = json.loads(run.stdout)
            self.assertIn("unreadable_or_invalid_official_marginal_receipt", output["findings"])
            self.assertFalse(output["publication_approved"])

    def test_cli_reconciles_and_does_not_echo_source_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c, s = root / "candidate.json", root / "receipt.json"
            c.write_text(json.dumps(candidate(n=21)))
            s.write_text(json.dumps(source()))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")),
                                  str(c), "--official-marginal-receipt", str(s)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            output = json.loads(run.stdout)
            self.assertTrue(output["hold"])
            self.assertFalse(output["publication_approved"])
            self.assertIn("official_marginal_receipt_visible_candidate_exceeds_source", output["findings"])
            self.assertNotIn("SYNTHETIC-FICTIONAL", run.stdout)
            self.assertNotIn("QUEENS", run.stdout)
            self.assertNotIn("20", run.stdout)


if __name__ == "__main__":
    unittest.main()
