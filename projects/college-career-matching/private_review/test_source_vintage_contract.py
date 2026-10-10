"""Synthetic-only regression checks for field-level source vintages."""
import unittest
from source_vintage_contract import normalize_source_field

def sample(**kw):
    row = dict(unitid="001234", source_system="ipeds",
        source_record_id="synthetic:001234:2024", field="enrollment",
        status="provided", value=12000, source_variable="EFTOTLT",
        source_url="https://nces.ed.gov/ipeds/", reporting_year=2024,
        collection_period="2023-24", release_date="2026-06-10",
        cohort_year=None, definition="total enrollment")
    return {**row, **kw}

class VintageTests(unittest.TestCase):
    def test_private(self):
        row = normalize_source_field(sample())
        self.assertEqual(row["publication_status"], "DO_NOT_PUBLISH")
        self.assertFalse(row["public_export_allowed"])
        self.assertFalse(row["independently_verified"])
        self.assertIsNone(row["admissions_probability"])

    def test_unitid(self):
        self.assertEqual(normalize_source_field(sample())["unitid"], "001234")

    def test_bad_reporting_year(self):
        for year in ("latest", True, None):
            with self.subTest(year=year), self.assertRaises(ValueError):
                normalize_source_field(sample(reporting_year=year))

    def test_missing_distinct(self):
        row = normalize_source_field(sample(status="missing", value=None))
        self.assertEqual(row["status"], "missing")
        self.assertIsNone(row["value"])

    def test_missing_cannot_carry_value(self):
        with self.assertRaises(ValueError):
            normalize_source_field(sample(status="unknown"))

    def test_cohort_specific_price(self):
        with self.assertRaises(ValueError):
            normalize_source_field(sample(field="net_price"))

    def test_release_date(self):
        with self.assertRaises(ValueError):
            normalize_source_field(sample(release_date="2026-02-30"))

    def test_unexpected_field(self):
        with self.assertRaises(ValueError):
            normalize_source_field({**sample(), "owner_approved": True})

if __name__ == "__main__":
    unittest.main()
