"""Regression tests for the institution-level national IPEDS enrichment bridge."""
import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ipeds_bridge", BASE / "national_ipeds_completion_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def baseline(unitid, locale=None):
    row = [None] * 23
    row[0] = unitid
    row[1] = "Fixture College " + unitid
    row[16] = locale
    return row


class NationalBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.national = self.root / "national"
        self.national.mkdir()
        self.output = self.root / "output"
        self.hd = self.root / "HD2025.csv"
        self.c = self.root / "C2025_A.csv"
        self.records = [baseline("123456", "12"), baseline("12345678", "21"), baseline("654321")]
        self.write_base()
        self.write_csv(self.hd, ["UNITID", "LOCALE"], [
            ["123456", "11"], ["654321", "43"], ["987654", "32"]
        ])
        self.write_csv(self.c, ["UNITID", "MAJORNUM", "CIPCODE", "AWLEVEL", "CTOTALT"], [
            ["123456", "1", "11.0101", "5", "12"],
            ["123456", "1", "13.0101", "3", "PS"],
            ["123456", "2", "11.0101", "5", "2"],
            ["123456", "1", "99.0000", "5", "14"],
            ["123456", "1", "11.0101", "20", "4"],
            ["987654", "1", "11.0101", "5", "7"],
        ])

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def write_csv(path, headers, rows):
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            w.writerows(rows)

    def write_base(self):
        path = self.national / "national-00.json"
        path.write_text(json.dumps({"schema_version": "1.0", "part": 0, "records": self.records}), encoding="utf-8")
        self.sha = hashlib.sha256(path.read_bytes()).hexdigest()
        (self.national / "manifest.v1.json").write_text(json.dumps({
            "data_version": "synthetic-national-v1", "expected_records": len(self.records),
            "row_layout": ["unitid"] + ["field_" + str(i) for i in range(1, 16)] + ["locale_code"] + ["field_" + str(i) for i in range(17, 23)],
            "shards": [{"file": "national-00.json", "count": len(self.records), "sha256": self.sha}]
        }), encoding="utf-8")

    def test_full_build_preserves_extension_and_missing_counts(self):
        result = bridge.build(self.national, self.hd, self.c, self.output)
        self.assertFalse(result["publication_authorized"])
        rows = json.loads((self.output / "enrichment-00.json").read_text())["records"]
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0][0:2], ["123456", "11"])
        self.assertEqual(rows[1], ["12345678", None, []])
        self.assertEqual(rows[2], ["654321", "43", []])
        self.assertEqual(rows[0][2], [
            ["11", 1, ["5"], 12, 0],
            ["13", 1, ["3"], 0, 1]
        ])
        counts = result["counts"]
        self.assertEqual(counts["exact_six_digit_hd2025_matches"], 2)
        self.assertEqual(counts["independent_ipeds_locale_cells"], 2)
        self.assertEqual(counts["scorecard_ipeds_locale_disagreements"], 1)
        self.assertEqual(counts["second_major_rows_excluded"], 1)
        self.assertEqual(counts["summary_or_invalid_cip_rows_excluded"], 1)
        self.assertEqual(counts["rollup_or_overlapping_award_rows_excluded"], 1)
        self.assertEqual(result["scorecard_data_version"], "synthetic-national-v1")

    def test_duplicate_first_major_is_rejected(self):
        self.write_csv(self.c, ["UNITID", "MAJORNUM", "CIP6", "AWLEVEL", "CTOTALT"], [
            ["123456", "1", "110101", "5", "12"],
            ["123456", "1", "110101", "5", "15"],
        ])
        with self.assertRaisesRegex(ValueError, "Duplicate first-major"):
            bridge.build(self.national, self.hd, self.c, self.output)

    def test_negative_completion_not_coerced_to_zero(self):
        self.write_csv(self.c, ["UNITID", "MAJORNUM", "CIPCODE", "AWLEVEL", "CTOTALT"], [
            ["123456", "1", "11.0101", "5", "-9"]
        ])
        with self.assertRaisesRegex(ValueError, "Invalid completion count"):
            bridge.build(self.national, self.hd, self.c, self.output)

    def test_shard_hash_mismatch_is_fatal(self):
        (self.national / "national-00.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "integrity mismatch"):
            bridge.build(self.national, self.hd, self.c, self.output)

    def test_broken_headers_fail_closed(self):
        self.write_csv(self.hd, ["UNITID", "WRONG"], [["123456", "11"]])
        with self.assertRaisesRegex(ValueError, "LOCALE"):
            bridge.build(self.national, self.hd, self.c, self.output)

    def test_id_must_not_be_coerced_to_parent(self):
        hd = [{"UNITID": "123456", "LOCALE": "11"}]
        completions = [{"UNITID": "123456", "MAJORNUM": "1", "CIPCODE": "11.0101",
                        "AWLEVEL": "5", "CTOTALT": "1"}]
        shards, coverage = bridge.build_enrichment([("national-00.json", [baseline("12345678")])], hd, completions)
        self.assertEqual(shards[0][1], [["12345678", None, []]])
        self.assertEqual(coverage["exact_six_digit_hd2025_matches"], 0)
        self.assertEqual(coverage["institutions_with_2024_25_first_major_completions"], 0)


if __name__ == "__main__":
    unittest.main()
