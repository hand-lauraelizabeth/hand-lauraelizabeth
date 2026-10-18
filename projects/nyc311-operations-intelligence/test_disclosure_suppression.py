"""Synthetic regression tests for complementary small-cell disclosure protection."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"]

class TestDisclosureSuppression(unittest.TestCase):
    def aggregate(self, count, closures, min_cell=10):
        with tempfile.TemporaryDirectory() as td:
            src, dest = Path(td)/"source.csv", Path(td)/"out.json"
            with src.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                for i in range(count):
                    writer.writerow([
                        str(i+1), "2026-09-01T12:00:00-04:00",
                        "2026-09-02T12:00:00-04:00" if i < closures else "",
                        "DOT", "Pothole", "Queens", "Closed" if i < closures else "Open",
                    ])
            payload = ingest(src, dest, as_of="2026-09-30", min_cell=min_cell)
            self.assertEqual(json.loads(dest.read_text()), payload)
            return payload

    def test_small_closed_subset_is_suppressed(self):
        item = self.aggregate(25, 1)["aggregates"][0]
        self.assertEqual(item["requests"], 25)
        self.assertIsNone(item["closed_with_valid_interval"])
        self.assertTrue(item["closure_count_suppressed"])

    def test_small_nonclosed_complement_is_suppressed(self):
        item = self.aggregate(25, 24)["aggregates"][0]
        self.assertIsNone(item["closed_with_valid_interval"])
        self.assertTrue(item["closure_count_suppressed"])

    def test_both_sides_above_threshold_may_be_shown(self):
        item = self.aggregate(25, 12)["aggregates"][0]
        self.assertEqual(item["closed_with_valid_interval"], 12)
        self.assertFalse(item["closure_count_suppressed"])

    def test_small_request_group_is_entirely_withheld(self):
        payload = self.aggregate(9, 4)
        self.assertEqual(payload["aggregates"], [])
        self.assertEqual(payload["quality"]["small_cells_suppressed"], 1)

    def test_zero_closure_is_not_misrepresented_as_visible_zero(self):
        item = self.aggregate(25, 0)["aggregates"][0]
        self.assertIsNone(item["closed_with_valid_interval"])

    def test_cli_rejects_unsafe_threshold(self):
        pipeline = Path(__file__).with_name("pipeline.py")
        p = subprocess.run([
            sys.executable, str(pipeline), "in.csv", "out.json",
            "--as-of", "2026-09-30", "--min-cell", "1",
        ], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("at least 10", p.stderr)

    def test_publication_not_authorized_and_low_threshold_flagged(self):
        payload = self.aggregate(12, 4, min_cell=1)
        self.assertFalse(payload["publication_authorized"])
        self.assertTrue(payload["rules"]["test_only_threshold"])
        self.assertEqual(payload["aggregates"][0]["closed_with_valid_interval"], 4)
        self.assertFalse(self.aggregate(12, 4)["rules"]["test_only_threshold"])

if __name__ == "__main__":
    unittest.main()
