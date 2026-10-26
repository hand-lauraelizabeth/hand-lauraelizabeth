"""Synthetic-only adversarial tests for cross-dimension public marginal audit."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from cross_dimension_marginal_receipt import HOLDS, audit
from test_official_marginal_receipt import receipt

WHERE = "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'"
BASE = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"


def url():
    return BASE + "?" + urlencode({
        "$select": "borough, agency, count(*) as records",
        "$where": WHERE,
        "$group": "borough, agency",
        "$order": "borough, agency",
        "$limit": "1000",
    })


def cross():
    return {"url": url(), "rows": [
        {"borough": "QUEENS", "agency": "SYNTHETIC-A", "records": "1"},
        {"borough": "QUEENS", "agency": "SYNTHETIC-B", "records": "1"},
        {"borough": "BRONX", "agency": "SYNTHETIC-A", "records": "0"},
        {"borough": "BRONX", "agency": "SYNTHETIC-B", "records": "4"},
    ]}


class CrossDimensionMarginalTests(unittest.TestCase):
    def setUp(self):
        self.base = receipt()
        self.cross = cross()

    def findings(self):
        return audit(self.base, self.cross)

    def test_balanced_source_still_holds(self):
        self.assertEqual(self.findings(), sorted(HOLDS))

    def test_citywide_balanced_but_agency_marginal_mismatch(self):
        self.cross["rows"][0]["records"] = "2"
        self.cross["rows"][1]["records"] = "0"
        self.assertIn("cross_agency_marginal_mismatch", self.findings())
        self.assertNotIn("cross_borough_marginal_mismatch", self.findings())

    def test_citywide_balanced_but_borough_marginal_mismatch(self):
        self.cross["rows"][1]["records"] = "2"
        self.cross["rows"][3]["records"] = "3"
        self.assertIn("cross_borough_marginal_mismatch", self.findings())
        self.assertNotIn("cross_agency_marginal_mismatch", self.findings())

    def test_cross_cell_swap_preserves_marginals_but_not_authenticity(self):
        # Mathematical limitation: both one-way marginals can remain identical.
        self.cross["rows"][0]["records"] = "0"
        self.cross["rows"][1]["records"] = "2"
        self.cross["rows"][2]["records"] = "1"
        self.cross["rows"][3]["records"] = "3"
        self.assertEqual(self.findings(), sorted(HOLDS))
        self.assertIn("cross_cells_not_independently_authenticated", self.findings())

    def test_missing_positive_pair(self):
        self.cross["rows"].pop(0)
        self.assertIn("cross_borough_marginal_mismatch", self.findings())
        self.assertIn("cross_agency_marginal_mismatch", self.findings())

    def test_omitted_zero_pair_is_not_a_false_mismatch(self):
        self.cross["rows"].pop(2)
        self.assertEqual(self.findings(), sorted(HOLDS))

    def test_unrecognized_agency(self):
        self.cross["rows"][0]["agency"] = "SYNTHETIC-UNKNOWN"
        self.assertIn("cross_category_not_in_marginals", self.findings())

    def test_unrecognized_borough(self):
        self.cross["rows"][0]["borough"] = "SYNTHETIC-UNKNOWN"
        self.assertIn("cross_category_not_in_marginals", self.findings())

    def test_duplicate_pair_rejected(self):
        self.cross["rows"].append(copy.deepcopy(self.cross["rows"][0]))
        self.assertIn("cross_response_invalid", self.findings())

    def test_record_level_identifier_rejected(self):
        self.cross["rows"][0]["unique_key"] = "SYNTHETIC-PRIVATE-KEY"
        self.assertIn("cross_response_invalid", self.findings())

    def test_malformed_counts_rejected(self):
        for bad in (True, -1, 1.5, "01", "1.0", None, {}):
            with self.subTest(bad=bad):
                self.cross = cross()
                self.cross["rows"][0]["records"] = bad
                self.assertIn("cross_response_invalid", self.findings())

    def test_blank_category_rejected(self):
        self.cross["rows"][0]["borough"] = " "
        self.assertIn("cross_response_invalid", self.findings())

    def test_wrong_month_query_rejected(self):
        self.cross["url"] = url().replace("2026-09-01", "2026-08-01")
        self.assertIn("cross_query_scope_invalid", self.findings())

    def test_limit_cannot_be_removed(self):
        self.cross["url"] = url().replace("&%24limit=1000", "")
        self.assertIn("cross_query_scope_invalid", self.findings())

    def test_query_cannot_change_dataset(self):
        self.cross["url"] = url().replace("erm2-nwe9", "different")
        self.assertIn("cross_query_scope_invalid", self.findings())

    def test_query_cannot_use_unapproved_group(self):
        self.cross["url"] = url().replace("borough%2C+agency", "agency")
        self.assertIn("cross_query_scope_invalid", self.findings())

    def test_base_receipt_mismatch_not_overlooked(self):
        self.base["queries"]["cohort"]["rows"][0]["records"] = "7"
        self.assertIn("base_marginals_invalid", self.findings())

    def test_cross_schema_and_empty_rows(self):
        self.cross["extra"] = "not allowed"
        self.assertIn("cross_query_scope_invalid", self.findings())
        self.cross = cross()
        self.cross["rows"] = []
        self.assertIn("cross_response_invalid", self.findings())

    def test_cli_fails_closed_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "private_four.json"
            b = Path(tmp) / "private_cross.json"
            a.write_text(json.dumps(self.base), encoding="utf-8")
            b.write_text(json.dumps(self.cross), encoding="utf-8")
            p = subprocess.run([
                sys.executable,
                str(Path(__file__).with_name("cross_dimension_marginal_receipt.py")),
                str(a), str(b)], capture_output=True, text=True, check=False)
            self.assertEqual(p.returncode, 2, p.stderr)
            output = json.loads(p.stdout)
            self.assertTrue(output["hold"])
            self.assertFalse(output["publication_approved"])
            self.assertNotIn("SYNTHETIC-A", p.stdout)
            self.assertNotIn("QUEENS", p.stdout)
            self.assertNotIn("323630", p.stdout)


if __name__ == "__main__":
    unittest.main()
