"""Synthetic adversarial tests for the strict NYC 311 request allowlist."""
from copy import deepcopy
from urllib.parse import urlencode
import unittest

from aggregate_query_request_gate import (ENDPOINT, MONTH, COUNT_SELECT,
                                          audit_with_requests)
from aggregate_query_variant_gate import HOLD, VERIFIED


def make_url(**params):
    return ENDPOINT + "?" + urlencode({"$" + k: v for k, v in params.items()})


class RequestGateTests(unittest.TestCase):
    def setUp(self):
        self.meta = {"id": "erm2-nwe9", "publicationStage": "published",
                     "rowIdentifierColumnId": 623546861,
                     "rowsUpdatedAt": 1793151360}
        self.cohort = {"records": "45", "distinct_keys": "45"}
        self.pairs = [{"borough": "BRONX", "agency": "A", "n": "30"},
                      {"borough": "QUEENS", "agency": "B", "n": "15"}]
        self.triples = [
            {"borough": "BRONX", "agency": "A", "status": "Open", "n": "18"},
            {"borough": "BRONX", "agency": "A", "status": "Closed", "n": "12"},
            {"borough": "QUEENS", "agency": "B", "status": "Open", "n": "15"},
        ]
        self.urls = {
            "cohort": make_url(select=COUNT_SELECT, where=MONTH),
            "pairs_primary": make_url(select="borough,agency,count(*) as n",
                                      where=MONTH, group="borough,agency",
                                      order="borough,agency", limit="50000"),
            "pairs_alternate": make_url(select="borough,agency,count(*) as n",
                                        where=MONTH, group="borough,agency",
                                        order="agency,borough", limit="50000",
                                        offset="0"),
            "triples_primary": make_url(select="borough,agency,status,count(*) as n",
                                        where=MONTH, group="borough,agency,status",
                                        order="borough,agency,status", limit="50000"),
            "triples_alternate": make_url(select="borough,agency,status,count(*) as n",
                                          where=MONTH, group="borough,agency,status",
                                          order="status,borough,agency", limit="50000",
                                          offset="0"),
        }

    def codes(self):
        return audit_with_requests(self.meta, self.meta, self.cohort,
                                   self.pairs, deepcopy(self.pairs),
                                   self.triples, deepcopy(self.triples), self.urls)

    def test_valid_order_variants_still_hold_for_provenance(self):
        self.assertEqual(self.codes(), [HOLD, VERIFIED])

    def test_changed_date_bound_rejected(self):
        self.urls["pairs_alternate"] = self.urls["pairs_alternate"].replace(
            "2026-10-01", "2026-10-02")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_different_dataset_rejected(self):
        self.urls["pairs_primary"] = self.urls["pairs_primary"].replace(
            "erm2-nwe9", "76ig-c548")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_http_and_external_host_rejected(self):
        for url in (self.urls["cohort"].replace("https:", "http:"),
                    self.urls["cohort"].replace("data.cityofnewyork.us", "evil.example")):
            with self.subTest(url=url):
                self.urls["cohort"] = url
                self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_extra_filter_rejected(self):
        self.urls["cohort"] += "&%24where=1%3D1"
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_extra_unreviewed_clause_rejected(self):
        self.urls["pairs_primary"] += "&%24having=n%3E1"
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_truncated_limit_rejected(self):
        self.urls["triples_primary"] = self.urls["triples_primary"].replace(
            "50000", "50")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_nonzero_offset_rejected(self):
        self.urls["pairs_alternate"] = self.urls["pairs_alternate"].replace(
            "offset=0", "offset=1")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_same_order_is_not_an_independent_challenge(self):
        self.urls["pairs_alternate"] = self.urls["pairs_primary"]
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_wrong_group_dimensions_rejected(self):
        self.urls["triples_primary"] = self.urls["triples_primary"].replace(
            "borough%2Cagency%2Cstatus", "borough%2Cagency")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_missing_request_rejected(self):
        del self.urls["cohort"]
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_unexpected_url_field_rejected(self):
        self.urls["notes"] = "extra"
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_redacted_failure_does_not_leak_query(self):
        self.urls["pairs_primary"] += "&secret=DO_NOT_PRINT"
        result = repr(self.codes())
        self.assertNotIn("DO_NOT_PRINT", result)
        self.assertNotIn("BRONX", result)
        self.assertNotIn(VERIFIED, result)

    def test_missing_required_limit_even_with_offset_fails_closed(self):
        self.urls["pairs_alternate"] = self.urls["pairs_alternate"].replace(
            "&%24limit=50000", "")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_fragment_and_userinfo_are_rejected(self):
        original = self.urls["cohort"]
        for url in (original + "#fake", original.replace(
                "data.cityofnewyork.us", "user@data.cityofnewyork.us")):
            with self.subTest(url=url):
                self.urls["cohort"] = url
                self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_cohort_unique_key_requirement_cannot_be_removed(self):
        self.urls["cohort"] = self.urls["cohort"].replace(
            "distinct+unique_key", "distinct+agency")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_wrong_order_not_a_reviewed_variant(self):
        self.urls["triples_alternate"] = self.urls["triples_alternate"].replace(
            "status%2Cborough%2Cagency", "status%2Cagency%2Cborough")
        self.assertIn("QUERY_REQUEST_EVIDENCE_INVALID", self.codes())

    def test_changed_aggregate_data_still_fails_arithmetic_gate(self):
        self.pairs[0]["n"] = "29"
        self.assertIn("COHORT_TOTAL_MISMATCH", self.codes())
        self.assertNotIn(VERIFIED, self.codes())


if __name__ == "__main__":
    unittest.main()
