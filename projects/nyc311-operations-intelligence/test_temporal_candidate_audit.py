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

    def _add_second_visible_cell(self):
        for item in (self.old, self.new):
            second = copy.deepcopy(item["aggregates"][0])
            second["problem"] = "Synthetic second category"
            item["aggregates"].append(second)

    def test_small_common_cell_request_marginal_detected(self):
        self._add_second_visible_cell()
        self.old["aggregates"][0]["requests"] = 100
        self.old["aggregates"][1]["requests"] = 100
        self.new["aggregates"][0]["requests"] = 120
        self.new["aggregates"][1]["requests"] = 81
        result = assess_pair(self.old, self.new)
        found = codes(result)
        self.assertIn("small_visible_common_cell_request_marginal_delta", found)
        self.assertNotIn("small_visible_request_delta", found)
        self.assertNotIn("Synthetic second category", str(result))
        self.assertNotIn("81", str(result))
        self.assertFalse(result["publication_cleared"])

    def test_small_common_cell_closure_marginal_detected(self):
        self._add_second_visible_cell()
        for item in (self.old, self.new):
            for row in item["aggregates"]:
                row["requests"] = 100
        self.old["aggregates"][0]["closed_with_valid_interval"] = 30
        self.old["aggregates"][1]["closed_with_valid_interval"] = 40
        self.new["aggregates"][0]["closed_with_valid_interval"] = 50
        self.new["aggregates"][1]["closed_with_valid_interval"] = 21
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_common_cell_closure_marginal_delta", found)
        self.assertNotIn("small_visible_closure_delta", found)

    def test_small_common_cell_open_marginal_detected(self):
        self._add_second_visible_cell()
        self.old["aggregates"][0].update(requests=100, closed_with_valid_interval=30)
        self.old["aggregates"][1].update(requests=100, closed_with_valid_interval=60)
        self.new["aggregates"][0].update(requests=130, closed_with_valid_interval=40)
        self.new["aggregates"][1].update(requests=130, closed_with_valid_interval=109)
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_common_cell_open_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_request_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_closure_marginal_delta", found)
        self.assertNotIn("small_visible_open_complement_delta", found)

    def test_common_cell_marginal_negative_control(self):
        self._add_second_visible_cell()
        for row in self.old["aggregates"]:
            row["requests"] = 100
        for row in self.new["aggregates"]:
            row["requests"] = 120
        found = codes(assess_pair(self.old, self.new))
        self.assertFalse(any("common_cell" in code for code in found))

    def test_suppressed_closure_blocks_closure_marginal_inference(self):
        self._add_second_visible_cell()
        for item in (self.old, self.new):
            item["aggregates"][1]["closed_with_valid_interval"] = None
        self.old["aggregates"][0].update(requests=100, closed_with_valid_interval=30)
        self.new["aggregates"][0].update(requests=120, closed_with_valid_interval=50)
        found = codes(assess_pair(self.old, self.new))
        self.assertNotIn("small_visible_common_cell_closure_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_open_marginal_delta", found)

    def _three_visible_cells(self):
        for item in (self.old, self.new):
            first = item["aggregates"][0]
            first["problem"] = "Synthetic A"
            second = copy.deepcopy(first)
            second["problem"] = "Synthetic B"
            third = copy.deepcopy(first)
            third["borough"] = "BRONX"
            third["problem"] = "Synthetic C"
            item["aggregates"] = [first, second, third]

    def test_borough_request_marginal_hidden_by_third_category(self):
        self._three_visible_cells()
        for row in self.old["aggregates"]:
            row["requests"] = 100
        for row, n in zip(self.new["aggregates"], (120, 81, 130)):
            row["requests"] = n
        result = assess_pair(self.old, self.new)
        found = codes(result)
        self.assertIn("small_visible_dimension_request_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_request_marginal_delta", found)
        self.assertNotIn("Synthetic A", str(result))
        self.assertNotIn("BRONX", str(result))
        self.assertFalse(result["publication_cleared"])

    def test_borough_closure_marginal_hidden_by_third_category(self):
        self._three_visible_cells()
        for row, n in zip(self.old["aggregates"], (30, 40, 50)):
            row.update(requests=100, closed_with_valid_interval=n)
        for row, n in zip(self.new["aggregates"], (50, 21, 70)):
            row.update(requests=100, closed_with_valid_interval=n)
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_dimension_closure_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_closure_marginal_delta", found)

    def test_borough_open_marginal_hidden_by_third_category(self):
        self._three_visible_cells()
        for row, n in zip(self.old["aggregates"], (30, 60, 40)):
            row.update(requests=100, closed_with_valid_interval=n)
        for row, n in zip(self.new["aggregates"], (40, 109, 50)):
            row.update(requests=130, closed_with_valid_interval=n)
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_dimension_open_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_open_marginal_delta", found)
        self.assertNotIn("small_visible_open_complement_delta", found)

    def test_visible_closure_subset_with_other_suppressed_row(self):
        self._three_visible_cells()
        for item in (self.old, self.new):
            item["aggregates"][2]["borough"] = "QUEENS"
            item["aggregates"][2]["closed_with_valid_interval"] = None
            for row in item["aggregates"]:
                row["requests"] = 100
        for row, n in zip(self.old["aggregates"][:2], (30, 40)):
            row["closed_with_valid_interval"] = n
        for row, n in zip(self.new["aggregates"][:2], (50, 21)):
            row["closed_with_valid_interval"] = n
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_dimension_closure_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_closure_marginal_delta", found)

    def test_large_dimension_deltas_are_not_misclassified(self):
        self._three_visible_cells()
        for row in self.old["aggregates"]:
            row["requests"] = 100
        for row in self.new["aggregates"]:
            row["requests"] = 120
        found = codes(assess_pair(self.old, self.new))
        self.assertFalse(any("dimension" in code for code in found))

    def _four_joint_cells(self):
        for item in (self.old, self.new):
            first = item["aggregates"][0]
            first["problem"] = "Synthetic A"
            second = copy.deepcopy(first)
            second["problem"] = "Synthetic B"
            third = copy.deepcopy(first)
            third["agency"] = "NYPD"
            third["problem"] = "Synthetic C"
            fourth = copy.deepcopy(first)
            fourth["borough"] = "BRONX"
            fourth["problem"] = "Synthetic D"
            item["aggregates"] = [first, second, third, fourth]

    def test_joint_borough_agency_request_marginal_masked_by_single_axes(self):
        self._four_joint_cells()
        for row in self.old["aggregates"]:
            row["requests"] = 100
        for row, count in zip(self.new["aggregates"], (120, 81, 120, 120)):
            row["requests"] = count
        outcome = assess_pair(self.old, self.new)
        found = codes(outcome)
        self.assertIn("small_visible_joint_dimension_request_marginal_delta", found)
        self.assertNotIn("small_visible_dimension_request_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_request_marginal_delta", found)
        self.assertNotIn("Synthetic A", str(outcome))
        self.assertNotIn("QUEENS", str(outcome))
        self.assertFalse(outcome["publication_cleared"])

    def test_joint_borough_agency_closure_marginal_masked_by_single_axes(self):
        self._four_joint_cells()
        for item in (self.old, self.new):
            for row in item["aggregates"]:
                row["requests"] = 100
        for row in self.old["aggregates"]:
            row["closed_with_valid_interval"] = 30
        for row, count in zip(self.new["aggregates"], (50, 11, 50, 50)):
            row["closed_with_valid_interval"] = count
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_joint_dimension_closure_marginal_delta", found)
        self.assertNotIn("small_visible_dimension_closure_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_closure_marginal_delta", found)

    def test_joint_borough_agency_open_marginal_masked_by_single_axes(self):
        self._four_joint_cells()
        for row, closed in zip(self.old["aggregates"], (30, 60, 40, 50)):
            row.update(requests=100, closed_with_valid_interval=closed)
        for row, closed in zip(self.new["aggregates"], (40, 109, 50, 60)):
            row.update(requests=130, closed_with_valid_interval=closed)
        found = codes(assess_pair(self.old, self.new))
        self.assertIn("small_visible_joint_dimension_open_marginal_delta", found)
        self.assertNotIn("small_visible_dimension_open_marginal_delta", found)
        self.assertNotIn("small_visible_common_cell_open_marginal_delta", found)

    def test_large_joint_deltas_are_not_misclassified(self):
        self._four_joint_cells()
        for row in self.old["aggregates"]:
            row["requests"] = 100
        for row in self.new["aggregates"]:
            row["requests"] = 120
        found = codes(assess_pair(self.old, self.new))
        self.assertFalse(any("joint_dimension" in code for code in found))

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
