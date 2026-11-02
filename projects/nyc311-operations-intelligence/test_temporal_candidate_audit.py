"""Synthetic negative and positive controls for paired review candidates."""
import copy
import unittest
from temporal_candidate_audit import assess_pair


def candidate(day, *, requests=20, closed=0):
    return {
        "schema_version": "nyc311-review-candidate-v1", "dataset_id": "erm2-nwe9",
        "snapshot_as_of": day,
        "rules": {"grain": "month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count": 10},
        "aggregates": [{"month": "2026-09", "borough": "QUEENS", "agency": "DOT",
                        "problem": "Synthetic only", "requests": requests,
                        "closed_with_valid_interval": closed}],
    }


def codes(result):
    return {item["code"] for item in result["findings"]}


class TestTemporalCandidateAudit(unittest.TestCase):
    def setUp(self):
        self.old = candidate("2026-10-25")
        self.new = candidate("2026-10-26")

    def test_small_request_delta_detected_without_values(self):
        self.new["aggregates"][0]["requests"] = 21
        outcome = assess_pair(self.old, self.new)
        self.assertIn("small_visible_request_delta", codes(outcome))
        self.assertNotIn("21", str(outcome))
        self.assertNotIn("QUEENS", str(outcome))
        self.assertFalse(outcome["publication_cleared"])

    def test_small_closure_delta_detected(self):
        self.old["aggregates"][0]["requests"] = 30
        self.new["aggregates"][0]["requests"] = 30
        self.old["aggregates"][0]["closed_with_valid_interval"] = 10
        self.new["aggregates"][0]["closed_with_valid_interval"] = 11
        self.assertIn("small_visible_closure_delta", codes(assess_pair(self.old, self.new)))

    def test_suppression_state_change_detected(self):
        self.old["aggregates"][0]["closed_with_valid_interval"] = None
        self.assertIn("closure_suppression_state_changed", codes(assess_pair(self.old, self.new)))

    def test_disappearing_and_appearing_cells_flagged_not_treated_as_zero(self):
        self.new["aggregates"] = []
        self.assertIn("visible_cell_presence_changed", codes(assess_pair(self.old, self.new)))
        self.assertIn("visible_cell_presence_changed", codes(assess_pair(self.new, candidate("2026-10-27"))))

    def test_identical_values_still_hold(self):
        result = assess_pair(self.old, self.new)
        self.assertEqual(codes(result), {"external_marginal_and_provenance_review_pending"})
        self.assertFalse(result["publication_cleared"])

    def test_large_delta_does_not_mean_approval(self):
        self.new["aggregates"][0]["requests"] = 31
        self.assertNotIn("small_visible_request_delta", codes(assess_pair(self.old, self.new)))
        self.assertFalse(assess_pair(self.old, self.new)["publication_cleared"])

    def test_nonchronological_snapshots_rejected(self):
        for value in ("2026-10-25", "2026-10-24"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess_pair(self.old, candidate(value))

    def test_invalid_schema_and_threshold_rejected(self):
        for field, value in (("schema_version", "other"), ("dataset_id", "other")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                later = copy.deepcopy(self.new)
                later[field] = value
                assess_pair(self.old, later)
        for value in (True, 9, "10"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                later = copy.deepcopy(self.new)
                later["rules"]["display_minimum_cell_count"] = value
                assess_pair(self.old, later)

    def test_duplicate_or_extra_fields_rejected(self):
        for mutation in ("duplicate", "address", "quality"):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                later = copy.deepcopy(self.new)
                if mutation == "duplicate":
                    later["aggregates"].append(copy.deepcopy(later["aggregates"][0]))
                elif mutation == "address":
                    later["aggregates"][0]["incident_address"] = "synthetic"
                else:
                    later["quality"] = {"valid_records": 21}
                assess_pair(self.old, later)

    def test_invalid_dates_and_months_rejected(self):
        for date in ("20261026", "2026-02-30", "2026-W44-1"):
            with self.subTest(date=date), self.assertRaises(ValueError):
                later = copy.deepcopy(self.new)
                later["snapshot_as_of"] = date
                assess_pair(self.old, later)
        for month in ("202609", "2026-13", "2026-11"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                later = copy.deepcopy(self.new)
                later["aggregates"][0]["month"] = month
                assess_pair(self.old, later)

    def test_invalid_subgroup_and_counts_rejected(self):
        for n, c in ((True, 0), (9, 0), (20, True), (20, 1), (20, 11), (20, 21)):
            with self.subTest(n=n, c=c), self.assertRaises(ValueError):
                later = candidate("2026-10-26", requests=n, closed=c)
                assess_pair(self.old, later)

    def test_source_suppression_floor_controls_temporal_delta(self):
        # Both candidate snapshots use a stronger publication floor of 20.
        for item in (self.old, self.new):
            item["rules"]["display_minimum_cell_count"] = 20
            item["aggregates"][0]["requests"] = 50
            item["aggregates"][0]["closed_with_valid_interval"] = 20
        self.new["aggregates"][0]["requests"] = 61
        self.new["aggregates"][0]["closed_with_valid_interval"] = 31
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_request_delta", found)
        self.assertIn("small_visible_closure_delta", found)
        self.assertFalse(assess_pair(self.old, self.new)["publication_cleared"])

    def test_stronger_explicit_delta_floor_is_respected(self):
        self.new["aggregates"][0]["requests"] = 35
        self.assertNotIn("small_visible_request_delta", codes(assess_pair(self.old, self.new)))
        self.assertIn("small_visible_request_delta",
                      codes(assess_pair(self.old, self.new, delta_floor=20)))

    def test_small_open_complement_delta_detected_when_other_deltas_are_large(self):
        # Publicly visible open = requests - closed, so this 9-count change
        # is reconstructible even though requests and closed each change >=10.
        self.old["aggregates"][0].update(requests=100, closed_with_valid_interval=50)
        self.new["aggregates"][0].update(requests=120, closed_with_valid_interval=61)
        result = assess_pair(self.old, self.new)
        found = codes(result)
        self.assertIn("small_visible_open_complement_delta", found)
        self.assertNotIn("small_visible_request_delta", found)
        self.assertNotIn("small_visible_closure_delta", found)
        self.assertNotIn("QUEENS", str(result))
        self.assertNotIn("61", str(result))
        self.assertFalse(result["publication_cleared"])

    def test_source_floor_applies_to_open_complement_delta(self):
        for item in (self.old, self.new):
            item["rules"]["display_minimum_cell_count"] = 20
        self.old["aggregates"][0].update(requests=100, closed_with_valid_interval=40)
        self.new["aggregates"][0].update(requests=140, closed_with_valid_interval=61)
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_open_complement_delta", found)
        self.assertNotIn("small_visible_request_delta", found)
        self.assertNotIn("small_visible_closure_delta", found)

    def test_unchanged_open_complement_is_not_misclassified(self):
        self.old["aggregates"][0].update(requests=100, closed_with_valid_interval=50)
        self.new["aggregates"][0].update(requests=120, closed_with_valid_interval=70)
        self.assertNotIn("small_visible_open_complement_delta",
                         codes(assess_pair(self.old, self.new)))

    def test_inputs_not_modified(self):
        old, new = copy.deepcopy(self.old), copy.deepcopy(self.new)
        assess_pair(self.old, self.new)
        self.assertEqual(self.old, old)
        self.assertEqual(self.new, new)

    def test_invalid_floor_rejected(self):
        for value in (0, 1, 9, True, 1.5, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess_pair(self.old, self.new, delta_floor=value)


if __name__ == "__main__":
    unittest.main()
