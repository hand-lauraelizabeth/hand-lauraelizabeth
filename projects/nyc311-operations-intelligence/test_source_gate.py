"""Independent synthetic regression cases for source integrity and dates."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline import dateparse, ingest
from snapshot_audit import audit_snapshot

FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"]

def write_rows(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        writer.writerows(rows)

class SourceGateTests(unittest.TestCase):
    def test_reject_duplicate_id_without_creating_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "in.csv", Path(tmp) / "out.json"
            write_rows(src, [["1", "2026-09-01", "", "DOT", "Road", "Queens", "Open"],
                             ["1", "2026-09-02", "", "DOT", "Road", "Queens", "Open"]])
            self.assertEqual(audit_snapshot(src)["duplicate_unique_key"], 1)
            with self.assertRaisesRegex(ValueError, "Source integrity failed"):
                ingest(src, dst, as_of="2026-10-15", min_cell=2)
            self.assertFalse(dst.exists())

    def test_reject_blank_id_and_expected_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "in.csv", Path(tmp) / "out.json"
            write_rows(src, [["", "2026-09-01", "", "DOT", "Road", "Queens", "Open"]])
            with self.assertRaisesRegex(ValueError, "Source integrity failed"):
                ingest(src, dst, as_of="2026-10-15")
            write_rows(src, [["1", "2026-09-01", "", "DOT", "Road", "Queens", "Open"]])
            with self.assertRaisesRegex(ValueError, "Source integrity failed"):
                ingest(src, dst, as_of="2026-10-15", expected_rows=2)
            self.assertFalse(dst.exists())

    def test_source_floating_timestamps_no_inferred_timezone(self):
        self.assertIsNone(dateparse("2026-09-01T00:00:00Z"))
        self.assertIsNone(dateparse("2026-09-01T00:00:00-04:00"))
        self.assertIsNotNone(dateparse("2026-09-01T00:00:00"))

    def test_closure_date_quality_and_no_private_counts_in_public_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "in.csv", Path(tmp) / "out.json"
            rows = [
                ["1", "2026-09-01T00:00:00", "2026-09-01T00:00:00", "DOT", "Road", "Queens", "Closed"],
                ["2", "2026-09-01T00:00:00", "2026-08-31T23:00:00", "DOT", "Road", "Queens", "Closed"],
                ["3", "2026-09-01T00:00:00", "2026-09-03T00:00:00Z", "DOT", "Road", "Queens", "Closed"],
                ["4", "2026-09-01T00:00:00", "2026-11-01T00:00:00", "DOT", "Road", "Queens", "Closed"],
                ["5", "2026-09-01T00:00:00", "", "DOT", "Road", "Queens", "Closed"],
                ["6", "2026-09-01T00:00:00", "2026-09-02T00:00:00", "DOT", "Road", "Queens", "Open"],
                ["7", "2026-09-01T00:00:00", "2026-09-02T00:00:00", "DOT", "Road", "Queens", "Closed"],
                ["8", "2026-09-01T00:00:00", "2026-09-02T00:00:00", "DOT", "Road", "Queens", "Closed"],
            ]
            write_rows(src, rows)
            result = ingest(src, dst, as_of="2026-10-15", min_cell=2, expected_rows=8)
            qa = result["quality"]
            self.assertEqual(qa["closure_before_creation"], 1)
            self.assertEqual(qa["invalid_or_timezone_qualified_closed_date"], 1)
            self.assertEqual(qa["closed_date_after_as_of"], 1)
            self.assertEqual(qa["closed_status_without_usable_close_date"], 4)
            self.assertEqual(qa["closed_with_valid_interval"], 3)
            self.assertEqual(qa["zero_length_closure_interval"], 1)
            self.assertEqual(qa["nonclosed_status_with_closed_date"], 1)
            public = json.loads(dst.read_text())
            self.assertEqual(public["aggregates"][0]["requests"], 8)
            self.assertEqual(public["aggregates"][0]["closed_with_valid_interval"], 3)
            self.assertNotIn("quality", public)
            self.assertNotIn("closure_before_creation", dst.read_text())

    def test_large_synthetic_streaming_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.csv"
            with src.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(FIELDS)
                for i in range(12000):
                    writer.writerow([str(i), "2026-09-01", "", "DOT", "Road", "Queens", "Open"])
            result = audit_snapshot(src, expected_rows=12000)
            self.assertEqual(result["distinct_nonblank_unique_keys"], 12000)
            self.assertEqual(result["duplicate_unique_key"], 0)
            self.assertTrue(result["expected_rows_match"])

if __name__ == "__main__":
    unittest.main()
