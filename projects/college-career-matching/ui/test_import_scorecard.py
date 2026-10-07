"""Importer tests using synthetic CSV and reviewed metadata fixtures."""
import copy
import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("scorecard_importer", Path(__file__).with_name("import_scorecard.py"))
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

META = {
    "release_year": 2025,
    "net_price_reference_year": 2023,
    "source_url": "https://collegescorecard.ed.gov/example.csv",
    "institutions": {"123456": {
        "population": "PUB", "setting": "Urban", "housing": True,
        "access": None, "aid": [],
        "careers": {"data": None, "education": None, "health": None, "business": None}
    }}
}


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "sample.csv"
        self.row = {"UNITID": "123456", "INSTNM": "Example University", "CONTROL": "1",
                    **{f"NPT4{i}_PUB": v for i, v in enumerate(("0", "PS", "4500", "7000", "10000"), 1)}}
        self.write_rows([self.row])

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, rows):
        with self.path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.row.keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_import_preserves_zero_and_suppressed(self):
        payload = importer.convert(self.path, copy.deepcopy(META))
        costs = payload["records"][0]["cost"]
        self.assertEqual(costs["0_30k"], 0)
        self.assertIsNone(costs["30_48k"])
        self.assertEqual(costs["48_75k"], 4500)
        self.assertIsNone(payload["records"][0]["access"])
        self.assertEqual(payload["records"][0]["reference_year"], 2023)

    def test_negative_net_price_preserved(self):
        self.row["NPT41_PUB"] = "-275"
        self.write_rows([self.row])
        self.assertEqual(importer.convert(self.path, META)["records"][0]["cost"]["0_30k"], -275)

    def test_privacy_suppressed_marker_is_missing(self):
        self.row["NPT42_PUB"] = "PrivacySuppressed"
        self.write_rows([self.row])
        self.assertIsNone(importer.convert(self.path, META)["records"][0]["cost"]["30_48k"])

    def test_duplicate_csv_header_fails(self):
        with self.path.open("w", encoding="utf-8") as f:
            f.write(",".join([*self.row.keys(), "NPT41_PUB"]) + "\n")
            f.write(",".join([*self.row.values(), "999"]) + "\n")
        with self.assertRaisesRegex(ValueError, "Duplicate CSV header"):
            importer.convert(self.path, META)

    def test_extra_csv_cell_fails(self):
        with self.path.open("w", encoding="utf-8") as f:
            f.write(",".join(self.row.keys()) + "\n")
            f.write(",".join([*self.row.values(), "unexpected"]) + "\n")
        with self.assertRaisesRegex(ValueError, "more values"):
            importer.convert(self.path, META)

    def test_official_2026_download_host_accepted(self):
        meta = copy.deepcopy(META)
        meta["source_url"] = "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_06102026.zip"
        self.assertEqual(len(importer.convert(self.path, meta)["records"]), 1)

    def test_broad_ed_gov_host_rejected(self):
        meta = copy.deepcopy(META)
        meta["source_url"] = "https://unrelated.ed.gov/file.csv"
        with self.assertRaisesRegex(ValueError, "official Department"):
            importer.convert(self.path, meta)

    def test_unofficial_source_host_rejected(self):
        meta = copy.deepcopy(META)
        meta["source_url"] = "https://collegescorecard.ed.gov.evil.example/data.csv"
        with self.assertRaisesRegex(ValueError, "official Department"):
            importer.convert(self.path, meta)

    def test_unofficial_source_credentials_rejected(self):
        meta = copy.deepcopy(META)
        meta["source_url"] = "https://someone@collegescorecard.ed.gov/data.csv"
        with self.assertRaisesRegex(ValueError, "official Department"):
            importer.convert(self.path, meta)

    def test_missing_price_reference_year_fails(self):
        meta = copy.deepcopy(META)
        del meta["net_price_reference_year"]
        with self.assertRaisesRegex(ValueError, "net_price_reference_year"):
            importer.convert(self.path, meta)

    def test_future_price_reference_year_fails(self):
        meta = copy.deepcopy(META)
        meta["net_price_reference_year"] = 2026
        with self.assertRaisesRegex(ValueError, "net_price_reference_year"):
            importer.convert(self.path, meta)

    def test_invalid_control_code_rejected(self):
        self.row["CONTROL"] = "9"
        self.write_rows([self.row])
        with self.assertRaisesRegex(ValueError, "Unrecognized CONTROL"):
            importer.convert(self.path, META)

    def test_malformed_reviewed_unitid_rejected(self):
        meta = copy.deepcopy(META)
        meta["institutions"] = {"12345X": meta["institutions"]["123456"]}
        with self.assertRaisesRegex(ValueError, "six-digit ASCII"):
            importer.convert(self.path, meta)

    def test_malformed_csv_unitid_rejected(self):
        self.row["UNITID"] = "1234567"
        self.write_rows([self.row])
        meta = copy.deepcopy(META)
        meta["institutions"] = {"1234567": meta["institutions"]["123456"]}
        with self.assertRaisesRegex(ValueError, "six-digit ASCII"):
            importer.convert(self.path, meta)

    def test_missing_unitid_fails(self):
        meta = copy.deepcopy(META)
        meta["institutions"] = {"999999": meta["institutions"]["123456"]}
        with self.assertRaisesRegex(ValueError, "absent"):
            importer.convert(self.path, meta)

    def test_missing_population_fails(self):
        meta = copy.deepcopy(META)
        del meta["institutions"]["123456"]["population"]
        with self.assertRaisesRegex(ValueError, "population"):
            importer.convert(self.path, meta)

    def test_unexpected_price_fails(self):
        self.row["NPT41_PUB"] = "not a price"
        self.write_rows([self.row])
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            importer.convert(self.path, META)

    def test_duplicate_unitid_fails(self):
        self.write_rows([self.row, self.row])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            importer.convert(self.path, META)

    def test_conflicting_public_private_population_fails(self):
        self.row["CONTROL"] = "2"
        self.write_rows([self.row])
        with self.assertRaisesRegex(ValueError, "conflicts with CONTROL"):
            importer.convert(self.path, META)

    def test_unavailable_control_does_not_claim_validation(self):
        self.row["CONTROL"] = ""
        self.write_rows([self.row])
        self.assertEqual(len(importer.convert(self.path, META)["records"]), 1)

    def test_missing_name_fails(self):
        self.row["INSTNM"] = ""
        self.write_rows([self.row])
        with self.assertRaisesRegex(ValueError, "Missing institution name"):
            importer.convert(self.path, META)

    def test_unreviewed_records_not_exported(self):
        extra = dict(self.row, UNITID="654321", INSTNM="Other Institution")
        self.write_rows([self.row, extra])
        payload = importer.convert(self.path, META)
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["name"], "Example University")


if __name__ == "__main__":
    unittest.main()
