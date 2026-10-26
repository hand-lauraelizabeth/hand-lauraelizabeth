"""Synthetic-only tests for candidate-to-20-cell source alignment.

Never use actual NYC 311 records, agency counts, source hashes, or identifiers.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from candidate_coarse_alignment_audit import audit
from test_coarse_20cell_binding_audit import sample

SCRIPT = Path(__file__).with_name("candidate_coarse_alignment_audit.py")


def candidate():
    manifest = sample()
    return {
        "schema_version": "nyc311-review-candidate-v1",
        "dataset_id": "erm2-nwe9",
        "snapshot_as_of": manifest["snapshot_as_of"],
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10},
        "aggregates": [
            {"month": manifest["month"], "borough": row["borough"],
             "agency": row["agency"], "problem": "Fictional type",
             "requests": row["requests"], "closed_with_valid_interval": None}
            for row in manifest["fine_rows"] if row["borough"] != "UNSPECIFIED"
        ],
    }


class CandidateCoarseAlignmentTests(unittest.TestCase):
    def test_exact_synthetic_alignment_still_cannot_clear_release(self):
        findings = audit(candidate(), sample())
        self.assertEqual(findings, [
            "candidate_source_provenance_not_authenticated",
            "external_marginals_and_temporal_disclosure_pending",
        ])

    def test_missing_visible_agency_is_reported(self):
        c = candidate()
        c["aggregates"].pop(0)
        f = audit(c, sample())
        self.assertIn("source_agency_missing_from_candidate", f)
        self.assertIn("candidate_source_coverage_incomplete", f)
        self.assertIn("candidate_coarse_cell_undercovered", f)

    def test_small_residual_is_flagged(self):
        c = candidate()
        c["aggregates"][0]["requests"] -= 1
        f = audit(c, sample())
        self.assertIn("small_unpublished_source_residual", f)
        self.assertIn("candidate_source_coverage_incomplete", f)

    def test_candidate_overage_detected_at_both_grains(self):
        c = candidate()
        c["aggregates"][0]["requests"] += 1
        f = audit(c, sample())
        self.assertIn("candidate_agency_total_exceeds_source", f)
        self.assertIn("candidate_coarse_cell_exceeds_source", f)

    def test_balanced_cross_cell_tamper_detected(self):
        c = candidate()
        c["aggregates"][0]["requests"] += 1
        c["aggregates"][1]["requests"] -= 1
        f = audit(c, sample())
        self.assertIn("candidate_agency_total_exceeds_source", f)
        self.assertIn("candidate_source_coverage_incomplete", f)

    def test_split_problem_categories_sum_correctly(self):
        c = candidate()
        row = c["aggregates"][0]
        row["requests"] = 10
        second = copy.deepcopy(row)
        second["problem"] = "Fictional type B"
        second["requests"] = 10
        c["aggregates"].append(second)
        self.assertNotIn("candidate_source_coverage_incomplete", audit(c, sample()))

    def test_balanced_same_agency_problem_changes_are_not_misrepresented_as_detected(self):
        c = candidate()
        row = c["aggregates"][0]
        row["requests"] = 10
        second = copy.deepcopy(row)
        second["problem"] = "Fictional type B"
        second["requests"] = 10
        c["aggregates"].append(second)
        # Two valid partitions of 20 have the same aggregate; provenance hold remains.
        f = audit(c, sample())
        self.assertIn("candidate_source_provenance_not_authenticated", f)

    def test_wrong_month_is_not_silently_included(self):
        c = candidate()
        c["aggregates"][0]["month"] = "2026-10"
        f = audit(c, sample())
        self.assertIn("candidate_source_month_mismatch", f)
        self.assertIn("candidate_source_coverage_incomplete", f)

    def test_wrong_snapshot_flagged(self):
        c = candidate()
        c["snapshot_as_of"] = "2026-10-26"
        self.assertIn("candidate_source_snapshot_mismatch", audit(c, sample()))

    def test_wrong_dataset_flagged(self):
        c = candidate()
        c["dataset_id"] = "not-erm2-nwe9"
        self.assertIn("candidate_source_dataset_mismatch", audit(c, sample()))

    def test_unexpected_candidate_agency_detected(self):
        c = candidate()
        c["aggregates"][0]["agency"] = "FICTIONAL NEW AGENCY"
        self.assertIn("candidate_agency_not_in_source_binding", audit(c, sample()))

    def test_excluded_borough_cannot_be_published(self):
        c = candidate()
        c["aggregates"][0]["borough"] = "UNSPECIFIED"
        self.assertIn("candidate_excluded_or_unexpected_borough", audit(c, sample()))

    def test_inconsistent_source_manifest_rejected(self):
        m = sample()
        m["coarse_cells"][0]["requests"] += 1
        self.assertEqual(audit(candidate(), m), ["invalid_or_inconsistent_source_binding"])

    def test_malformed_source_manifest_rejected(self):
        m = sample()
        m["fine_rows"][0]["requests"] = True
        self.assertEqual(audit(candidate(), m), ["invalid_or_inconsistent_source_binding"])

    def test_unsafe_candidate_rejected(self):
        c = candidate()
        c["aggregates"][0]["requests"] = 3
        self.assertEqual(audit(c, sample()), ["invalid_or_unsafe_review_candidate"])

    def test_duplicate_candidate_group_rejected(self):
        c = candidate()
        c["aggregates"].append(copy.deepcopy(c["aggregates"][0]))
        self.assertEqual(audit(c, sample()), ["invalid_or_unsafe_review_candidate"])

    def test_cli_never_echoes_private_data_and_stays_on_hold(self):
        c, m = candidate(), sample()
        m["agency_to_group"]["SECRET-AGENCY-XYZ"] = "Group A"
        with tempfile.TemporaryDirectory() as td:
            p, q = Path(td) / "candidate.json", Path(td) / "manifest.json"
            p.write_text(json.dumps(c), encoding="utf-8")
            q.write_text(json.dumps(m), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), str(p), str(q)],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 2)
            report = json.loads(proc.stdout)
            self.assertTrue(report["hold"])
            self.assertFalse(report["publication_approved"])
            for private in ("SECRET-AGENCY-XYZ", "Fictional type", "Group A",
                            "source_sha256", "433", "Agency 0"):
                self.assertNotIn(private, proc.stdout)

    def test_cli_malformed_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p, q = Path(td) / "candidate.json", Path(td) / "manifest.json"
            p.write_text("{bad", encoding="utf-8")
            q.write_text(json.dumps(sample()), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(SCRIPT), str(p), str(q)],
                                  capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 2)
            self.assertIn("unreadable_or_invalid_candidate_source_pair",
                          json.loads(proc.stdout)["findings"])


if __name__ == "__main__":
    unittest.main()
