"""Synthetic regression tests for all-pairs 20-cell release-history QA."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from coarse_release_history_audit import HOLDS, audit
from test_coarse_20cell_binding_audit import sample

ROOT = Path(__file__).parent


def history():
    out = []
    for day, digest in ((25, "a"), (26, "b"), (27, "c")):
        item = sample()
        item["snapshot_as_of"] = "2026-10-%02d" % day
        item["source_sha256"] = digest * 64
        out.append(item)
    return out


def change(item, delta):
    item["fine_rows"][0]["requests"] += delta
    item["coarse_cells"][0]["requests"] += delta
    item["source_total_requests"] += delta


class CoarseReleaseHistoryTests(unittest.TestCase):
    def test_three_stable_snapshots_still_hold(self):
        findings = audit(history())
        self.assertEqual(findings, sorted(HOLDS))

    def test_nonadjacent_small_difference_hidden_by_large_adjacent_deltas(self):
        items = history()
        change(items[1], 20)
        change(items[2], 1)
        findings = audit(items)
        self.assertIn("nonadjacent_small_published_coarse_difference", findings)
        self.assertIn("nonadjacent_small_fine_source_difference", findings)
        self.assertNotIn("adjacent_small_published_coarse_difference", findings)
        self.assertNotIn("adjacent_small_fine_source_difference", findings)

    def test_adjacent_small_difference(self):
        items = history()
        change(items[1], 1)
        self.assertIn("adjacent_small_published_coarse_difference", audit(items))

    def test_nonadjacent_identical_digest_changed_counts(self):
        items = history()
        change(items[2], 1)
        items[2]["source_sha256"] = items[0]["source_sha256"]
        self.assertIn(
            "nonadjacent_identical_digest_conflicts_with_changed_aggregates",
            audit(items))

    def test_malformed_manifest_rejected(self):
        items = history()
        items[1]["coarse_cells"].pop()
        self.assertIn("invalid_history_manifest", audit(items))

    def test_inconsistent_private_total_rejected(self):
        items = history()
        items[1]["source_total_requests"] += 1
        self.assertIn("invalid_history_manifest", audit(items))

    def test_month_change_rejected(self):
        items = history()
        items[1]["month"] = "2026-10"
        self.assertIn("history_cohort_changed", audit(items))

    def test_mapping_change_rejected(self):
        items = history()
        items[1]["agency_to_group"]["Agency 0"] = "Group B"
        self.assertIn("history_editorial_definitions_changed", audit(items))

    def test_label_order_change_rejected(self):
        items = history()
        items[1]["group_labels"].reverse()
        self.assertIn("history_editorial_definitions_changed", audit(items))

    def test_duplicate_or_reverse_dates_rejected(self):
        items = history()
        items[1]["snapshot_as_of"] = items[0]["snapshot_as_of"]
        self.assertIn("history_snapshot_order_invalid", audit(items))
        items = history()
        items[2]["snapshot_as_of"] = "2026-10-24"
        self.assertIn("history_snapshot_order_invalid", audit(items))

    def test_incomplete_september_snapshot_rejected(self):
        items = history()
        items[0]["snapshot_as_of"] = "2026-09-30"
        self.assertIn("history_snapshot_before_month_close", audit(items))

    def test_december_to_january_boundary(self):
        items = history()
        for item, day in zip(items, (1, 2, 3)):
            item["month"] = "2026-12"
            item["snapshot_as_of"] = "2027-01-%02d" % day
        self.assertEqual(audit(items), sorted(HOLDS))
        items[0]["snapshot_as_of"] = "2026-12-31"
        self.assertIn("history_snapshot_before_month_close", audit(items))

    def test_same_month_snapshot_before_close_rejected(self):
        items = history()
        for item, day in zip(items, (29, 30, 31)):
            item["month"] = "2026-10"
            item["snapshot_as_of"] = "2026-10-%02d" % day
        self.assertIn("history_snapshot_before_month_close", audit(items))

    def test_invalid_history_shapes(self):
        for items in (None, {}, [], [sample()], [sample()] * 25,
                      [sample(), "not a manifest"]):
            self.assertTrue(any(x.startswith("invalid_") for x in audit(items)))

    def test_history_cli_fail_closed_and_no_source_values(self):
        items = history()
        change(items[2], 1)
        items[2]["fine_rows"][0]["agency"] = "PRIVATE-AGENCY-XYZ"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "private.json"
            path.write_text(json.dumps(items), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "coarse_release_history_audit.py"),
                 str(path)], capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2, run.stderr)
        response = json.loads(run.stdout)
        self.assertTrue(response["hold"])
        self.assertFalse(response["publication_approved"])
        for private in ("PRIVATE-AGENCY-XYZ", "Agency 0", "433", "a" * 64):
            self.assertNotIn(private, run.stdout)

    def test_release_gate_history_integration(self):
        items = history()
        change(items[1], 20)
        change(items[2], 1)
        candidate = {
            "schema_version": "nyc311-review-candidate-v1",
            "dataset_id": "erm2-nwe9",
            "snapshot_as_of": "2026-10-27",
            "rules": {
                "grain": "month × borough × agency × original API complaint_type",
                "display_minimum_cell_count": 10,
            },
            "aggregates": [{
                "month": "2026-09", "borough": "BRONX",
                "agency": "Agency 0", "problem": "Synthetic",
                "requests": 20, "closed_with_valid_interval": 0,
            }],
        }
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td) / "candidate.json", Path(td) / "history.json"
            a.write_text(json.dumps(candidate), encoding="utf-8")
            b.write_text(json.dumps(items), encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "release_privacy_gate.py"),
                 str(a), "--coarse-history", str(b)],
                capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2, run.stderr)
        response = json.loads(run.stdout)
        self.assertFalse(response["publication_approved"])
        self.assertIn("nonadjacent_small_published_coarse_difference",
                      response["findings"])
        self.assertIn("coarse_history_candidate_alignment_unverified",
                      response["findings"])


if __name__ == "__main__":
    unittest.main()
