"""Synthetic-only strict September source-cohort checks.

This verifies row membership and independently supplied receipt equality, not
NYC's official origin, completeness, temporal privacy, or release approval.
No real request identifiers or NYC 311 source records are committed.
"""
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline import ingest

FIELDS = ("unique_key", "created_date", "closed_date", "agency",
          "complaint_type", "borough", "status")
VALID = [
    ["FICTIONAL-KEY-A", "2026-09-01T00:00:00", "", "SYNTHETIC", "Fictional A", "Queens", "Open"],
    # Oct 1 in UTC is still September 30 in New York.
    ["FICTIONAL-KEY-B", "2026-10-01T01:30:00+00:00", "", "SYNTHETIC", "Fictional B", "Queens", "Open"],
    ["FICTIONAL-KEY-C", "2026-09-30T23:59:59", "", "SYNTHETIC", "Fictional C", "Bronx", "Open"],
]


def fixture(root, rows=None, headers=FIELDS):
    path = root / "synthetic.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows(VALID if rows is None else rows)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def verify(source, target, digest, rows=3, month="2026-09", as_of="2026-10-26"):
    return ingest(source, target, as_of=as_of, min_cell=1,
                  expected_sha256=digest, expected_rows=rows,
                  reporting_month=month)


class StrictReportingMonthTests(unittest.TestCase):
    def test_valid_full_month_with_utc_boundary_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            output = root / "private.json"
            result = verify(source, output, digest)
            self.assertEqual(result["quality"]["rows_read"], 3)
            self.assertEqual(result["quality"]["unique_keys_verified"], 3)
            self.assertEqual(result["quality"]["reporting_month_rows_verified"], 3)
            self.assertEqual(result["rules"]["strict_reporting_month"], "2026-09")
            self.assertEqual({r["month"] for r in result["aggregates"]}, {"2026-09"})
            self.assertNotIn("FICTIONAL-KEY", output.read_text())

    def test_default_pipeline_contract_still_accepts_multi_month_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = VALID + [["FICTIONAL-KEY-D", "2026-08-15T12:00:00",
                             "", "SYNTHETIC", "Fictional D", "Queens", "Open"]]
            source, _ = fixture(root, rows)
            result = ingest(source, root / "default.json", as_of="2026-10-26", min_cell=1)
            self.assertEqual(result["quality"]["rows_read"], 4)
            self.assertNotIn("strict_reporting_month", result["rules"])

    def test_strict_mode_requires_independent_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            output = root / "private.json"
            for kwargs in (dict(expected_sha256=None, expected_rows=None),
                           dict(expected_sha256=digest, expected_rows=None)):
                with self.assertRaises(ValueError):
                    ingest(source, output, as_of="2026-10-26",
                           reporting_month="2026-09", **kwargs)
            self.assertFalse(output.exists())

    def test_bad_month_format_or_calendar_month_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            for month in ("2026-9", "2026-13", "2026-00", "2026/09", "", "2026-09x"):
                with self.subTest(month=month), self.assertRaises(ValueError):
                    verify(source, root / "private.json", digest, month=month)

    def test_snapshot_before_month_end_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            with self.assertRaisesRegex(ValueError, "Snapshot precedes"):
                verify(source, root / "private.json", digest, as_of="2026-09-29")

    def test_out_of_month_local_record_rejected_and_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = VALID + [["FICTIONAL-KEY-D", "2026-08-31T23:59:59",
                             "", "SYNTHETIC", "Fictional D", "Queens", "Open"]]
            source, digest = fixture(root, rows)
            output = root / "private.json"
            output.write_text("DO-NOT-REPLACE")
            with self.assertRaisesRegex(ValueError, "outside required reporting month"):
                verify(source, output, digest, rows=4)
            self.assertEqual(output.read_text(), "DO-NOT-REPLACE")

    def test_utc_september_first_can_be_august_in_new_york(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [VALID[0], ["FICTIONAL-KEY-B", "2026-09-01T02:00:00+00:00",
                               "", "SYNTHETIC", "Fictional B", "Queens", "Open"]]
            source, digest = fixture(root, rows)
            with self.assertRaisesRegex(ValueError, "outside required reporting month"):
                verify(source, root / "private.json", digest, rows=2)

    def test_unparseable_created_date_rejected_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [VALID[0], ["FICTIONAL-KEY-B", "NOT-A-DATE", "",
                               "SYNTHETIC", "Fictional B", "Queens", "Open"]]
            source, digest = fixture(root, rows)
            with self.assertRaisesRegex(ValueError, "Invalid created_date"):
                verify(source, root / "private.json", digest, rows=2)

    def test_expected_row_count_catches_truncated_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root, VALID[:2])
            with self.assertRaisesRegex(ValueError, "row count"):
                verify(source, root / "private.json", digest, rows=3)

    def test_expected_sha256_catches_altered_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                verify(source, root / "private.json", "b" * 64)

    def test_duplicate_keys_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = VALID + [VALID[0]]
            source, digest = fixture(root, rows)
            with self.assertRaisesRegex(ValueError, "Duplicate unique_key"):
                verify(source, root / "private.json", digest, rows=4)

    def test_duplicate_headers_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root, headers=list(FIELDS) + ["unique_key"])
            with self.assertRaisesRegex(ValueError, "Duplicate CSV header"):
                verify(source, root / "private.json", digest)

    def test_bool_and_zero_row_receipts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            for rows in (False, 0, True):
                with self.subTest(rows=rows), self.assertRaises(ValueError):
                    verify(source, root / "private.json", digest, rows=rows)

    def test_cli_strict_month_accepts_only_cohort_and_keeps_ids_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, digest = fixture(root)
            output = root / "private.json"
            proc = subprocess.run([
                sys.executable, str(Path(__file__).with_name("pipeline.py")),
                str(source), str(output), "--as-of", "2026-10-26",
                "--min-cell", "1", "--reporting-month", "2026-09",
                "--expected-sha256", digest, "--expected-rows", "3"
            ], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["quality"]["reporting_month_rows_verified"], 3)
            self.assertNotIn("FICTIONAL-KEY", proc.stdout)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
