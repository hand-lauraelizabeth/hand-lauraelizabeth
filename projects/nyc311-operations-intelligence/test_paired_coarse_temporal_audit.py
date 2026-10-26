"""Adversarial synthetic regression tests for paired 20-cell temporal QA."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from paired_coarse_temporal_audit import audit
from test_coarse_20cell_binding_audit import sample

CLI = Path(__file__).with_name("paired_coarse_temporal_audit.py")


def pair():
    old = sample()
    new = copy.deepcopy(old)
    new["snapshot_as_of"] = "2026-10-26"
    new["source_sha256"] = "b" * 64
    return old, new


def change(p, delta, borough="BRONX", agency="Agency 0", group="Group A"):
    next(r for r in p["fine_rows"] if r["borough"] == borough
         and r["agency"] == agency)["requests"] += delta
    next(r for r in p["coarse_cells"] if r["borough"] == borough
         and r["group"] == group)["requests"] += delta
    p["source_total_requests"] += delta


class PairedCoarseTemporalTests(unittest.TestCase):
    def test_unchanged_snapshots_still_hold(self):
        old, new = pair()
        issues = audit(old, new)
        self.assertIn("source_identity_cohort_not_reconciled", issues)
        self.assertIn("temporal_privacy_clearance_pending", issues)
        self.assertNotIn("small_published_coarse_difference", issues)

    def test_small_positive_coarse_delta(self):
        old, new = pair()
        change(new, 1)
        self.assertIn("small_published_coarse_difference", audit(old, new))

    def test_small_negative_coarse_delta(self):
        old, new = pair()
        change(new, -1)
        issues = audit(old, new)
        self.assertIn("small_published_coarse_difference", issues)
        self.assertIn("decreasing_coarse_cell_revision", issues)

    def test_large_delta_not_falsely_small(self):
        old, new = pair()
        change(new, 10)
        self.assertNotIn("small_published_coarse_difference", audit(old, new))

    def test_mixed_deltas_cannot_cancel(self):
        old, new = pair()
        change(new, 1)
        change(new, -1, "BROOKLYN")
        issues = audit(old, new)
        self.assertIn("small_published_coarse_difference", issues)
        self.assertIn("decreasing_coarse_cell_revision", issues)
        self.assertNotIn("small_source_total_difference", issues)

    def test_fine_redistribution_hidden_under_coarse_total(self):
        old, new = pair()
        for p in (old, new):
            p["agency_to_group"]["Agency 4"] = "Group A"
            p["fine_rows"].append({"borough": "BRONX", "agency": "Agency 4",
                                   "requests": 0})
        next(r for r in new["fine_rows"] if r["borough"] == "BRONX"
             and r["agency"] == "Agency 0")["requests"] -= 1
        next(r for r in new["fine_rows"] if r["borough"] == "BRONX"
             and r["agency"] == "Agency 4")["requests"] += 1
        issues = audit(old, new)
        self.assertIn("fine_redistribution_masked_by_stable_coarse_totals", issues)
        self.assertIn("small_fine_source_difference", issues)
        self.assertNotIn("small_published_coarse_difference", issues)

    def test_fine_support_drift(self):
        old, new = pair()
        new["fine_rows"][0]["agency"] = "Agency 4"
        new["agency_to_group"]["Agency 4"] = "Group A"
        # Definitions changed as well; fail closed before comparing.
        self.assertIn("editorial_group_definition_changed", audit(old, new))

    def test_mapping_drift(self):
        old, new = pair()
        new["agency_to_group"]["Agency 0"] = "Group B"
        self.assertIn("editorial_group_definition_changed", audit(old, new))

    def test_group_label_reordering_is_not_silently_accepted(self):
        old, new = pair()
        new["group_labels"].reverse()
        self.assertIn("editorial_group_definition_changed", audit(old, new))

    def test_wrong_month(self):
        old, new = pair()
        new["month"] = "2026-10"
        self.assertIn("incompatible_paired_cohort", audit(old, new))

    def test_same_date_is_not_a_valid_order(self):
        old, new = pair()
        new["snapshot_as_of"] = old["snapshot_as_of"]
        self.assertIn("nonincreasing_snapshot_order", audit(old, new))

    def test_reverse_date_order(self):
        old, new = pair()
        new["snapshot_as_of"] = "2026-10-24"
        self.assertIn("nonincreasing_snapshot_order", audit(old, new))

    def test_invalid_manifest_fails_closed(self):
        old, new = pair()
        new["coarse_cells"].pop()
        self.assertIn("inconsistent_paired_coarse_manifest", audit(old, new))

    def test_small_excluded_borough_delta(self):
        old, new = pair()
        new["fine_rows"][-1]["requests"] += 1
        new["excluded_requests"] += 1
        new["source_total_requests"] += 1
        self.assertIn("small_excluded_borough_difference", audit(old, new))

    def test_identical_digest_with_changed_aggregate(self):
        old, new = pair()
        change(new, 1)
        new["source_sha256"] = old["source_sha256"]
        self.assertIn("identical_digest_conflicts_with_changed_aggregates", audit(old, new))

    def test_private_counts_and_agencies_not_echoed(self):
        old, new = pair()
        change(new, 1)
        new["agency_to_group"]["SECRET-AGENCY-XYZ"] = "Group A"
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "old.json", Path(td) / "new.json"
            a.write_text(json.dumps(old), encoding="utf-8")
            b.write_text(json.dumps(new), encoding="utf-8")
            run = subprocess.run([sys.executable, str(CLI), str(a), str(b)],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        report = json.loads(run.stdout)
        self.assertTrue(report["hold"])
        self.assertFalse(report["publication_approved"])
        for secret in ("SECRET-AGENCY-XYZ", "433", "Agency 0", "source_sha256"):
            self.assertNotIn(secret, run.stdout)

    def test_unreadable_manifest_cli_holds(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "old.json", Path(td) / "missing.json"
            a.write_text("{invalid json", encoding="utf-8")
            run = subprocess.run([sys.executable, str(CLI), str(a), str(b)],
                                 capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn("unreadable_or_invalid_paired_coarse_manifest",
                      json.loads(run.stdout)["findings"])


if __name__ == "__main__":
    unittest.main()
