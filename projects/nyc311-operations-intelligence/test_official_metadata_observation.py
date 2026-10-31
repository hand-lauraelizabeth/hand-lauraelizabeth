"""Read-only official 311 metadata observation contract regression (no source rows)."""
import json
from pathlib import Path
import unittest

from source_metadata_contract import validate_metadata, REQUIRED_TYPES

EVIDENCE = Path(__file__).parent / "evidence" / "official_metadata_observation_20261031_14et.json"


class OfficialMetadataObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observation = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_observed_schema_matches_pinned_contract(self):
        o = self.observation
        receipt = validate_metadata({
            "id": o["dataset_id"],
            "name": o["dataset_name"],
            "columns": o["columns"],
        })
        self.assertEqual(receipt["required_field_count"], 7)
        self.assertEqual(receipt["publisher_column_count"], o["publisher_column_count"])
        self.assertEqual(o["required_backend_field_types"], REQUIRED_TYPES)
        self.assertFalse(receipt["publisher_origin_authenticated"])
        self.assertFalse(receipt["publication_authorized"])

    def test_problem_display_label_does_not_replace_backend_field(self):
        cols = self.observation["columns"]
        problem = [c for c in cols if c["fieldName"] == "complaint_type"]
        self.assertEqual(len(problem), 1)
        self.assertEqual(problem[0]["name"], "Problem (formerly Complaint Type)")

    def test_observation_explicitly_disclaims_authentication_and_csv_reconciliation(self):
        o = self.observation
        self.assertEqual(o["publication_stage"], "published")
        self.assertEqual(o["dataset_id"], "erm2-nwe9")
        self.assertGreaterEqual(o["publisher_column_count"], 7)
        limits = " ".join(o["limitations"]).lower()
        for required in ("byte-for-byte", "checksum", "september 2026 csv", "disclosure", "publication"):
            self.assertIn(required, limits)

    def test_public_observation_excludes_service_request_rows(self):
        o = self.observation
        self.assertNotIn("rows", o)
        self.assertNotIn("data", o)
        self.assertEqual(len(o["columns"]), o["publisher_column_count"])
        self.assertEqual(len({c["fieldName"] for c in o["columns"]}), len(o["columns"]))


if __name__ == "__main__":
    unittest.main()
