"""Synthetic snapshot integrity tests; no real request IDs included."""
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from snapshot_audit import audit_snapshot

class SnapshotAuditTests(unittest.TestCase):
    def test_detect_duplicates_and_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"sample.csv"
            with f.open("w",encoding="utf-8",newline="") as h:
                w=csv.writer(h)
                w.writerow(["unique_key","created_date","closed_date"])
                w.writerows([["A","2026-09-01","2026-09-02"],["A","2026-09-01",""],["","2026-09-01",""],["B","",""]])
            result=audit_snapshot(f,expected_rows=4)
            self.assertEqual(result["rows"],4)
            self.assertEqual(result["duplicate_unique_key"],1)
            self.assertEqual(result["missing_unique_key"],1)
            self.assertEqual(result["missing_created_date"],1)
            self.assertEqual(result["closed_date_present"],1)
            self.assertTrue(result["expected_rows_match"])
            self.assertEqual(result["source_sha256"],hashlib.sha256(f.read_bytes()).hexdigest())
            self.assertNotIn("A",result)
    def test_expected_count_mismatch_and_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/"sample.csv"
            f.write_text("unique_key,created_date,closed_date\n1,2026-09-01,\n",encoding="utf-8")
            self.assertFalse(audit_snapshot(f,expected_rows=2)["expected_rows_match"])
            f.write_text("id,date\n1,2026-09-01\n",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"requires"):
                audit_snapshot(f)
if __name__=="__main__":
    unittest.main()
