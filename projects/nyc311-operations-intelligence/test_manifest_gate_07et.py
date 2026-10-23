"""Synthetic manifest-bound reconciliation tests; never uses real 311 records."""
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
import pipeline

COLUMNS = ["unique_key", "created_date", "closed_date", "agency",
           "complaint_type", "borough", "status"]

class SuppliedManifestGate(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "synthetic.csv"
        self.out = Path(self.temp.name) / "export.json"
        with self.source.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(COLUMNS)
            writer.writerow(["SYNTHETIC-1", "2026-09-10T12:00:00", "",
                             "DOT", "Pothole", "Queens", "Open"])
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def run_gate(self, **kwargs):
        return pipeline.ingest(self.source, self.out, as_of="2026-09-30",
                               min_cell=1, **kwargs)

    def test_matching_manifest_and_unique_key_audit(self):
        result = self.run_gate(expected_sha256=self.digest, expected_rows=1)
        self.assertTrue(result["quality"]["supplied_manifest_verified"])
        self.assertEqual(result["quality"]["unique_keys_verified"], 1)
        self.assertEqual(result["source_sha256"], self.digest)

    def test_wrong_digest_fails_without_overwriting_export(self):
        self.out.write_text("previous")
        with self.assertRaisesRegex(ValueError, "SHA-256 does not match"):
            self.run_gate(expected_sha256="0" * 64, expected_rows=1)
        self.assertEqual(self.out.read_text(), "previous")

    def test_wrong_row_count_fails_without_overwriting_export(self):
        self.out.write_text("previous")
        with self.assertRaisesRegex(ValueError, "row count does not match"):
            self.run_gate(expected_sha256=self.digest, expected_rows=2)
        self.assertEqual(self.out.read_text(), "previous")

    def test_partial_manifest_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "must be supplied together"):
            self.run_gate(expected_sha256=self.digest)
        with self.assertRaisesRegex(ValueError, "must be supplied together"):
            self.run_gate(expected_rows=1)
        self.assertFalse(self.out.exists())

    def test_malformed_digest_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "64 hexadecimal"):
            self.run_gate(expected_sha256="not-a-digest", expected_rows=1)
        self.assertFalse(self.out.exists())

    def test_unanchored_export_is_explicitly_labeled(self):
        result = self.run_gate()
        self.assertFalse(result["quality"]["supplied_manifest_verified"])
        self.assertIn("not independent authentication", result["rules"]["source_provenance"])

if __name__ == "__main__":
    unittest.main()
