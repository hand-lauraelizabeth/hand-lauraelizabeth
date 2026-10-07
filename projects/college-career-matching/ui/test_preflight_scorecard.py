"""Synthetic preflight tests; no official institution data bundled."""
import csv
import hashlib
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location("preflight", Path(__file__).with_name("preflight_scorecard.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "sample.csv"
        self.headers = ["UNITID", "INSTNM", "CONTROL", *[f"NPT4{i}_PUB" for i in range(1, 6)]]
        self.write_headers(self.headers)

    def tearDown(self):
        self.tmp.cleanup()

    def write_headers(self, headers):
        with self.path.open("w", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerow(headers)

    def test_single_csv_zip_preflight(self):
        archive_path = Path(self.tmp.name) / "institution.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(self.path, arcname="institution.csv")
        self.assertEqual(preflight.inspect(archive_path, "PUB")["header_check"], "PASS")

    def test_macos_resource_fork_is_not_second_dataset(self):
        archive_path = Path(self.tmp.name) / "institution.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(self.path, arcname="Most-Recent-Cohorts-Institution.csv")
            archive.writestr("__MACOSX/._Most-Recent-Cohorts-Institution.csv", b"resource fork")
        self.assertEqual(preflight.inspect(archive_path, "PUB")["header_check"], "PASS")

    def test_multiple_csv_zip_rejected(self):
        archive_path = Path(self.tmp.name) / "institution.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(self.path, arcname="one.csv")
            archive.write(self.path, arcname="two.csv")
        with self.assertRaisesRegex(ValueError, "exactly one CSV"):
            preflight.inspect(archive_path, "PUB")

    def test_valid_public_headers(self):
        self.assertEqual(preflight.inspect(self.path, "PUB")["header_check"], "PASS")

    def test_sha256_identifies_exact_input_bytes(self):
        expected = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(preflight.inspect(self.path, "PUB")["sha256"], expected)
        self.assertEqual(len(expected), 64)

    def test_missing_income_band_rejected(self):
        self.write_headers(self.headers[:-1])
        with self.assertRaisesRegex(ValueError, "NPT45_PUB"):
            preflight.inspect(self.path, "PUB")

    def test_wrong_population_rejected(self):
        with self.assertRaisesRegex(ValueError, "NPT41_PRIV"):
            preflight.inspect(self.path, "PRIV")

    def test_duplicate_headers_rejected(self):
        self.write_headers([*self.headers, "UNITID"])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            preflight.inspect(self.path, "PUB")

    def test_blank_headers_rejected(self):
        self.write_headers([*self.headers, ""])
        with self.assertRaisesRegex(ValueError, "blank"):
            preflight.inspect(self.path, "PUB")


if __name__ == "__main__":
    unittest.main()
