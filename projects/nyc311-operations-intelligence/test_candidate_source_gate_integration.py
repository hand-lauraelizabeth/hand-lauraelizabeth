"""Synthetic-only integration checks for the opt-in NYC 311 candidate/source gate.

The source manifest is NOT official or complete evidence. No service requests,
identifiers, real agency totals, or private values are stored in this test.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_candidate_coarse_alignment_audit import candidate
from test_coarse_20cell_binding_audit import sample

GATE = Path(__file__).with_name("release_privacy_gate.py")


def invoke(c=None, m=None, *, enabled=True, binding=True, legacy=False,
           missing=False, malformed=False, paired=False):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        c = candidate() if c is None else c
        if legacy:
            c = copy.deepcopy(c)
            c.pop("schema_version", None)
        p = root / "candidate.json"
        p.write_text(json.dumps(c), encoding="utf-8")
        cmd = [sys.executable, str(GATE), str(p)]
        if enabled:
            cmd.append("--candidate-source-alignment")
        if binding:
            q = root / "binding.json"
            if not missing:
                q.write_text("{bad" if malformed else json.dumps(sample() if m is None else m),
                             encoding="utf-8")
            cmd.extend(["--coarse-binding", str(q)])
        if paired:
            old = sample()
            new = copy.deepcopy(old)
            new["snapshot_as_of"] = "2026-10-27"
            old_path, new_path = root / "previous.json", root / "current.json"
            old_path.write_text(json.dumps(old), encoding="utf-8")
            new_path.write_text(json.dumps(new), encoding="utf-8")
            cmd += ["--paired-coarse-previous", str(old_path),
                    "--paired-coarse-current", str(new_path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc, json.loads(proc.stdout)


class CandidateSourceGateIntegrationTests(unittest.TestCase):
    def test_existing_binding_without_opt_in_unchanged(self):
        proc, report = invoke(enabled=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("coarse_binding_candidate_alignment_unverified", report["findings"])
        self.assertNotIn("candidate_source_alignment_authentication_pending", report["findings"])

    def test_exact_synthetic_alignment_is_never_clearance(self):
        proc, report = invoke()
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(report["hold"])
        self.assertFalse(report["publication_approved"])
        self.assertIn("candidate_source_alignment_authentication_pending", report["findings"])
        self.assertIn("candidate_source_provenance_not_authenticated", report["findings"])

    def test_opt_in_without_binding_fails_closed(self):
        _, report = invoke(binding=False)
        self.assertIn("candidate_source_alignment_requires_coarse_binding", report["findings"])

    def test_legacy_payload_not_treated_as_valid_review_candidate(self):
        _, report = invoke(legacy=True)
        self.assertIn("candidate_source_alignment_requires_review_candidate", report["findings"])
        self.assertNotIn("candidate_source_alignment_authentication_pending", report["findings"])

    def test_missing_binding_fails_closed(self):
        _, report = invoke(missing=True)
        self.assertIn("unreadable_or_invalid_candidate_source_pair", report["findings"])

    def test_malformed_binding_fails_closed(self):
        _, report = invoke(malformed=True)
        self.assertIn("unreadable_or_invalid_candidate_source_pair", report["findings"])

    def test_invalid_coarse_grid_rejected(self):
        m = sample()
        m["coarse_cells"].pop()
        _, report = invoke(m=m)
        self.assertIn("invalid_or_inconsistent_source_binding", report["findings"])

    def test_small_residual_reveals_coverage_gap(self):
        c = candidate()
        c["aggregates"][0]["requests"] -= 1
        _, report = invoke(c=c)
        self.assertIn("small_unpublished_source_residual", report["findings"])
        self.assertIn("candidate_source_coverage_incomplete", report["findings"])

    def test_candidate_overage_detected_at_both_grains(self):
        c = candidate()
        c["aggregates"][0]["requests"] += 1
        _, report = invoke(c=c)
        self.assertIn("candidate_agency_total_exceeds_source", report["findings"])
        self.assertIn("candidate_coarse_cell_exceeds_source", report["findings"])

    def test_balanced_cross_agency_tampering_detected(self):
        c = candidate()
        c["aggregates"][0]["requests"] += 1
        c["aggregates"][1]["requests"] -= 1
        _, report = invoke(c=c)
        self.assertIn("candidate_agency_total_exceeds_source", report["findings"])
        self.assertIn("candidate_source_coverage_incomplete", report["findings"])

    def test_missing_candidate_agency_detected(self):
        c = candidate()
        c["aggregates"].pop(0)
        _, report = invoke(c=c)
        self.assertIn("source_agency_missing_from_candidate", report["findings"])

    def test_unexpected_candidate_agency_detected(self):
        c = candidate()
        c["aggregates"][0]["agency"] = "SECRET-AGENCY-XYZ"
        _, report = invoke(c=c)
        self.assertIn("candidate_agency_not_in_source_binding", report["findings"])

    def test_candidate_month_mismatch_detected(self):
        c = candidate()
        c["aggregates"][0]["month"] = "2026-10"
        _, report = invoke(c=c)
        self.assertIn("candidate_source_month_mismatch", report["findings"])

    def test_candidate_snapshot_mismatch_detected(self):
        c = candidate()
        c["snapshot_as_of"] = "2026-10-26"
        _, report = invoke(c=c)
        self.assertIn("candidate_source_snapshot_mismatch", report["findings"])

    def test_invalid_candidate_not_silently_aligned(self):
        c = candidate()
        c["aggregates"][0]["requests"] = 2
        _, report = invoke(c=c)
        self.assertIn("invalid_or_unsafe_review_candidate", report["findings"])

    def test_duplicate_candidate_cell_rejected(self):
        c = candidate()
        c["aggregates"].append(copy.deepcopy(c["aggregates"][0]))
        _, report = invoke(c=c)
        self.assertIn("invalid_or_unsafe_review_candidate", report["findings"])

    def test_combined_paired_audit_keeps_both_issues(self):
        _, report = invoke(paired=True)
        self.assertIn("candidate_source_alignment_authentication_pending", report["findings"])
        self.assertIn("paired_coarse_candidate_alignment_unverified", report["findings"])

    def test_output_never_echoes_private_labels_or_counts(self):
        c, m = candidate(), sample()
        c["aggregates"][0]["agency"] = "SECRET-AGENCY-XYZ"
        m["agency_to_group"]["SECRET-AGENCY-XYZ"] = "Group A"
        proc, report = invoke(c=c, m=m)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(report["publication_approved"])
        for secret in ("SECRET-AGENCY-XYZ", "Fictional type", "Agency 0",
                       "source_sha256", "Group A", "433"):
            self.assertNotIn(secret, proc.stdout)


if __name__ == "__main__":
    unittest.main()
