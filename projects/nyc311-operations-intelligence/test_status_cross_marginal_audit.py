"""Synthetic-only adversarial tests for the three-way 311 public-marginal gate."""
import unittest
from urllib.parse import urlencode
from status_cross_marginal_audit import audit, BASE, HOLD, SHAPES, _expected_where


def fixture():
    where = _expected_where("2026-09")
    def wrap(kind, rows):
        select, group, order = SHAPES[kind]
        return {"url": BASE + "?" + urlencode({
            "$select": select, "$where": where, "$group": group,
            "$order": order, "$limit": "50000"}), "rows": rows}
    three = wrap("three", [
        {"borough": "BRONX", "agency": "DOT", "status": "Open", "n": "5"},
        {"borough": "BRONX", "agency": "DOT", "status": "Closed", "n": "15"},
        {"borough": "QUEENS", "agency": "NYPD", "status": "Open", "n": "10"},
        {"borough": "QUEENS", "agency": "NYPD", "status": "Closed", "n": "20"}])
    two = wrap("two", [
        {"borough": "BRONX", "agency": "DOT", "n": "20"},
        {"borough": "QUEENS", "agency": "NYPD", "n": "30"}])
    status = wrap("status", [
        {"status": "Open", "n": "15"},
        {"status": "Closed", "n": "35"}])
    return three, two, status


class CrossMarginalTests(unittest.TestCase):
    def test_clean_arithmetic_still_hold(self):
        codes = audit(*fixture())
        self.assertTrue(HOLD.issubset(codes))
        self.assertIn("small_public_three_way_cells_present", codes)
        self.assertFalse(any("mismatch" in code for code in codes))

    def test_status_reassignment_balanced_within_pair_detected(self):
        three, two, status = fixture()
        three["rows"][0]["n"] = "6"
        three["rows"][1]["n"] = "14"
        codes = audit(three, two, status)
        self.assertIn("cross_dimension_status_mismatch", codes)
        self.assertNotIn("cross_dimension_borough_agency_mismatch", codes)

    def test_pair_reassignment_balanced_within_status_detected(self):
        three, two, status = fixture()
        three["rows"][0]["n"] = "6"
        three["rows"][2]["n"] = "9"
        codes = audit(three, two, status)
        self.assertIn("cross_dimension_borough_agency_mismatch", codes)
        self.assertNotIn("cross_dimension_status_mismatch", codes)

    def test_missing_three_way_row_detected(self):
        three, two, status = fixture()
        three["rows"].pop()
        codes = audit(three, two, status)
        self.assertIn("cross_dimension_citywide_total_mismatch", codes)

    def test_duplicate_cell_fails_closed(self):
        three, two, status = fixture()
        three["rows"].append(dict(three["rows"][0]))
        self.assertIn("cross_dimension_input_invalid", audit(three, two, status))

    def test_zero_and_boolean_count_fail_closed(self):
        for value in ("0", 1, True, "1.0", "-1", "01"):
            with self.subTest(value=value):
                three, two, status = fixture()
                three["rows"][0]["n"] = value
                self.assertIn("cross_dimension_input_invalid", audit(three, two, status))

    def test_extra_field_rejected(self):
        three, two, status = fixture()
        three["rows"][0]["unique_key"] = "do-not-accept"
        self.assertIn("cross_dimension_input_invalid", audit(three, two, status))

    def test_wrong_month_or_host_rejected(self):
        three, two, status = fixture()
        self.assertIn("cross_dimension_input_invalid",
                      audit(three, two, status, month="2026-10"))
        three["url"] = three["url"].replace("data.cityofnewyork.us", "example.org")
        self.assertIn("cross_dimension_input_invalid", audit(three, two, status))

    def test_wrong_aggregate_scope_rejected(self):
        three, two, status = fixture()
        three["url"] += "&%24offset=1"
        self.assertIn("cross_dimension_input_invalid", audit(three, two, status))

    def test_invalid_month_fails_closed(self):
        self.assertIn("cross_dimension_input_invalid",
                      audit(*fixture(), month="2026-13"))

    def test_empty_input_fails_closed(self):
        three, two, status = fixture()
        three["rows"] = []
        self.assertIn("cross_dimension_input_invalid", audit(three, two, status))


if __name__ == "__main__":
    unittest.main()
