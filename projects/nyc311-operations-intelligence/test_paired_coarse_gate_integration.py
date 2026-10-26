"""Synthetic-only release-gate tests for paired 20-cell temporal risk checks.

No official source rows, private counts, identities, or source files are fixtures.
"""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_external_marginal_audit import candidate
from test_paired_coarse_temporal_audit import pair, change

GATE = Path(__file__).with_name("release_privacy_gate.py")


def invoke(old=None, new=None, *, old_text=None, new_text=None,
           old_missing=False, new_missing=False, only=None, legacy=False,
           with_binding=False):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        payload = candidate()
        if legacy:
            payload.pop("schema_version")
        p = root / "candidate.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        cmd = [sys.executable, str(GATE), str(p)]
        if only != "current" and (old is not None or old_text is not None or old_missing):
            a = root / "previous_private.json"
            if not old_missing:
                a.write_text(old_text if old_text is not None else json.dumps(old),
                             encoding="utf-8")
            cmd += ["--paired-coarse-previous", str(a)]
        if only != "previous" and (new is not None or new_text is not None or new_missing):
            b = root / "current_private.json"
            if not new_missing:
                b.write_text(new_text if new_text is not None else json.dumps(new),
                             encoding="utf-8")
            cmd += ["--paired-coarse-current", str(b)]
        if with_binding:
            manifest = root / "binding.json"
            manifest.write_text(json.dumps(old), encoding="utf-8")
            cmd += ["--coarse-binding", str(manifest)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc, json.loads(proc.stdout)


class PairedCoarseGateIntegrationTests(unittest.TestCase):
    def test_unchanged_pair_still_holds_and_is_unbound(self):
        old, new = pair()
        proc, report = invoke(old, new)
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(report["hold"])
        self.assertFalse(report["publication_approved"])
        self.assertIn("paired_coarse_candidate_alignment_unverified", report["findings"])
        self.assertIn("source_identity_cohort_not_reconciled", report["findings"])

    def test_small_positive_delta_detected(self):
        old, new = pair()
        change(new, 1)
        _, report = invoke(old, new)
        self.assertIn("small_published_coarse_difference", report["findings"])

    def test_negative_revision_detected(self):
        old, new = pair()
        change(new, -1)
        _, report = invoke(old, new)
        self.assertIn("decreasing_coarse_cell_revision", report["findings"])

    def test_changed_editorial_group_definition_detected(self):
        old, new = pair()
        new["agency_to_group"]["Agency 0"] = "Group B"
        _, report = invoke(old, new)
        self.assertIn("editorial_group_definition_changed", report["findings"])

    def test_wrong_month_detected(self):
        old, new = pair()
        new["month"] = "2026-10"
        _, report = invoke(old, new)
        self.assertIn("incompatible_paired_cohort", report["findings"])

    def test_nonincreasing_snapshot_detected(self):
        old, new = pair()
        new["snapshot_as_of"] = old["snapshot_as_of"]
        _, report = invoke(old, new)
        self.assertIn("nonincreasing_snapshot_order", report["findings"])

    def test_missing_current_argument_fails_closed(self):
        old, _ = pair()
        _, report = invoke(old, only="previous")
        self.assertIn("paired_coarse_manifest_pair_incomplete", report["findings"])

    def test_missing_previous_argument_fails_closed(self):
        _, new = pair()
        _, report = invoke(new=new, only="current")
        self.assertIn("paired_coarse_manifest_pair_incomplete", report["findings"])

    def test_invalid_json_fails_closed(self):
        old, _ = pair()
        _, report = invoke(old, new_text="{bad-json")
        self.assertIn("unreadable_or_invalid_paired_coarse_manifest", report["findings"])

    def test_missing_private_file_fails_closed(self):
        old, _ = pair()
        _, report = invoke(old, new_missing=True)
        self.assertIn("unreadable_or_invalid_paired_coarse_manifest", report["findings"])

    def test_invalid_manifest_fails_closed(self):
        old, new = pair()
        new["coarse_cells"].pop()
        _, report = invoke(old, new)
        self.assertIn("inconsistent_paired_coarse_manifest", report["findings"])

    def test_legacy_payload_cannot_invoke_paired_audit(self):
        old, new = pair()
        _, report = invoke(old, new, legacy=True)
        self.assertIn("paired_coarse_requires_review_candidate", report["findings"])
        self.assertNotIn("paired_coarse_candidate_alignment_unverified", report["findings"])

    def test_combines_binding_and_paired_findings(self):
        old, new = pair()
        change(new, 1)
        _, report = invoke(old, new, with_binding=True)
        self.assertIn("coarse_binding_candidate_alignment_unverified", report["findings"])
        self.assertIn("small_published_coarse_difference", report["findings"])

    def test_private_data_never_echoed(self):
        old, new = pair()
        change(new, 1)
        new["agency_to_group"]["SECRET-AGENCY-XYZ"] = "Group A"
        proc, report = invoke(old, new)
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(report["publication_approved"])
        for private in ("SECRET-AGENCY-XYZ", "Agency 0", "source_sha256", "433"):
            self.assertNotIn(private, proc.stdout)

    def test_no_pair_preserves_existing_hold(self):
        proc, report = invoke()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("external_marginal_integer_review_pending", report["findings"])
        self.assertNotIn("paired_coarse_candidate_alignment_unverified", report["findings"])


if __name__ == "__main__":
    unittest.main()
