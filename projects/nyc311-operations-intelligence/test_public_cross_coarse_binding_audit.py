"""Synthetic-only tests for public 2D receipt ↔ private coarse source binding."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from public_cross_coarse_binding_audit import HOLDS, audit
from test_coarse_20cell_binding_audit import sample
from test_official_marginal_receipt import receipt
from test_cross_dimension_marginal_receipt import url


def fixture():
    binding = sample()
    base = receipt()
    rows = [{"borough": r["borough"], "agency": r["agency"],
             "records": str(r["requests"])} for r in binding["fine_rows"]]
    borough = defaultdict(int)
    agency = defaultdict(int)
    for r in rows:
        borough[r["borough"]] += int(r["records"])
        agency[r["agency"]] += int(r["records"])
    total = sum(borough.values())
    base["queries"]["cohort"]["rows"] = [{"records": str(total),
                                              "distinct_keys": str(total)}]
    base["queries"]["borough"]["rows"] = [
        {"borough": k, "records": str(v)} for k, v in sorted(borough.items())]
    base["queries"]["agency"]["rows"] = [
        {"agency": k, "records": str(v)} for k, v in sorted(agency.items())]
    base["queries"]["status"]["rows"] = [
        {"status": "Open", "records": str(total - 200)},
        {"status": "Closed", "records": "200"}]
    return binding, base, {"url": url(), "rows": rows}


class PublicCoarseBindingTests(unittest.TestCase):
    def setUp(self):
        self.binding, self.base, self.cross = fixture()

    def findings(self):
        return audit(self.binding, self.base, self.cross)

    def test_reconciled_fixture_retains_all_release_holds(self):
        self.assertEqual(self.findings(), sorted(HOLDS))

    def test_2x2_balanced_tamper_escapes_marginals_but_not_pair_audit(self):
        # Four changes preserve each borough and agency marginal.
        lookup = {(r["borough"], r["agency"]): r for r in self.cross["rows"]}
        for b, a, delta in (("BRONX", "Agency 0", 1),
                            ("BRONX", "Agency 1", -1),
                            ("BROOKLYN", "Agency 0", -1),
                            ("BROOKLYN", "Agency 1", 1)):
            r = lookup[(b, a)]
            r["records"] = str(int(r["records"]) + delta)
        issues = self.findings()
        self.assertIn("public_private_source_pair_count_mismatch", issues)
        self.assertIn("public_private_coarse_cell_mismatch", issues)
        self.assertNotIn("invalid_or_inconsistent_public_cross_receipt", issues)

    def test_source_total_drift_detected(self):
        self.binding["source_total_requests"] += 1
        issues = self.findings()
        self.assertIn("invalid_or_inconsistent_private_binding", issues)

    def test_public_missing_pair_fails_source_receipt(self):
        self.cross["rows"].pop()
        self.assertIn("invalid_or_inconsistent_public_cross_receipt", self.findings())

    def test_public_agency_mapping_must_be_exact(self):
        self.binding["agency_to_group"]["Agency 99"] = "Group A"
        self.assertIn("editorial_mapping_does_not_cover_public_agencies",
                      self.findings())

    def test_wrong_reporting_month(self):
        self.binding["month"] = "2026-08"
        self.assertIn("reporting_month_mismatch", self.findings())

    def test_premature_private_snapshot(self):
        self.binding["snapshot_as_of"] = "2026-09-15"
        self.assertIn("private_snapshot_before_month_end", self.findings())

    def test_official_title_case_boroughs_normalize_safely(self):
        for r in self.cross["rows"]:
            r["borough"] = r["borough"].title()
        for r in self.base["queries"]["borough"]["rows"]:
            r["borough"] = r["borough"].title()
        self.assertEqual(self.findings(), sorted(HOLDS))

    def test_case_normalization_collision_rejected(self):
        for r in self.cross["rows"]:
            if r["borough"] == "BRONX" and r["agency"] == "Agency 0":
                r["records"] = "10"
                self.cross["rows"].append(
                    {"borough": "Bronx", "agency": "Agency 0", "records": "10"})
                break
        old = next(r for r in self.base["queries"]["borough"]["rows"]
                   if r["borough"] == "BRONX")
        old["records"] = str(int(old["records"]) - 10)
        self.base["queries"]["borough"]["rows"].append(
            {"borough": "Bronx", "records": "10"})
        self.assertIn("borough_normalization_collision", self.findings())

    def test_unrecognized_public_borough_is_not_silently_coerced(self):
        for r in self.cross["rows"]:
            if r["borough"] == "BRONX":
                r["borough"] = "OTHER"
        for r in self.base["queries"]["borough"]["rows"]:
            if r["borough"] == "BRONX":
                r["borough"] = "OTHER"
        self.assertIn("unrecognized_public_borough", self.findings())

    def test_invalid_source_query_scope_stops_comparison(self):
        self.cross["url"] = self.cross["url"].replace("2026-09-01", "2026-08-01")
        self.assertIn("invalid_or_inconsistent_public_cross_receipt",
                      self.findings())

    def test_record_level_field_rejected(self):
        self.cross["rows"][0]["unique_key"] = "SYNTHETIC-PRIVATE"
        self.assertIn("invalid_or_inconsistent_public_cross_receipt",
                      self.findings())

    def test_invalid_private_group_rejected(self):
        self.binding["agency_to_group"]["Agency 0"] = "UNAPPROVED"
        self.assertIn("invalid_or_inconsistent_private_binding", self.findings())

    def test_private_pair_count_difference_after_self_consistent_change(self):
        self.binding["fine_rows"][0]["requests"] += 1
        self.binding["coarse_cells"][0]["requests"] += 1
        self.binding["source_total_requests"] += 1
        issues = self.findings()
        self.assertIn("public_private_source_pair_count_mismatch", issues)
        self.assertIn("public_private_coarse_cell_mismatch", issues)

    def test_cli_holds_and_does_not_echo_private_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [root / n for n in ("binding.json", "base.json", "cross.json")]
            self.binding["fine_rows"][0]["requests"] = 987654321
            for p, data in zip(paths, (self.binding, self.base, self.cross)):
                p.write_text(json.dumps(data), encoding="utf-8")
            run = subprocess.run([sys.executable,
                                  str(Path(__file__).with_name(
                                      "public_cross_coarse_binding_audit.py")),
                                  *(str(p) for p in paths)],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            result = json.loads(run.stdout)
            self.assertTrue(result["hold"])
            self.assertFalse(result["publication_approved"])
            for private in ("987654321", "Agency 0", "BRONX", "a" * 64):
                self.assertNotIn(private, run.stdout)


if __name__ == "__main__":
    unittest.main()
