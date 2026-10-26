"""Synthetic-only tests for 2D public source bounds in the private release gate."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from release_privacy_gate import inspect_cross_dimension_receipt
from test_official_marginal_receipt import receipt
from test_cross_dimension_marginal_receipt import url
from test_official_marginal_gate import candidate


def source():
    s = receipt()
    s["queries"]["cohort"]["rows"] = [{"records": "60", "distinct_keys": "60"}]
    for dimension in ("borough", "agency", "status"):
        for row in s["queries"][dimension]["rows"]:
            row["records"] = "30"
    return s


def cross():
    return {"url": url(), "rows": [
        {"borough": b, "agency": a, "records": "15"}
        for b in ("QUEENS", "BRONX") for a in ("SYNTHETIC-A", "SYNTHETIC-B")
    ]}


def review_candidate(n=12):
    p = candidate(n)
    p["aggregates"][0]["agency"] = "SYNTHETIC-A"
    return p


class CrossDimensionGateTests(unittest.TestCase):
    def setUp(self):
        self.p = review_candidate()
        self.s = source()
        self.x = cross()

    def findings(self):
        return inspect_cross_dimension_receipt(self.p, self.s, self.x)

    def test_matching_pair_still_holds(self):
        result = self.findings()
        self.assertIn("cross_dimension_candidate_source_not_authenticated", result)
        self.assertIn("cross_query_not_atomic", result)
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)

    def test_pair_over_source_bound(self):
        self.p["aggregates"][0]["requests"] = 16
        self.assertIn("cross_dimension_candidate_pair_exceeds_source", self.findings())

    def test_multiple_problem_groups_accumulate_by_pair(self):
        self.p["aggregates"].append(dict(self.p["aggregates"][0], problem="SECOND-SYNTHETIC"))
        self.assertIn("cross_dimension_candidate_pair_exceeds_source", self.findings())

    def test_pair_equal_to_source_is_not_clearance(self):
        self.p["aggregates"][0]["requests"] = 15
        result = self.findings()
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)
        self.assertIn("cross_cells_not_independently_authenticated", result)

    def test_unknown_candidate_pair(self):
        self.p["aggregates"][0]["agency"] = "SYNTHETIC-UNKNOWN"
        self.assertIn("cross_dimension_candidate_pair_absent_from_source", self.findings())

    def test_invalid_cross_scope_disables_bound(self):
        self.x["url"] = self.x["url"].replace("2026-09-01", "2026-08-01")
        self.p["aggregates"][0]["requests"] = 16
        result = self.findings()
        self.assertIn("cross_query_scope_invalid", result)
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)

    def test_invalid_one_dim_source_disables_bound(self):
        self.s["queries"]["status"]["rows"][0]["records"] = "31"
        self.p["aggregates"][0]["requests"] = 16
        result = self.findings()
        self.assertIn("base_marginals_invalid", result)
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)

    def test_inconsistent_cross_marginal_disables_bound(self):
        self.x["rows"][0]["records"] = "16"
        result = self.findings()
        self.assertIn("cross_borough_marginal_mismatch", result)
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)

    def test_wrong_candidate_month_disables_bound(self):
        self.p["aggregates"][0]["month"] = "2026-08"
        self.p["aggregates"][0]["requests"] = 16
        result = self.findings()
        self.assertIn("official_marginal_receipt_candidate_month_mismatch", result)
        self.assertNotIn("cross_dimension_candidate_pair_exceeds_source", result)

    def test_invalid_candidate_schema_disables_bound(self):
        self.p["aggregates"][0]["unique_key"] = "PRIVATE-SYNTHETIC"
        result = self.findings()
        self.assertIn("cross_dimension_requires_valid_review_candidate", result)

    def test_non_object_candidate_fails_closed(self):
        self.p = []
        self.assertIn("cross_dimension_requires_valid_review_candidate", self.findings())

    def test_missing_cross_rows_fails_closed(self):
        self.x = {"url": url()}
        self.assertIn("cross_response_invalid", self.findings())

    def test_cli_requires_base_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c = root / "candidate.json"
            x = root / "cross.json"
            c.write_text(json.dumps(self.p))
            x.write_text(json.dumps(self.x))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")),
                                  str(c), "--borough-agency-cross-receipt", str(x)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            data = json.loads(run.stdout)
            self.assertIn("cross_dimension_requires_official_marginal_receipt", data["findings"])
            self.assertFalse(data["publication_approved"])

    def test_cli_detects_pair_overbound_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c, s, x = (root / name for name in ("candidate.json", "base.json", "cross.json"))
            self.p["aggregates"][0]["requests"] = 16
            c.write_text(json.dumps(self.p))
            s.write_text(json.dumps(self.s))
            x.write_text(json.dumps(self.x))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")),
                                  str(c), "--official-marginal-receipt", str(s),
                                  "--borough-agency-cross-receipt", str(x)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            data = json.loads(run.stdout)
            self.assertIn("cross_dimension_candidate_pair_exceeds_source", data["findings"])
            self.assertTrue(data["hold"])
            self.assertFalse(data["publication_approved"])
            self.assertNotIn("SYNTHETIC-A", run.stdout)
            self.assertNotIn("QUEENS", run.stdout)

    def test_cli_unreadable_cross_receipt_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            c, s = root / "candidate.json", root / "base.json"
            c.write_text(json.dumps(self.p))
            s.write_text(json.dumps(self.s))
            run = subprocess.run([sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")),
                                  str(c), "--official-marginal-receipt", str(s),
                                  "--borough-agency-cross-receipt", str(root / "missing.json")],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn("unreadable_or_invalid_cross_dimension_receipt",
                          json.loads(run.stdout)["findings"])


if __name__ == "__main__":
    unittest.main()
