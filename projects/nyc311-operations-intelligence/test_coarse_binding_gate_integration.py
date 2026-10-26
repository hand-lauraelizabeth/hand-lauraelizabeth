"""Synthetic-only integration tests for private 20-cell coarse source reconciliation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_external_marginal_audit import candidate, marginals
from test_coarse_20cell_binding_audit import sample

GATE = Path(__file__).with_name("release_privacy_gate.py")
SHA = "a" * 64


def run_gate(payload=None, binding=None, malformed=None, missing=False,
             digest=None, previous=None, external=None):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p = root / "candidate.json"
        p.write_text(json.dumps(candidate() if payload is None else payload), encoding="utf-8")
        cmd = [sys.executable, str(GATE), str(p)]
        if binding is not None or malformed is not None or missing:
            f = root / "private_binding.json"
            if not missing:
                f.write_text(malformed if malformed is not None else json.dumps(binding),
                             encoding="utf-8")
            cmd += ["--coarse-binding", str(f)]
        if digest is not None:
            cmd += ["--expected-source-sha256", digest]
        if previous is not None:
            old = root / "previous.json"
            old.write_text(json.dumps(previous), encoding="utf-8")
            cmd += ["--previous", str(old)]
        if external is not None:
            aux = root / "external.json"
            aux.write_text(json.dumps(external), encoding="utf-8")
            cmd += ["--external-marginals", str(aux)]
        run = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return run, json.loads(run.stdout)


class CoarseBindingGateIntegrationTests(unittest.TestCase):
    def test_consistent_manifest_and_digest_still_hold(self):
        run, report = run_gate(binding=sample(), digest=SHA)
        self.assertEqual(run.returncode, 2)
        self.assertFalse(report["publication_approved"])
        self.assertTrue(report["hold"])
        self.assertIn("coarse_binding_candidate_alignment_unverified", report["findings"])
        self.assertIn("source_provenance_not_authenticated", report["findings"])
        self.assertNotIn("coarse_counts_do_not_reconcile", report["findings"])

    def test_missing_independent_digest_explicit(self):
        _, report = run_gate(binding=sample())
        self.assertIn("independent_source_digest_not_supplied", report["findings"])

    def test_digest_mismatch(self):
        _, report = run_gate(binding=sample(), digest="b" * 64)
        self.assertIn("source_digest_mismatch", report["findings"])

    def test_invalid_digest(self):
        _, report = run_gate(binding=sample(), digest="bad")
        self.assertIn("invalid_expected_source_digest", report["findings"])

    def test_orphan_digest_fails_closed(self):
        _, report = run_gate(digest=SHA)
        self.assertIn("orphan_expected_source_digest", report["findings"])

    def test_balanced_cell_tampering_detected(self):
        manifest = sample()
        manifest["coarse_cells"][0]["requests"] += 1
        manifest["coarse_cells"][1]["requests"] -= 1
        _, report = run_gate(binding=manifest, digest=SHA)
        self.assertIn("coarse_counts_do_not_reconcile", report["findings"])

    def test_small_cell_detected(self):
        manifest = sample()
        manifest["fine_rows"][0]["requests"] = 3
        manifest["coarse_cells"][0]["requests"] = 3
        manifest["source_total_requests"] -= 17
        _, report = run_gate(binding=manifest, digest=SHA)
        self.assertIn("coarse_cell_below_display_threshold", report["findings"])

    def test_unmapped_agency_detected(self):
        manifest = sample()
        manifest["fine_rows"][0]["agency"] = "Unmapped private agency"
        _, report = run_gate(binding=manifest)
        self.assertIn("unmapped_source_agency", report["findings"])

    def test_incomplete_grid_detected(self):
        manifest = sample()
        manifest["coarse_cells"].pop()
        _, report = run_gate(binding=manifest)
        self.assertIn("incomplete_or_extra_coarse_grid", report["findings"])

    def test_malformed_json_fails_closed(self):
        run, report = run_gate(malformed="{private:bad")
        self.assertEqual(run.returncode, 2)
        self.assertIn("unreadable_or_invalid_coarse_binding", report["findings"])

    def test_missing_file_fails_closed(self):
        run, report = run_gate(missing=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn("unreadable_or_invalid_coarse_binding", report["findings"])

    def test_legacy_payload_cannot_use_binding(self):
        legacy = copy.deepcopy(candidate())
        legacy.pop("schema_version")
        _, report = run_gate(payload=legacy, binding=sample())
        self.assertIn("coarse_binding_requires_review_candidate", report["findings"])
        self.assertNotIn("source_provenance_not_authenticated", report["findings"])

    def test_combines_external_and_temporal_findings(self):
        previous = candidate()
        previous["snapshot_as_of"] = "2026-10-24"
        previous["aggregates"][0]["requests"] = 11
        _, report = run_gate(binding=sample(), previous=previous, external=marginals(15))
        self.assertIn("small_temporal_difference", report["findings"])
        self.assertIn("small_external_residual_reconstructible", report["findings"])
        self.assertIn("coarse_binding_candidate_alignment_unverified", report["findings"])

    def test_private_values_and_digest_not_echoed(self):
        manifest = sample()
        manifest["coarse_cells"][0]["requests"] = 987654321
        manifest["agency_to_group"]["SECRET-AGENCY-XYZ"] = "Group A"
        run, report = run_gate(binding=manifest, digest=SHA)
        self.assertEqual(run.returncode, 2)
        for secret in ("987654321", "SECRET-AGENCY-XYZ", SHA, "source_total_requests"):
            self.assertNotIn(secret, run.stdout)
        self.assertFalse(report["publication_approved"])

    def test_without_binding_option_retains_previous_behavior(self):
        run, report = run_gate()
        self.assertEqual(run.returncode, 2)
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertNotIn("coarse_binding_candidate_alignment_unverified", report["findings"])


if __name__ == "__main__":
    unittest.main()
