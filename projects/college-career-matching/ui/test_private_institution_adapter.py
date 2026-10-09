import json
import tempfile
import unittest
from pathlib import Path
from private_institution_adapter import stage_records, validate_record

class PrivateAdapterTests(unittest.TestCase):
    def test_valid_record_remains_private(self):
        record = {"unitid": 123456, "name": "Illustrative College", "state": "NY",
                  "source_url": "https://example.org/source", "retrieved_at": "2026-10-08",
                  "undergraduate_enrollment": 2500,
                  "field_evidence": {
                      "name": {"url": "https://example.org/source", "as_of": "2025"},
                      "state": {"url": "https://example.org/source", "as_of": "2025"},
                      "undergraduate_enrollment": {"url": "https://example.org/source", "as_of": "2025"}}}
        self.assertEqual(validate_record(record), [])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "private_review.json"
            rows = stage_records([record, record], target)
            self.assertEqual(rows[0]["publication_status"], "DO_NOT_PUBLISH")
            self.assertIn("Duplicate UNITID", rows[1]["validation_errors"])
            self.assertEqual(json.loads(target.read_text())["publication_status"], "DO_NOT_PUBLISH")
            with self.assertRaises(ValueError):
                stage_records([record], Path(directory) / "public-data.json")
            for blocked in ("public-data.JSON", "dist/private_review.json", "site/private_review.json", "static/private_review.json"):
                with self.subTest(destination=blocked), self.assertRaises(ValueError):
                    stage_records([record], Path(directory) / blocked)

    def test_missing_field_evidence(self):
        record = {"unitid": 123456, "name": "Example", "state": "NY",
                  "source_url": "https://example.org/source", "retrieved_at": "2026-10-08"}
        self.assertTrue(any("name needs source" in error for error in validate_record(record)))
        self.assertTrue(any("state needs source" in error for error in validate_record(record)))

if __name__ == "__main__":
    unittest.main()
