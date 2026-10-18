"""Synthetic NYC local-calendar and DST-fold regression tests (not source evidence)."""
import csv
import tempfile
import unittest
from pathlib import Path
from pipeline import dateparse, ingest

FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"]

class TestTimezoneRegression(unittest.TestCase):
    def test_utc_midnight_crosses_local_calendar(self):
        self.assertEqual(dateparse("2026-10-01T01:30:00Z").date().isoformat(), "2026-09-30")
        self.assertEqual(dateparse("2026-10-01T01:30:00+00:00").date().isoformat(), "2026-09-30")

    def test_naive_timestamp_is_local(self):
        self.assertEqual(dateparse("2026-09-30T23:30:00").date().isoformat(), "2026-09-30")

    def test_mixed_timezone_closure(self):
        rows = [
            ["1", "2026-10-01T01:30:00Z", "2026-10-01T02:30:00Z", "DOT", "Pothole", "Queens", "Closed"],
            ["2", "2026-09-30T23:30:00", "2026-10-01T04:00:00Z", "DOT", "Pothole", "Queens", "Closed"],
            ["3", "2026-09-30T23:30:00", "2026-09-30T22:30:00-04:00", "DOT", "Pothole", "Queens", "Closed"],
        ]
        result = self.ingest_rows(rows, "2026-09-30")
        self.assertEqual(result["quality"]["valid_records"], 3)
        self.assertEqual(result["quality"]["closure_before_creation"], 1)
        self.assertEqual(result["aggregates"][0]["requests"], 3)
        self.assertEqual(result["aggregates"][0]["closed_with_valid_interval"], 2)
        self.assertEqual(result["aggregates"][0]["month"], "2026-09")

    def test_dst_fall_back_utc_order_not_wall_clock_order(self):
        # 01:30 EDT precedes 01:15 EST by 45 real minutes.
        rows = [
            ["1", "2026-11-01T01:30:00-04:00", "2026-11-01T01:15:00-05:00", "DOT", "Pothole", "Queens", "Closed"],
            ["2", "2026-11-01T01:15:00-05:00", "2026-11-01T01:30:00-04:00", "DOT", "Pothole", "Queens", "Closed"],
        ]
        valid = self.ingest_rows([rows[0]], "2026-11-02")
        invalid = self.ingest_rows([rows[1]], "2026-11-02")
        self.assertEqual(valid["aggregates"][0]["closed_with_valid_interval"], 1)
        self.assertEqual(valid["quality"].get("closure_before_creation", 0), 0)
        self.assertEqual(invalid["aggregates"][0]["closed_with_valid_interval"], 0)
        self.assertEqual(invalid["quality"]["closure_before_creation"], 1)

    @staticmethod
    def ingest_rows(rows, as_of):
        with tempfile.TemporaryDirectory() as td:
            source, output = Path(td)/"fixture.csv", Path(td)/"aggregate.json"
            with source.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(FIELDS)
                writer.writerows(rows)
            return ingest(source, output, as_of=as_of, min_cell=1)

if __name__ == "__main__":
    unittest.main()
