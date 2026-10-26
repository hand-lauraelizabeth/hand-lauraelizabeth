"""Synthetic-only negative controls for source-only public marginal receipts."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlencode

from official_marginal_receipt import BASE, DIMENSIONS, audit

MONTH = "2026-09"
WHERE = "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'"


def url(dimension):
    select = ("count(*) as records, count(distinct unique_key) as distinct_keys"
              if dimension == "cohort" else dimension + ", count(*) as records")
    params = {"$select": select, "$where": WHERE}
    if dimension != "cohort":
        params.update({"$group": dimension, "$order": dimension})
    return BASE + "?" + urlencode(params)


def receipt():
    return {"dataset_id": "erm2-nwe9", "reporting_month": MONTH, "queries": {
        "cohort": {"url": url("cohort"), "rows": [{"records": "6", "distinct_keys": "6"}]},
        "borough": {"url": url("borough"), "rows": [
            {"borough": "QUEENS", "records": "2"}, {"borough": "BRONX", "records": "4"}]},
        "agency": {"url": url("agency"), "rows": [
            {"agency": "SYNTHETIC-A", "records": "1"}, {"agency": "SYNTHETIC-B", "records": "5"}]},
        "status": {"url": url("status"), "rows": [
            {"status": "Open", "records": "3"}, {"status": "Closed", "records": "3"}]},
    }}


class IndependentPublicMarginalReceiptTests(unittest.TestCase):
    def setUp(self):
        self.data = receipt()

    def test_balanced_independent_totals_still_hold(self):
        findings = audit(self.data)
        self.assertEqual(findings, sorted([
            "source_queries_not_atomic", "official_csv_origin_not_authenticated",
            "privacy_and_temporal_release_review_pending"]))

    def test_borough_total_mismatch(self):
        self.data["queries"]["borough"]["rows"][0]["records"] = "3"
        self.assertIn("mismatched_borough_marginal", audit(self.data))

    def test_agency_total_mismatch(self):
        self.data["queries"]["agency"]["rows"][1]["records"] = "4"
        self.assertIn("mismatched_agency_marginal", audit(self.data))

    def test_status_total_mismatch(self):
        self.data["queries"]["status"]["rows"][1]["records"] = "4"
        self.assertIn("mismatched_status_marginal", audit(self.data))

    def test_distinct_keys_less_than_rows(self):
        self.data["queries"]["cohort"]["rows"][0]["distinct_keys"] = "5"
        self.assertIn("cohort_duplicate_or_missing_unique_keys", audit(self.data))

    def test_distinct_keys_cannot_exceed_rows(self):
        self.data["queries"]["cohort"]["rows"][0]["distinct_keys"] = "7"
        self.assertIn("distinct_key_count_exceeds_rows", audit(self.data))

    def test_query_where_cannot_shift_month(self):
        self.data["queries"]["agency"]["url"] = url("agency").replace("2026-09-01", "2026-08-01")
        self.assertIn("unverified_or_mismatched_query_scope", audit(self.data))

    def test_query_cannot_change_host(self):
        self.data["queries"]["cohort"]["url"] = url("cohort").replace("data.cityofnewyork.us", "example.org")
        self.assertIn("unverified_or_mismatched_query_scope", audit(self.data))

    def test_query_cannot_be_limited(self):
        self.data["queries"]["status"]["url"] += "&%24limit=1"
        self.assertIn("unverified_or_mismatched_query_scope", audit(self.data))

    def test_duplicate_group_label(self):
        self.data["queries"]["borough"]["rows"][1]["borough"] = "QUEENS"
        self.assertIn("invalid_aggregate_response", audit(self.data))

    def test_bool_negative_float_and_bad_string_counts(self):
        for bad in (True, -1, 1.5, "6.0", "03"):
            with self.subTest(bad=bad):
                data = receipt()
                data["queries"]["agency"]["rows"][0]["records"] = bad
                self.assertIn("invalid_aggregate_response", audit(data))

    def test_missing_or_extra_query_dimension(self):
        self.data["queries"].pop("status")
        self.assertIn("invalid_receipt_schema", audit(self.data))

    def test_invalid_month_rejected(self):
        self.data["reporting_month"] = "2026-13"
        self.assertIn("unverified_or_mismatched_query_scope", audit(self.data))

    def test_empty_grouped_response_rejected(self):
        self.data["queries"]["agency"]["rows"] = []
        self.assertIn("invalid_aggregate_response", audit(self.data))

    def test_record_level_fields_rejected(self):
        self.data["queries"]["cohort"]["rows"][0]["unique_key"] = "SYNTHETIC-PRIVATE-KEY"
        self.assertIn("invalid_aggregate_response", audit(self.data))

    def test_cli_holds_and_does_not_echo_source_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "private.json"
            p.write_text(json.dumps(self.data), encoding="utf-8")
            run = subprocess.run([sys.executable,
                str(Path(__file__).with_name("official_marginal_receipt.py")), str(p)],
                capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 2, run.stderr)
            output = json.loads(run.stdout)
            self.assertTrue(output["hold"])
            self.assertFalse(output["publication_approved"])
            self.assertNotIn("SYNTHETIC-A", run.stdout)
            self.assertNotIn("QUEENS", run.stdout)
            self.assertNotIn("6", run.stdout)


if __name__ == "__main__":
    unittest.main()
