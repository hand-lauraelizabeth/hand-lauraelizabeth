"""Synthetic-only CLI integration checks for private cross-table disclosure QA."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_external_marginal_audit import candidate, marginals

GATE = Path(__file__).with_name("release_privacy_gate.py")


def run_gate(payload, external=None, previous=None, invalid_external=None):
    with tempfile.TemporaryDirectory() as folder:
        directory = Path(folder)
        source = directory / "candidate.json"
        source.write_text(json.dumps(payload), encoding="utf-8")
        command = [sys.executable, str(GATE), str(source)]
        if previous is not None:
            previous_path = directory / "previous.json"
            previous_path.write_text(json.dumps(previous), encoding="utf-8")
            command.extend(["--previous", str(previous_path)])
        if external is not None or invalid_external is not None:
            external_path = directory / "marginals.json"
            external_path.write_text(
                invalid_external if invalid_external is not None else json.dumps(external),
                encoding="utf-8")
            command.extend(["--external-marginals", str(external_path)])
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result, json.loads(result.stdout)


class ExternalMarginalGateIntegration(unittest.TestCase):
    def test_small_residual_blocks_review(self):
        result, report = run_gate(candidate(), marginals(15))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(report["hold"])
        self.assertFalse(report["publication_approved"])
        self.assertIn("small_external_residual_reconstructible", report["findings"])

    def test_zero_residual_does_not_approve_publication(self):
        result, report = run_gate(candidate(), marginals(12))
        self.assertEqual(result.returncode, 2)
        self.assertIn("cross_table_and_auxiliary_inference_review_pending", report["findings"])
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertFalse(report["publication_approved"])

    def test_combined_temporal_and_external_findings(self):
        previous = candidate()
        previous["snapshot_as_of"] = "2026-10-24"
        previous["aggregates"][0]["requests"] = 11
        result, report = run_gate(candidate(), marginals(15), previous=previous)
        self.assertEqual(result.returncode, 2)
        self.assertIn("small_temporal_difference", report["findings"])
        self.assertIn("small_external_residual_reconstructible", report["findings"])

    def test_bad_external_json_fails_closed(self):
        result, report = run_gate(candidate(), invalid_external="{not-json")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unreadable_or_invalid_external_marginals", report["findings"])

    def test_invalid_external_schema_fails_closed(self):
        bad = marginals(15)
        bad["totals"][0]["requests"] = True
        result, report = run_gate(candidate(), bad)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid_external_marginal_schema", report["findings"])

    def test_missing_external_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "candidate.json"
            source.write_text(json.dumps(candidate()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(GATE), str(source),
                 "--external-marginals", str(Path(folder) / "missing.json")],
                capture_output=True, text=True, check=False)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 2)
            self.assertIn("unreadable_or_invalid_external_marginals", report["findings"])

    def test_external_option_rejects_private_payload(self):
        private = copy.deepcopy(candidate())
        private.pop("schema_version")
        result, report = run_gate(private, marginals(15))
        self.assertEqual(result.returncode, 2)
        self.assertIn("external_marginals_require_review_candidate", report["findings"])

    def test_marginal_coverage_gap_fails_closed(self):
        empty = marginals(15)
        empty["totals"] = []
        result, report = run_gate(candidate(), empty)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unverified_external_marginal_coverage", report["findings"])

    def test_no_auxiliary_values_leaked_in_report(self):
        result, report = run_gate(candidate(), marginals(987654321))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("987654321", result.stdout)
        self.assertNotIn('"requests"', result.stdout)
        self.assertIn("external_residual_may_reveal_suppressed_categories", report["findings"])

    def test_without_external_option_retains_prior_contract(self):
        result, report = run_gate(candidate())
        self.assertEqual(result.returncode, 2)
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertNotIn("unreadable_or_invalid_external_marginals", report["findings"])


if __name__ == "__main__":
    unittest.main()
