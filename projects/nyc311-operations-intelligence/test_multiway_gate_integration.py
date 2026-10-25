"""Synthetic CLI regression tests for the unbound 20-cell private release gate."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_external_marginal_audit import candidate, marginals
from test_multiway_integer_audit import sample

GATE = Path(__file__).with_name("release_privacy_gate.py")


def run_gate(payload, multiway=None, malformed=None, missing=False, previous=None, external=None):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "candidate.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        cmd = [sys.executable, str(GATE), str(source)]
        if multiway is not None or malformed is not None or missing:
            constraints = root / "private_multiway.json"
            if not missing:
                constraints.write_text(
                    malformed if malformed is not None else json.dumps(multiway),
                    encoding="utf-8")
            cmd += ["--multiway-constraints", str(constraints)]
        if previous is not None:
            old = root / "previous.json"
            old.write_text(json.dumps(previous), encoding="utf-8")
            cmd += ["--previous", str(old)]
        if external is not None:
            aux = root / "external.json"
            aux.write_text(json.dumps(external), encoding="utf-8")
            cmd += ["--external-marginals", str(aux)]
        completed = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return completed, json.loads(completed.stdout)


class MultiwayGateIntegrationTests(unittest.TestCase):
    def test_forced_small_cells_are_detected(self):
        run, report = run_gate(candidate(), multiway=sample())
        self.assertEqual(run.returncode, 2)
        self.assertIn("small_multiway_target_forced_by_constraints", report["findings"])
        self.assertIn("multiway_constraints_alignment_unverified", report["findings"])
        self.assertFalse(report["publication_approved"])

    def test_nonunique_small_range_is_reported(self):
        constraints = sample()
        constraints["marginals"] = [{"cells": [0, 1], "total": 15}]
        constraints["targets"] = [0]
        _, report = run_gate(candidate(), multiway=constraints)
        self.assertIn("multiway_target_range_includes_small_cells", report["findings"])
        self.assertNotIn("small_multiway_target_forced_by_constraints", report["findings"])

    def test_fractional_only_solution_fails_closed(self):
        constraints = sample()
        for row in constraints["marginals"]:
            row["total"] = 1
        _, report = run_gate(candidate(), multiway=constraints)
        self.assertIn("infeasible_multiway_integer_constraints", report["findings"])

    def test_unauthenticated_structural_zeros_are_not_assumed(self):
        constraints = sample()
        constraints["marginals"] = [{"cells": [0, 1], "total": 15}]
        constraints["targets"] = [0]
        constraints["structural_zero_claims"] = [0]
        _, report = run_gate(candidate(), multiway=constraints)
        self.assertIn("structural_zero_claims_not_authenticated", report["findings"])
        self.assertNotIn("multiway_target_forced_by_constraints", report["findings"])

    def test_incomplete_20_cell_coverage_is_reported(self):
        _, report = run_gate(candidate(), multiway=sample())
        self.assertIn("incomplete_multiway_cell_coverage", report["findings"])

    def test_full_20_cell_coverage_is_not_clearance(self):
        constraints = sample()
        constraints["marginals"] = [{"cells": list(range(20)), "total": 200}]
        constraints["targets"] = [19]
        _, report = run_gate(candidate(), multiway=constraints)
        self.assertNotIn("incomplete_multiway_cell_coverage", report["findings"])
        self.assertIn("candidate_20cell_alignment_unverified", report["findings"])
        self.assertFalse(report["publication_approved"])

    def test_invalid_schema_fails_closed(self):
        constraints = sample()
        constraints["bounds"][0] = [10, 9]
        _, report = run_gate(candidate(), multiway=constraints)
        self.assertIn("invalid_multiway_integer_schema", report["findings"])

    def test_malformed_json_fails_closed(self):
        run, report = run_gate(candidate(), malformed="{bad")
        self.assertEqual(run.returncode, 2)
        self.assertIn("unreadable_or_invalid_multiway_constraints", report["findings"])

    def test_missing_file_fails_closed(self):
        run, report = run_gate(candidate(), missing=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn("unreadable_or_invalid_multiway_constraints", report["findings"])

    def test_legacy_payload_cannot_run_multiway(self):
        payload = copy.deepcopy(candidate())
        payload.pop("schema_version")
        _, report = run_gate(payload, multiway=sample())
        self.assertIn("multiway_constraints_require_review_candidate", report["findings"])
        self.assertNotIn("small_multiway_target_forced_by_constraints", report["findings"])

    def test_combines_temporal_and_multiway_findings(self):
        previous = candidate()
        previous["snapshot_as_of"] = "2026-10-24"
        previous["aggregates"][0]["requests"] = 11
        _, report = run_gate(candidate(), multiway=sample(), previous=previous)
        self.assertIn("small_temporal_difference", report["findings"])
        self.assertIn("small_multiway_target_forced_by_constraints", report["findings"])

    def test_combines_external_and_multiway_findings(self):
        _, report = run_gate(candidate(), multiway=sample(), external=marginals(15))
        self.assertIn("small_external_residual_reconstructible", report["findings"])
        self.assertIn("small_multiway_target_forced_by_constraints", report["findings"])

    def test_sensitive_private_totals_not_echoed(self):
        constraints = sample()
        constraints["marginals"] = [{"cells": [0], "total": 987654321}]
        run, report = run_gate(candidate(), multiway=constraints)
        self.assertEqual(run.returncode, 2)
        self.assertNotIn("987654321", run.stdout)
        self.assertNotIn('"total"', run.stdout)
        self.assertFalse(report["publication_approved"])

    def test_no_multiway_option_preserves_prior_behavior(self):
        run, report = run_gate(candidate())
        self.assertEqual(run.returncode, 2)
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertNotIn("multiway_constraints_alignment_unverified", report["findings"])


if __name__ == "__main__":
    unittest.main()
