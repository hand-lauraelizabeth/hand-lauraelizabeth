"""Synthetic-only adversarial tests for 311 coarse-candidate binding."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coarse_20cell_binding_audit import audit

SHA = "a" * 64


def sample():
    groups = ["Group A", "Group B", "Group C", "Group D"]
    boroughs = ["BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"]
    fine = [{"borough": b, "agency": f"Agency {i}", "requests": 20 + i}
            for b in boroughs for i in range(4)]
    fine.append({"borough": "UNSPECIFIED", "agency": "Agency 0", "requests": 3})
    return {
        "schema_version": "nyc311-coarse-binding-review-v1",
        "dataset_id": "erm2-nwe9", "month": "2026-09",
        "snapshot_as_of": "2026-10-25", "source_sha256": SHA,
        "group_labels": groups,
        "agency_to_group": {f"Agency {i}": groups[i] for i in range(4)},
        "fine_rows": fine,
        "coarse_cells": [{"borough": b, "group": groups[i], "requests": 20 + i}
                         for b in boroughs for i in range(4)],
        "excluded_requests": 3, "source_total_requests": 433,
    }


class CoarseBindingTests(unittest.TestCase):
    def test_reconciled_synthetic_20_cell_grid_is_still_on_hold(self):
        issues = audit(sample(), SHA)
        self.assertNotIn("coarse_counts_do_not_reconcile", issues)
        self.assertNotIn("source_digest_mismatch", issues)
        self.assertIn("source_provenance_not_authenticated", issues)
        self.assertIn("public_auxiliary_marginals_not_reconciled", issues)

    def test_missing_independent_digest_is_explicit(self):
        self.assertIn("independent_source_digest_not_supplied", audit(sample()))

    def test_independent_digest_mismatch(self):
        self.assertIn("source_digest_mismatch", audit(sample(), "b" * 64))

    def test_invalid_expected_digest(self):
        self.assertIn("invalid_expected_source_digest", audit(sample(), "unverified"))

    def test_one_cell_tamper_detected(self):
        p = sample()
        p["coarse_cells"][0]["requests"] += 1
        self.assertIn("coarse_counts_do_not_reconcile", audit(p, SHA))

    def test_balanced_cross_cell_tamper_detected(self):
        p = sample()
        p["coarse_cells"][0]["requests"] += 1
        p["coarse_cells"][1]["requests"] -= 1
        self.assertIn("coarse_counts_do_not_reconcile", audit(p, SHA))

    def test_missing_cell_fails_grid(self):
        p = sample()
        p["coarse_cells"].pop()
        self.assertIn("incomplete_or_extra_coarse_grid", audit(p, SHA))

    def test_duplicate_cell_fails_grid(self):
        p = sample()
        p["coarse_cells"][-1] = copy.deepcopy(p["coarse_cells"][0])
        issues = audit(p, SHA)
        self.assertIn("duplicate_coarse_cell", issues)
        self.assertIn("incomplete_or_extra_coarse_grid", issues)

    def test_unknown_agency_never_silently_dropped(self):
        p = sample()
        p["fine_rows"][0]["agency"] = "New agency"
        self.assertIn("unmapped_source_agency", audit(p, SHA))

    def test_duplicate_fine_group_detected(self):
        p = sample()
        p["fine_rows"].append(copy.deepcopy(p["fine_rows"][0]))
        self.assertIn("duplicate_fine_group", audit(p, SHA))

    def test_unexpected_borough_detected(self):
        p = sample()
        p["fine_rows"][0]["borough"] = "UNKNOWN BOROUGH"
        self.assertIn("unexpected_source_borough", audit(p, SHA))

    def test_excluded_borough_reconciliation(self):
        p = sample()
        p["excluded_requests"] = 0
        self.assertIn("excluded_borough_count_mismatch", audit(p, SHA))

    def test_total_reconciliation(self):
        p = sample()
        p["source_total_requests"] += 1
        self.assertIn("source_total_count_mismatch", audit(p, SHA))

    def test_unsafe_small_coarse_cell_detected(self):
        p = sample()
        p["fine_rows"][0]["requests"] = 3
        p["coarse_cells"][0]["requests"] = 3
        p["source_total_requests"] -= 17
        self.assertIn("coarse_cell_below_display_threshold", audit(p, SHA))

    def test_boolean_and_extra_field_rejected(self):
        for key in ("fine_rows", "coarse_cells"):
            p = sample()
            p[key][0]["requests"] = True
            self.assertEqual(audit(p, SHA), ["invalid_coarse_binding_schema"])
        p = sample()
        p["secret_private_field"] = 1
        self.assertEqual(audit(p, SHA), ["invalid_coarse_binding_schema"])

    def test_duplicate_editorial_labels_rejected(self):
        p = sample()
        p["group_labels"][1] = p["group_labels"][0]
        self.assertEqual(audit(p, SHA), ["invalid_coarse_binding_schema"])

    def test_bad_month_or_snapshot_rejected(self):
        for field, bad in (("month", "2026-13"), ("snapshot_as_of", "2026-02-30")):
            p = sample()
            p[field] = bad
            self.assertEqual(audit(p, SHA), ["invalid_coarse_binding_schema"])

    def test_cli_fail_closed_and_no_private_counts(self):
        p = sample()
        p["fine_rows"][0]["requests"] = 987654321
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.json"
            path.write_text(json.dumps(p), encoding="utf-8")
            run = subprocess.run([sys.executable,
                                  str(Path(__file__).with_name("coarse_20cell_binding_audit.py")),
                                  str(path), "--expected-source-sha256", SHA],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2)
            report = json.loads(run.stdout)
            self.assertTrue(report["hold"])
            self.assertFalse(report["publication_approved"])
            self.assertNotIn("987654321", run.stdout)
            self.assertNotIn(SHA, run.stdout)
            self.assertNotIn("Agency", run.stdout)


if __name__ == "__main__":
    unittest.main()
