"""Fail-closed regression tests for the six-digit NCES program evidence index."""
import csv
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import national_ipeds_program_index as program


class NationalProgramEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.national = self.root / "national"
        self.national.mkdir()
        self.out = self.root / "programs"
        self.cip = self.root / "CIPCode2020.csv"
        self.completions = self.root / "C2025_A.csv"
        self.write_csv(self.cip, ["CIPCode", "CIPTitle"], [
            ["11", "Computer and information sciences"],
            ['="11.0101"', "Computer and Information Sciences, General."],
            ['="51.3801"', "Registered Nursing/Registered Nurse."],
        ])
        self.write_csv(self.completions,
            ["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"], [
            ["123456", "11.0101", "1", "5", "12"],
            ["123456", "51.3801", "1", "3", "PS"],
            ["123456", "51.3801", "1", "5", "0"],
            ["123456", "51.3801", "2", "5", "4"],
            ["123456", "11.0101", "1", "12", "12"],
            ["999999", "11.0101", "1", "5", "2"],
        ])
        rows = [self.baseline("123456"), self.baseline("12345678"), self.baseline("654321")]
        national_file = self.national / "national-00.json"
        national_file.write_text(json.dumps({"schema_version": "1.0", "part": 0, "records": rows}))
        (self.national / "manifest.v1.json").write_text(json.dumps({
            "data_version": "test-scorecard-v1",
            "expected_records": 3,
            "row_layout": ["unitid"] + ["field_" + str(i) for i in range(1, 16)]
                + ["locale_code"] + ["field_" + str(i) for i in range(17, 23)],
            "shards": [{"file": "national-00.json", "count": 3,
                        "sha256": hashlib.sha256(national_file.read_bytes()).hexdigest()}]
        }))

    @staticmethod
    def baseline(unitid):
        row = [None] * 23
        row[0] = unitid
        return row

    @staticmethod
    def write_csv(path, columns, rows):
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows(rows)

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_cip6_awlevel_records_no_licensure_claim(self):
        m = program.build(self.national, self.completions, self.cip, self.out)
        self.assertFalse(m["current_program_offering_verified"])
        self.assertFalse(m["professional_license_eligibility_verified"])
        self.assertFalse(m["admissions_and_career_matching_authorized"])
        self.assertEqual(m["counts"]["national_institutions"], 3)
        self.assertEqual(m["counts"]["institutions_with_historical_program_completions"], 1)
        self.assertEqual(m["counts"]["joined_program_award_records"], 3)
        self.assertEqual(m["counts"]["source_rows_outside_national_universe"], 1)
        self.assertEqual(m["counts"]["second_major_excluded"], 1)
        self.assertEqual(m["counts"]["overlapping_award_totals_excluded"], 1)
        rows = json.loads((self.out / "programs-00.json").read_text())["institutions"]
        self.assertEqual(rows, [["123456", [
            ["110101", "5", 12, "reported"],
            ["513801", "3", None, "missing_or_suppressed"],
            ["513801", "5", 0, "reported"]
        ]]])
        self.assertEqual(m["counts"]["national_institutions_without_joined_completions"], 2)
        raw = (self.out / "programs-00.json").read_bytes()
        self.assertEqual(gzip.decompress((self.out / "programs-00.json.gz").read_bytes()), raw)
        self.assertLess(m["shards"][0]["gzip_bytes"], 768000)
        self.assertIn("513801", json.loads((self.out / "cip2020-titles.json").read_text()))
        self.assertIn("completions", m["sources"])

    def test_zip_input_and_nces_headers(self):
        source_zip = self.root / "official.zip"
        with zipfile.ZipFile(source_zip, "w") as z:
            z.write(self.completions, "C2025_A.csv")
        cip_zip = self.root / "classification.zip"
        with zipfile.ZipFile(cip_zip, "w") as z:
            z.write(self.cip, "CIPCode2020.csv")
        m = program.build(self.national, source_zip, cip_zip, self.out)
        self.assertEqual(m["counts"]["joined_program_award_records"], 3)

    def test_duplicate_program_identity_fails(self):
        with self.completions.open("a") as stream:
            stream.write("123456,11.0101,1,5,7\n")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            program.build(self.national, self.completions, self.cip, self.out)

    def test_unsupported_award_level_fails(self):
        self.write_csv(self.completions,
            ["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"],
            [["123456", "11.0101", "1", "99", "1"]])
        with self.assertRaisesRegex(ValueError, "Unexpected NCES award level"):
            program.build(self.national, self.completions, self.cip, self.out)

    def test_unknown_cip_title_fails(self):
        self.write_csv(self.completions,
            ["UNITID", "CIPCODE", "MAJORNUM", "AWLEVEL", "CTOTALT"],
            [["123456", "51.3901", "1", "1", "5"]])
        with self.assertRaisesRegex(ValueError, "title missing"):
            program.build(self.national, self.completions, self.cip, self.out)

    def test_suppressed_count_not_zero_and_negative_rejected(self):
        self.assertEqual(program.reported_count("PS"), (None, "missing_or_suppressed"))
        self.assertEqual(program.reported_count("-1"), (None, "missing_or_suppressed"))
        self.assertEqual(program.reported_count("0"), (0, "reported"))
        with self.assertRaisesRegex(ValueError, "Invalid IPEDS"):
            program.reported_count("-9")

    def test_manifest_checksum_fails_closed(self):
        (self.national / "national-00.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            program.build(self.national, self.completions, self.cip, self.out)


if __name__ == "__main__":
    unittest.main()
