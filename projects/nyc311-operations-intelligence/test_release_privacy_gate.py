"""Synthetic, adversarial tests for private NYC 311 disclosure QA."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline import ingest
from release_privacy_gate import inspect

FIELDS = ["unique_key", "created_date", "closed_date", "agency",
          "complaint_type", "borough", "status"]


def fixture(groups, minimum=5):
    rows = []
    total = sum(groups)
    for idx, n in enumerate(groups):
        rows.append({"month": "2026-09", "borough": "QUEENS", "agency": "DOT",
                     "problem": f"Synthetic {idx}", "requests": n,
                     "closed_with_valid_interval": 0})
    return {"dataset_id": "erm2-nwe9",
            "rules": {"grain": "month × borough × agency × original API complaint_type",
                      "display_minimum_cell_count": minimum},
            "quality": {"rows_read": total, "valid_records": total,
                        "unique_keys_verified": total,
                        "small_cells_suppressed": 0},
            "aggregates": rows}


class TestMarginalGate(unittest.TestCase):
    def test_detects_reconstruction_from_one_suppressed_group(self):
        candidate = fixture([12, 10])
        candidate["quality"]["valid_records"] = 25
        candidate["quality"]["rows_read"] = 25
        candidate["quality"]["unique_keys_verified"] = 25
        candidate["quality"]["small_cells_suppressed"] = 1
        findings = inspect(candidate)
        self.assertIn("single_suppressed_cell_reconstructible", findings)
        self.assertIn("exact_quality_marginal_with_suppressed_cells", findings)

    def test_detects_leak_from_actual_pipeline_output_synthetic_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / "fixture.csv", Path(tmp) / "output.json"
            with src.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(FIELDS)
                key = 0
                for group, n in (("Visible", 12), ("Withheld", 3)):
                    for _ in range(n):
                        key += 1
                        writer.writerow([str(key), "2026-09-10T09:00:00",
                                         "", "DOT", group, "Queens", "Open"])
            ingest(src, out, as_of="2026-10-25", min_cell=5)
            findings = inspect(json.loads(out.read_text()))
            self.assertIn("single_suppressed_cell_reconstructible", findings)

    def test_safe_synthetic_single_snapshot_has_no_modeled_finding(self):
        self.assertEqual(inspect(fixture([10, 12])), [])

    def test_rejects_small_closure_and_complement(self):
        candidate = fixture([12, 12])
        candidate["aggregates"][0]["closed_with_valid_interval"] = 1
        candidate["aggregates"][1]["closed_with_valid_interval"] = 11
        self.assertIn("unsafe_closure_subcell", inspect(candidate))

    def test_rejects_record_level_field_and_small_denominator(self):
        candidate = fixture([12, 4])
        candidate["aggregates"][0]["incident_address"] = "FICTIONAL"
        findings = inspect(candidate)
        self.assertIn("record_level_field", findings)
        self.assertIn("unsafe_request_cell", findings)

    def test_temporal_differencing_and_support_changes(self):
        before = fixture([12, 14])
        after = fixture([13, 14])
        self.assertIn("small_temporal_difference", inspect(after, before))
        after["aggregates"][0]["problem"] = "Different synthetic category"
        self.assertIn("changed_published_group_support", inspect(after, before))

    def test_incompatible_snapshots_fail_closed(self):
        before, after = fixture([12]), fixture([12])
        before["dataset_id"] = "other"
        self.assertIn("incompatible_snapshots", inspect(after, before))

    def test_threshold_one_is_unsafe_for_public_export(self):
        self.assertIn("unsafe_or_invalid_threshold", inspect(fixture([1], 1)))

    def test_cli_reports_hold_without_echoing_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            candidate = fixture([12])
            candidate["aggregates"][0]["incident_address"] = "SECRET-FICTIONAL"
            path = Path(tmp) / "candidate.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            script = Path(__file__).with_name("release_privacy_gate.py")
            result = subprocess.run([sys.executable, str(script), str(path)],
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("SECRET-FICTIONAL", result.stdout)
            self.assertTrue(json.loads(result.stdout)["hold"])
            self.assertFalse(json.loads(result.stdout)["publication_approved"])


if __name__ == "__main__":
    unittest.main()
