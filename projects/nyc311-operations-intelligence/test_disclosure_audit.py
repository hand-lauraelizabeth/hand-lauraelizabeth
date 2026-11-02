"""Synthetic disclosure-preflight regressions; no NYC 311 request records."""
import csv
import tempfile
import unittest
from pathlib import Path

from disclosure_audit import assess_export
from pipeline import ingest


def synthetic_export(*, minimum=10, suppressed=1, valid=11, visible=10, closed=0):
    return {
        "quality": {"valid_records": valid, "small_cells_suppressed": suppressed},
        "rules": {"display_minimum_cell_count": minimum},
        "aggregates": [{"month": "2026-09", "borough": "QUEENS",
                        "agency": "DOT", "problem": "Synthetic A",
                        "requests": visible,
                        "closed_with_valid_interval": closed}],
    }


class TestDisclosurePreflight(unittest.TestCase):
    def test_single_suppressed_cell_is_exactly_reconstructable(self):
        result = assess_export(synthetic_export())
        self.assertFalse(result["publication_cleared"])
        self.assertIn("exact_suppressed_cell_reconstructable",
                      {finding["code"] for finding in result["findings"]})
        # No recovered small-cell value is emitted in the audit findings.
        self.assertNotIn('"suppressed_count"', str(result))

    def test_multiple_suppressed_cells_reveal_combined_total(self):
        result = assess_export(synthetic_export(suppressed=2, valid=15))
        codes = {finding["code"] for finding in result["findings"]}
        self.assertIn("suppressed_group_total_reconstructable", codes)
        self.assertNotIn("exact_suppressed_cell_reconstructable", codes)

    def test_low_threshold_never_passes_publication_gate(self):
        result = assess_export(synthetic_export(minimum=1, suppressed=0,
                                                valid=1, visible=1))
        codes = {finding["code"] for finding in result["findings"]}
        self.assertIn("publication_threshold_below_review_floor", codes)
        self.assertFalse(result["publication_cleared"])

    def test_no_suppression_still_requires_cross_release_audit(self):
        result = assess_export(synthetic_export(suppressed=0, valid=10))
        self.assertEqual([f["code"] for f in result["findings"]],
                         ["cross_release_and_source_review_pending"])

    def test_inconsistent_metadata_fails_closed(self):
        result = assess_export(synthetic_export(valid=20))
        self.assertIn("suppression_metadata_inconsistent",
                      {finding["code"] for finding in result["findings"]})

    def test_malformed_boolean_count_rejected(self):
        for field in ("valid_records", "small_cells_suppressed"):
            with self.subTest(field=field):
                payload = synthetic_export()
                payload["quality"][field] = True
                with self.assertRaisesRegex(ValueError, "count"):
                    assess_export(payload)

    def test_real_pipeline_shape_reveals_single_hidden_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "synthetic.csv"
            output = Path(tmp) / "private.json"
            with source.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.writer(stream)
                writer.writerow(["unique_key", "created_date", "closed_date",
                                 "agency", "complaint_type", "borough", "status"])
                for n in range(11):
                    writer.writerow([f"fixture-{n}", "2026-09-10T09:00:00",
                                     "", "DOT", "Synthetic A" if n < 10
                                     else "Synthetic B", "Queens", "Open"])
            ingest(source, output, as_of="2026-10-25", min_cell=10)
            import json
            result = assess_export(json.loads(output.read_text(encoding="utf-8")))
            self.assertIn("exact_suppressed_cell_reconstructable",
                          {f["code"] for f in result["findings"]})
            self.assertFalse(result["publication_cleared"])


if __name__ == "__main__":
    unittest.main()
