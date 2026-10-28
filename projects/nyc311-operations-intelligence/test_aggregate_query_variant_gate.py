"""Adversarial synthetic checks for NYC 311 query-order snapshot drift."""
from copy import deepcopy
import unittest

from aggregate_query_variant_gate import audit, HOLD, VERIFIED


class QueryVariantGateTests(unittest.TestCase):
    def setUp(self):
        self.meta = {
            "id": "erm2-nwe9", "publicationStage": "published",
            "rowIdentifierColumnId": 623546861,
            "rowsUpdatedAt": 1793151360,
        }
        self.cohort = {"records": "45", "distinct_keys": "45"}
        self.pairs = [
            {"borough": "BRONX", "agency": "A", "n": "30"},
            {"borough": "QUEENS", "agency": "B", "n": "15"},
        ]
        self.triples = [
            {"borough": "BRONX", "agency": "A", "status": "Open", "n": "18"},
            {"borough": "BRONX", "agency": "A", "status": "Closed", "n": "12"},
            {"borough": "QUEENS", "agency": "B", "status": "Open", "n": "15"},
        ]
        self.pair_alt = deepcopy(self.pairs)
        self.triple_alt = deepcopy(self.triples)
        self.after = deepcopy(self.meta)

    def codes(self):
        return audit(self.meta, self.after, self.cohort, self.pairs,
                     self.pair_alt, self.triples, self.triple_alt)

    def test_consistent_variants_are_only_private_arithmetic_verified(self):
        self.assertEqual(self.codes(), [HOLD, VERIFIED])

    def test_balanced_pair_variant_drift_detected_with_same_total(self):
        self.pair_alt[0]["n"] = "29"
        self.pair_alt[1]["n"] = "16"
        self.assertIn("TWO_WAY_QUERY_VARIANTS_DISAGREE", self.codes())
        self.assertNotIn(VERIFIED, self.codes())

    def test_status_only_variant_drift_detected_even_when_pairs_match(self):
        self.triple_alt[0]["n"] = "17"
        self.triple_alt[1]["n"] = "13"
        codes = self.codes()
        self.assertIn("THREE_WAY_QUERY_VARIANTS_DISAGREE", codes)
        self.assertNotIn("CROSS_DIMENSION_MARGINAL_MISMATCH", codes)

    def test_three_way_pair_mismatch_detected(self):
        self.triples[0]["n"] = "17"
        self.triples[1]["n"] = "14"
        self.triple_alt = deepcopy(self.triples)
        self.assertIn("CROSS_DIMENSION_MARGINAL_MISMATCH", self.codes())

    def test_metadata_change_detected_without_updated_clock_change(self):
        self.after["rowIdentifierColumnId"] = 123
        self.assertIn("AGGREGATE_EVIDENCE_INVALID", self.codes())

    def test_timestamp_change_detected(self):
        self.after["rowsUpdatedAt"] += 1
        self.assertIn("PUBLISHER_METADATA_CHANGED", self.codes())

    def test_duplicate_key_count_rejected(self):
        self.cohort["distinct_keys"] = "44"
        self.assertIn("COHORT_KEYS_NOT_UNIQUE", self.codes())

    def test_duplicate_aggregate_group_rejected(self):
        self.pair_alt.append(deepcopy(self.pair_alt[0]))
        self.assertIn("AGGREGATE_EVIDENCE_INVALID", self.codes())

    def test_boolean_negative_and_noncanonical_counts_rejected(self):
        for bad in (True, -1, "0001", "1.0", None):
            with self.subTest(bad=bad):
                self.pair_alt[0]["n"] = bad
                self.assertIn("AGGREGATE_EVIDENCE_INVALID", self.codes())

    def test_empty_aggregate_rejected(self):
        self.triple_alt = []
        self.assertIn("AGGREGATE_EVIDENCE_INVALID", self.codes())

    def test_redacted_codes_never_include_source_labels_or_counts(self):
        self.pair_alt[0]["n"] = "29"
        codes = repr(self.codes())
        for secret in ("BRONX", "QUEENS", "Open", "Closed", "29", "45"):
            self.assertNotIn(secret, codes)


if __name__ == "__main__":
    unittest.main()
