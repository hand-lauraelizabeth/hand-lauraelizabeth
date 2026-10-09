"""Regression tests for private applicant-input and size-matching contract."""
import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "applicant_input_contract.py"
spec = importlib.util.spec_from_file_location("applicant_input_contract", FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ApplicantInputTests(unittest.TestCase):
    def test_unweighted_four_point(self):
        self.assertEqual(m.validate_gpa(3.7, scale="4.0", weighting="unweighted")["maximum"], 4.0)

    def test_weighted_requires_maximum(self):
        with self.assertRaises(ValueError):
            m.validate_gpa(4.3, scale="4.0", weighting="weighted")

    def test_weighted_above_four_with_declared_max(self):
        self.assertEqual(m.validate_gpa(4.3, scale="4.0", weighting="weighted", maximum=5.0)["value"], 4.3)

    def test_other_scale_requires_maximum(self):
        with self.assertRaises(ValueError):
            m.validate_gpa(88, scale="other", weighting="unweighted")

    def test_other_scale_with_maximum(self):
        self.assertEqual(m.validate_gpa(88, scale="other", weighting="unweighted", maximum=100)["scale"], "other")

    def test_gpa_out_of_range(self):
        for value in (-0.1, 4.1):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validate_gpa(value, scale="4.0", weighting="unweighted")

    def test_gpa_missing_unknown_and_na(self):
        for state in m.MISSING_STATES:
            self.assertEqual(m.validate_gpa(status=state)["status"], state)
        with self.assertRaises(ValueError):
            m.validate_gpa(3.5, status="missing")

    def test_sat_valid_total_and_sections(self):
        self.assertEqual(m.validate_sat(reading_writing=650, math=700)["total"], 1350)
        self.assertEqual(m.validate_sat(1350, reading_writing=650, math=700)["total"], 1350)

    def test_sat_invalid_total_and_sections(self):
        for args in ({"total": 390}, {"total": 1610}, {"reading_writing": 850},
                     {"total": 1300, "reading_writing": 650, "math": 700},
                     {"reading_writing": 655}, {"total": True}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.validate_sat(**args)

    def test_sat_omission(self):
        self.assertEqual(m.validate_sat(status="unknown")["status"], "unknown")
        with self.assertRaises(ValueError):
            m.validate_sat()
        with self.assertRaises(ValueError):
            m.validate_sat(1100, status="missing")

    def test_act_composite_and_sections(self):
        self.assertEqual(m.validate_act(29, english=30, math=28)["composite"], 29)
        self.assertEqual(m.validate_act(reading=25)["sections"]["reading"], 25)

    def test_act_invalid_scores(self):
        for args in ({"composite": 0}, {"composite": 37}, {"science": 37},
                     {"math": 27.5}, {"english": True}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                m.validate_act(**args)

    def test_act_omission(self):
        self.assertEqual(m.validate_act(status="missing")["status"], "missing")
        with self.assertRaises(ValueError):
            m.validate_act()
        with self.assertRaises(ValueError):
            m.validate_act(29, status="not_applicable")

    def test_reject_forged_sat_total(self):
        with self.assertRaises(ValueError):
            m.testing_evidence("blind", {"test": "SAT", "status": "provided", "total": 1700, "sections": {}})

    def test_reject_forged_act_composite(self):
        with self.assertRaises(ValueError):
            m.testing_evidence("optional", {"test": "ACT", "status": "provided", "composite": 40, "sections": {}})

    def test_test_blind_never_uses_scores(self):
        x = m.testing_evidence("blind", m.validate_sat(1500))
        self.assertFalse(x["consider_scores"])
        self.assertIsNone(x["admission_probability"])

    def test_test_optional_can_omit_scores(self):
        x = m.testing_evidence("optional", m.validate_sat(status="missing"))
        self.assertEqual(x["evidence"], "scores_omitted_allowed")
        self.assertFalse(x["consider_scores"])

    def test_test_required_omitted_not_a_cutoff(self):
        x = m.testing_evidence("required", None)
        self.assertEqual(x["evidence"], "required_scores_unavailable")
        self.assertIsNone(x["admission_probability"])

    def test_unknown_policy_does_not_use_scores(self):
        self.assertFalse(m.testing_evidence("unknown", m.validate_act(34))["consider_scores"])

    def test_undergraduate_total_distinct(self):
        undergraduate = m.validate_enrollment(4999, definition="undergraduate")
        total = m.validate_enrollment(6500, definition="total")
        self.assertIsNone(m.enrollment_preference(total, definition="undergraduate", minimum=4000)["match"])
        self.assertTrue(m.enrollment_preference(undergraduate, definition="undergraduate", minimum=4000, maximum=4999)["match"])

    def test_size_range_inclusive(self):
        record = m.validate_enrollment(5000, definition="undergraduate")
        self.assertTrue(m.enrollment_preference(record, definition="undergraduate", minimum=5000, maximum=5000)["match"])
        self.assertFalse(m.enrollment_preference(record, definition="undergraduate", maximum=4999)["match"])

    def test_size_preference_and_filter(self):
        record = m.validate_enrollment(10000, definition="total")
        for mode in ("filter", "preference"):
            self.assertEqual(m.enrollment_preference(record, definition="total", minimum=8000, mode=mode)["mode"], mode)

    def test_missing_enrollment_not_zero(self):
        for state in m.MISSING_STATES:
            record = m.validate_enrollment(definition="total", status=state)
            self.assertIsNone(m.enrollment_preference(record, definition="total", maximum=500)["match"])

    def test_invalid_enrollment_and_range(self):
        for value in (-1, 4.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validate_enrollment(value, definition="undergraduate")
        record = m.validate_enrollment(100, definition="total")
        with self.assertRaises(ValueError):
            m.enrollment_preference(record, definition="total", minimum=200, maximum=100)

    def test_institution_testing_policy_requires_cohort(self):
        with self.assertRaises(ValueError):
            m.validate_institution_testing_policy("optional", unitid="123456", source_url="https://example.edu", reporting_year=2025)

    def test_unreviewed_school_policy_does_not_use_scores(self):
        policy = m.validate_institution_testing_policy("required", unitid="123456", source_url="https://example.edu", reporting_year=2025, admissions_cohort="Fall 2025")
        result = m.testing_evidence_with_provenance(policy, m.validate_sat(1500))
        self.assertFalse(result["consider_scores"])
        self.assertEqual(result["confidence"], "policy_unverified")

    def test_reviewed_test_blind_ignores_scores(self):
        policy = m.validate_institution_testing_policy("blind", unitid="123456", source_url="https://example.edu", reporting_year=2025, admissions_cohort="Fall 2025", independently_reviewed=True)
        result = m.testing_evidence_with_provenance(policy, m.validate_act(36))
        self.assertFalse(result["consider_scores"])
        self.assertIsNone(result["admission_probability"])

    def test_institution_enrollment_requires_independent_review_for_match(self):
        record = m.validate_institution_enrollment(5000, definition="undergraduate", unitid="123456", source_url="https://nces.ed.gov", reporting_year=2024)
        self.assertIsNone(m.enrollment_evidence_preference(record, definition="undergraduate", minimum=1000, maximum=9000)["match"])
        reviewed = m.validate_institution_enrollment(5000, definition="undergraduate", unitid="123456", source_url="https://nces.ed.gov", reporting_year=2024, independently_reviewed=True)
        self.assertTrue(m.enrollment_evidence_preference(reviewed, definition="undergraduate", minimum=5000, maximum=5000)["match"])
        self.assertIsNone(m.enrollment_evidence_preference(reviewed, definition="total", minimum=5000)["match"])

    def test_institution_unknown_enrollment_is_not_zero(self):
        for state in m.MISSING_STATES:
            record = m.validate_institution_enrollment(definition="total", unitid="123456", status=state)
            self.assertIsNone(m.enrollment_evidence_preference(record, definition="total", maximum=500)["match"])

    def test_reviewed_optional_policy_allows_omission(self):
        policy = m.validate_institution_testing_policy("optional", unitid="123456", source_url="https://example.edu", reporting_year=2025, admissions_cohort="Fall 2025", independently_reviewed=True)
        result = m.testing_evidence_with_provenance(policy, m.validate_sat(status="missing"))
        self.assertEqual(result["evidence"], "scores_omitted_allowed")
        self.assertEqual(result["policy_reporting_year"], 2025)
        self.assertEqual(policy["publication_status"], "DO_NOT_PUBLISH")


if __name__ == "__main__":
    unittest.main()
