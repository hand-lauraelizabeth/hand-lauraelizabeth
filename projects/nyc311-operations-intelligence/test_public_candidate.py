"""Synthetic-only tests for metadata-minimized NYC 311 candidate construction."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path
from public_candidate import prepare


def fixture():
    return {
        "dataset_id": "erm2-nwe9", "snapshot_as_of": "2026-10-25",
        "source_sha256": "a" * 64, "source_bytes": 91234,
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10, "privacy": "private notes"},
        "quality": {"rows_read": 15, "unique_keys_verified": 15,
                    "valid_records": 15, "small_cells_suppressed": 1,
                    "closure_subcells_suppressed": 0},
        "aggregates": [{"month": "2026-09", "borough": "QUEENS", "agency": "DOT",
                        "problem": "Synthetic visible", "requests": 12,
                        "closed_with_valid_interval": 0}]
    }


class TestCandidate(unittest.TestCase):
    def test_actual_pipeline_synthetic_export_is_redacted(self):
        from pipeline import ingest
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / "source.csv", Path(temp) / "private.json"
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(["unique_key", "created_date", "closed_date", "agency",
                                 "complaint_type", "borough", "status"])
                for i in range(15):
                    writer.writerow([str(i + 1), "2026-09-10T09:00:00", "", "DOT",
                                     "Synthetic visible" if i < 12 else "Synthetic withheld",
                                     "Queens", "Open"])
            private = ingest(source, output, as_of="2026-10-25", min_cell=10)
            self.assertEqual(private["quality"]["small_cells_suppressed"], 1)
            self.assertEqual(private["quality"]["valid_records"], 15)
            candidate = prepare(private)
            self.assertEqual(len(candidate["aggregates"]), 1)
            self.assertNotIn("quality", candidate)
            self.assertNotIn("source_sha256", candidate)
            self.assertEqual(candidate["aggregates"][0]["requests"], 12)

    def test_exact_suppressed_group_not_reconstructible_from_candidate(self):
        source = fixture()  # 12 visible + 3 hidden; 15 only in private QA
        candidate = prepare(source)
        self.assertEqual(candidate["aggregates"][0]["requests"], 12)
        for forbidden in ("quality", "source_sha256", "source_bytes", "publication_approved"):
            self.assertNotIn(forbidden, candidate)
        self.assertNotIn("valid_records", str(candidate))
        self.assertNotIn("small_cells_suppressed", str(candidate))
        self.assertNotIn("15", str(candidate))
        self.assertEqual(source["quality"]["valid_records"], 15)

    def test_whitelists_only_minimal_rules(self):
        public = prepare(fixture())
        self.assertEqual(set(public), {"schema_version", "dataset_id", "snapshot_as_of", "rules", "aggregates"})
        self.assertEqual(set(public["rules"]), {"grain", "display_minimum_cell_count"})

    def test_rejects_low_threshold(self):
        source = fixture()
        source["rules"]["display_minimum_cell_count"] = 1
        with self.assertRaises(ValueError): prepare(source)

    def test_rejects_small_denominator(self):
        source = fixture()
        source["aggregates"][0]["requests"] = 9
        with self.assertRaises(ValueError): prepare(source)

    def test_rejects_small_closure_and_complement(self):
        for c in (1, 3, 11):
            with self.subTest(c=c):
                source = fixture()
                source["aggregates"][0]["closed_with_valid_interval"] = c
                with self.assertRaises(ValueError): prepare(source)

    def test_rejects_record_level_field(self):
        source = fixture()
        source["aggregates"][0]["incident_address"] = "FICTIONAL"
        with self.assertRaises(ValueError): prepare(source)

    def test_rejects_duplicate_keys(self):
        source = fixture()
        source["aggregates"].append(copy.deepcopy(source["aggregates"][0]))
        with self.assertRaises(ValueError): prepare(source)

    def test_rejects_incomplete_key_audit(self):
        source = fixture()
        source["quality"]["unique_keys_verified"] = 14
        with self.assertRaises(ValueError): prepare(source)

    def test_source_unchanged(self):
        source = fixture()
        original = copy.deepcopy(source)
        prepare(source)
        self.assertEqual(source, original)

    def test_safe_closed_boundary(self):
        for c in (0, 12):
            with self.subTest(c=c):
                source = fixture()
                source["aggregates"][0]["closed_with_valid_interval"] = c
                self.assertEqual(prepare(source)["aggregates"][0]["closed_with_valid_interval"], c)

    def test_null_is_preserved_not_zero(self):
        source = fixture()
        source["aggregates"][0]["closed_with_valid_interval"] = None
        self.assertIsNone(prepare(source)["aggregates"][0]["closed_with_valid_interval"])


if __name__ == "__main__":
    unittest.main()
