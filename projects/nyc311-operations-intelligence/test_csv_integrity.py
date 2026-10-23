"""Synthetic CSV structural-integrity regressions; no official service requests."""
import csv
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ["unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"]
GOOD = ["1", "2026-09-01T10:00:00", "", "DOT", "Pothole", "Queens", "Open"]

class CSVIntegrity(unittest.TestCase):
    def run_case(self, headers, rows, expected=None):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "input.csv", Path(temp) / "result.json"
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(headers)
                writer.writerows(rows)
            if expected:
                with self.assertRaisesRegex(ValueError, expected):
                    ingest(source, output, as_of="2026-09-30")
                self.assertFalse(output.exists())
            else:
                result = ingest(source, output, as_of="2026-09-30")
                self.assertEqual(result["quality"]["rows_read"], 1)
                self.assertTrue(output.exists())

    def test_duplicate_header(self):
        self.run_case(FIELDS + ["unique_key"], [GOOD + ["2"]], "Duplicate CSV header")

    def test_extra_field(self):
        self.run_case(FIELDS, [GOOD + ["private extra"]], "Malformed CSV row")

    def test_short_field(self):
        self.run_case(FIELDS, [GOOD[:-1]], "Malformed CSV row")

    def test_missing_identifier(self):
        self.run_case(FIELDS, [[""] + GOOD[1:]], "Missing unique_key")

    def test_valid_record(self):
        self.run_case(FIELDS, [GOOD])

if __name__ == "__main__":
    unittest.main()
