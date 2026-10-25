"""Synthetic-only CLI regression tests for exact 2x2 overlap release-gate wiring."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_external_marginal_audit import candidate, marginals
from test_overlap_integer_audit import sample

GATE = Path(__file__).with_name("release_privacy_gate.py")


def run_gate(payload, overlap=None, previous=None, external=None, malformed=None, missing=False):
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        path = folder / "candidate.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        command = [sys.executable, str(GATE), str(path)]
        if overlap is not None or malformed is not None or missing:
            overlap_path = folder / "overlap.json"
            if not missing:
                overlap_path.write_text(malformed if malformed is not None else json.dumps(overlap),
                                        encoding="utf-8")
            command.extend(["--overlap-constraints", str(overlap_path)])
        if previous is not None:
            prior = folder / "prior.json"
            prior.write_text(json.dumps(previous), encoding="utf-8")
            command.extend(["--previous", str(prior)])
        if external is not None:
            aux = folder / "external.json"
            aux.write_text(json.dumps(external), encoding="utf-8")
            command.extend(["--external-marginals", str(aux)])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, json.loads(result.stdout)


class OverlapGateIntegrationTests(unittest.TestCase):
    def test_unique_small_cell_reported(self):
        result, report = run_gate(candidate(), overlap=sample())
        self.assertEqual(result.returncode, 2)
        self.assertIn("small_integer_target_uniquely_reconstructible", report["findings"])
        self.assertFalse(report["publication_approved"])

    def test_nonunique_small_range_reported(self):
        p = sample()
        p["bounds"][0][1][0] = 0
        _, report = run_gate(candidate(), overlap=p)
        self.assertIn("integer_target_range_includes_small_cells", report["findings"])
        self.assertNotIn("small_integer_target_uniquely_reconstructible", report["findings"])

    def test_inconsistent_totals_reported(self):
        p = sample()
        p["column_totals"][1] += 1
        _, report = run_gate(candidate(), overlap=p)
        self.assertIn("inconsistent_overlap_totals", report["findings"])

    def test_infeasible_bounds_reported(self):
        p = sample()
        p["bounds"][0][1][0] = 25
        _, report = run_gate(candidate(), overlap=p)
        self.assertIn("infeasible_overlap_constraints", report["findings"])

    def test_bad_schema_fail_closed(self):
        p = sample()
        p["row_totals"][0] = True
        _, report = run_gate(candidate(), overlap=p)
        self.assertIn("invalid_overlap_integer_schema", report["findings"])

    def test_malformed_json_fail_closed(self):
        result, report = run_gate(candidate(), malformed="{not json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unreadable_or_invalid_overlap_constraints", report["findings"])

    def test_missing_file_fail_closed(self):
        result, report = run_gate(candidate(), missing=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unreadable_or_invalid_overlap_constraints", report["findings"])

    def test_non_candidate_cannot_invoke_overlap(self):
        p = copy.deepcopy(candidate())
        p.pop("schema_version")
        _, report = run_gate(p, overlap=sample())
        self.assertIn("overlap_constraints_require_review_candidate", report["findings"])
        self.assertNotIn("small_integer_target_uniquely_reconstructible", report["findings"])

    def test_model_alignment_is_always_unverified(self):
        p = sample()
        p["bounds"][0][0] = [0, 0]
        _, report = run_gate(candidate(), overlap=p)
        self.assertIn("overlap_constraints_alignment_unverified", report["findings"])
        self.assertFalse(report["publication_approved"])

    def test_temporal_and_overlap_findings_combine(self):
        previous = candidate()
        previous["snapshot_as_of"] = "2026-10-24"
        previous["aggregates"][0]["requests"] = 11
        _, report = run_gate(candidate(), overlap=sample(), previous=previous)
        self.assertIn("small_temporal_difference", report["findings"])
        self.assertIn("small_integer_target_uniquely_reconstructible", report["findings"])

    def test_external_and_overlap_findings_combine(self):
        _, report = run_gate(candidate(), overlap=sample(), external=marginals(15))
        self.assertIn("small_external_residual_reconstructible", report["findings"])
        self.assertIn("small_integer_target_uniquely_reconstructible", report["findings"])

    def test_private_counts_never_echoed(self):
        p = sample()
        p["row_totals"][0] += 987654321
        p["column_totals"][1] += 987654321
        p["bounds"][0][1][0] += 987654321
        result, report = run_gate(candidate(), overlap=p)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("987654321", result.stdout)
        self.assertNotIn('"row_totals"', result.stdout)
        self.assertFalse(report["publication_approved"])

    def test_no_overlap_preserves_prior_behavior(self):
        result, report = run_gate(candidate())
        self.assertEqual(result.returncode, 2)
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertNotIn("overlap_constraints_alignment_unverified", report["findings"])


if __name__ == "__main__":
    unittest.main()
