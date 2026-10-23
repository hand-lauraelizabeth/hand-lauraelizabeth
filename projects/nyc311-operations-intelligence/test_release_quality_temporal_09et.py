"""Synthetic-only tests for quality-counter differencing in paired releases."""
import copy
import json
import unittest

import release_disclosure_audit as gate
from test_release_disclosure_audit_08et import fixture


class TemporalQualityTests(unittest.TestCase):
    def test_small_quality_counter_delta_is_flagged(self):
        a = fixture(cells=(20,), closures=(0,))
        b = copy.deepcopy(a)
        a["quality"]["missing_agency"] = 20
        b["quality"]["missing_agency"] = 21
        result = gate.audit_pair(a, b)
        self.assertIn("SMALL_QUALITY_DELTA_EXPOSED", result["codes"])
        self.assertEqual(result["status"], "HOLD")

    def test_source_row_delta_with_stable_valid_cohort(self):
        a = fixture(cells=(20,), closures=(0,))
        b = copy.deepcopy(a)
        b["quality"]["rows_read"] += 1
        b["quality"]["unique_keys_verified"] += 1
        self.assertTrue(gate.audit_single(b)["structural_valid"])
        result = gate.audit_pair(a, b)
        self.assertIn("SMALL_SOURCE_ROW_DELTA_EXPOSED", result["codes"])
        self.assertNotIn("SMALL_COHORT_TOTAL_DELTA_EXPOSED", result["codes"])

    def test_quality_counter_set_changed(self):
        a = fixture(cells=(20,), closures=(0,))
        b = copy.deepcopy(a)
        b["quality"]["new_quality_dimension"] = 20
        result = gate.audit_pair(a, b)
        self.assertIn("QUALITY_COUNTER_SET_CHANGED", result["codes"])

    def test_large_difference_not_mislabeled_small(self):
        a = fixture(cells=(20,), closures=(0,))
        b = copy.deepcopy(a)
        a["quality"]["missing_agency"] = 20
        b["quality"]["missing_agency"] = 40
        result = gate.audit_pair(a, b)
        self.assertNotIn("SMALL_QUALITY_DELTA_EXPOSED", result["codes"])
        self.assertEqual(result["status"], "HOLD")

    def test_report_never_includes_private_quality_label(self):
        a = fixture(cells=(20,), closures=(0,))
        b = copy.deepcopy(a)
        a["quality"]["private_fictional_category"] = 20
        b["quality"]["private_fictional_category"] = 21
        report = json.dumps(gate.audit_pair(a, b))
        self.assertIn("SMALL_QUALITY_DELTA_EXPOSED", report)
        self.assertNotIn("private_fictional_category", report)
        self.assertNotIn("QUEENS", report)


if __name__ == "__main__":
    unittest.main()
