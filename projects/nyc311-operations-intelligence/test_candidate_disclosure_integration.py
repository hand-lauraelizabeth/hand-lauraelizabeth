"""Synthetic-only contract tests: private QA -> minimized candidate -> private gate."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from public_candidate import prepare
from release_privacy_gate import inspect


def private_fixture(count=30, closed=10, snapshot="2026-10-25"):
    return {
        "dataset_id": "erm2-nwe9", "snapshot_as_of": snapshot,
        "source_sha256": "f" * 64, "source_bytes": 12345,
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10},
        "quality": {"rows_read": count + 3, "unique_keys_verified": count + 3,
                    "valid_records": count + 3, "small_cells_suppressed": 1},
        "aggregates": [{"month": "2026-09", "borough": "QUEENS",
                        "agency": "DOT", "problem": "Synthetic",
                        "requests": count, "closed_with_valid_interval": closed}],
    }


class CandidateGateIntegration(unittest.TestCase):
    def test_private_marginal_reconstruction_not_exported(self):
        private = private_fixture()
        self.assertIn("single_suppressed_cell_reconstructible", inspect(private))
        candidate = prepare(private)
        self.assertEqual(inspect(candidate), [])
        self.assertNotIn("quality", candidate)
        self.assertNotIn("source_sha256", candidate)
        self.assertNotIn("source_bytes", candidate)
        self.assertNotIn("33", json.dumps(candidate))

    def test_candidate_cli_stays_on_hold_even_without_modeled_findings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "synthetic.json"
            path.write_text(json.dumps(prepare(private_fixture())), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("release_privacy_gate.py")), str(path)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            output = json.loads(result.stdout)
            self.assertTrue(output["hold"])
            self.assertFalse(output["publication_approved"])
            self.assertIn("external_marginal_integer_review_pending", output["findings"])

    def test_rejects_quality_or_checksum_reintroduced(self):
        for field, value in (("quality", {"rows_read": 33}), ("source_sha256", "secret")):
            with self.subTest(field=field):
                candidate = prepare(private_fixture())
                candidate[field] = value
                self.assertIn("invalid_candidate_schema", inspect(candidate))

    def test_rejects_unknown_version(self):
        candidate = prepare(private_fixture())
        candidate["schema_version"] = "unknown"
        self.assertIn("invalid_candidate_schema", inspect(candidate))

    def test_rejects_wrong_dataset_or_grain(self):
        for field, value in (("dataset_id", "other"), ("grain", "other")):
            candidate = prepare(private_fixture())
            if field == "grain":
                candidate["rules"][field] = value
            else:
                candidate[field] = value
            self.assertIn("invalid_candidate_schema", inspect(candidate))

    def test_rejects_unexpected_candidate_rule(self):
        candidate = prepare(private_fixture())
        candidate["rules"]["privacy"] = "unreviewed"
        self.assertIn("invalid_candidate_schema", inspect(candidate))

    def test_rejects_record_level_field(self):
        candidate = prepare(private_fixture())
        candidate["aggregates"][0]["incident_address"] = "FICTIONAL"
        findings = inspect(candidate)
        self.assertIn("invalid_candidate_aggregate_schema", findings)
        self.assertIn("record_level_field", findings)

    def test_rejects_small_cell_and_closure_complement(self):
        candidate = prepare(private_fixture())
        candidate["aggregates"][0]["requests"] = 9
        self.assertIn("unsafe_request_cell", inspect(candidate))
        candidate = prepare(private_fixture())
        candidate["aggregates"][0]["closed_with_valid_interval"] = 29
        self.assertIn("unsafe_closure_subcell", inspect(candidate))

    def test_rejects_lowered_threshold(self):
        candidate = prepare(private_fixture())
        candidate["rules"]["display_minimum_cell_count"] = 5
        self.assertIn("unsafe_or_invalid_threshold", inspect(candidate))

    def test_rejects_invalid_date(self):
        candidate = prepare(private_fixture())
        candidate["snapshot_as_of"] = "2026-02-30"
        self.assertIn("invalid_candidate_schema", inspect(candidate))

    def test_temporal_request_difference(self):
        previous = prepare(private_fixture(count=30, closed=10, snapshot="2026-10-24"))
        current = prepare(private_fixture(count=31, closed=10))
        self.assertIn("small_temporal_difference", inspect(current, previous))

    def test_temporal_closure_difference(self):
        previous = prepare(private_fixture(count=30, closed=10, snapshot="2026-10-24"))
        current = prepare(private_fixture(count=30, closed=11))
        self.assertIn("small_temporal_closure_difference", inspect(current, previous))

    def test_temporal_closure_disclosure_support(self):
        previous = prepare(private_fixture(count=30, closed=None, snapshot="2026-10-24"))
        current = prepare(private_fixture(count=30, closed=10))
        self.assertIn("changed_closure_disclosure_support", inspect(current, previous))

    def test_temporal_category_support(self):
        previous = prepare(private_fixture(snapshot="2026-10-24"))
        current = prepare(private_fixture())
        current["aggregates"][0]["problem"] = "Changed synthetic category"
        self.assertIn("changed_published_group_support", inspect(current, previous))

    def test_rejects_reverse_snapshot_order(self):
        previous = prepare(private_fixture(snapshot="2026-10-26"))
        current = prepare(private_fixture(snapshot="2026-10-25"))
        self.assertIn("reverse_snapshot_order", inspect(current, previous))

    def test_rejects_incompatible_previous_schema(self):
        previous = private_fixture(snapshot="2026-10-24")
        current = prepare(private_fixture())
        self.assertIn("incompatible_snapshots", inspect(current, previous))

    def test_rejects_tampered_previous(self):
        previous = prepare(private_fixture(snapshot="2026-10-24"))
        previous["quality"] = {"valid_records": 33}
        current = prepare(private_fixture())
        self.assertIn("invalid_previous_snapshot", inspect(current, previous))

    def test_original_private_fixture_unchanged(self):
        source = private_fixture()
        before = copy.deepcopy(source)
        self.assertEqual(inspect(prepare(source)), [])
        self.assertEqual(source, before)


if __name__ == "__main__":
    unittest.main()
