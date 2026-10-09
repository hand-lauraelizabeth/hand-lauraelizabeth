"""Private enrollment consistency regressions; no publication authorization."""
import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / "applicant_input_contract.py"
spec = importlib.util.spec_from_file_location("applicant_input_contract", FILE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def count(value=5000, definition="undergraduate", reviewed=True):
    return m.validate_institution_enrollment(
        value, definition=definition, unitid="123456",
        source_url="https://nces.ed.gov", reporting_year=2025,
        independently_reviewed=reviewed)


class EnrollmentIntegrityTests(unittest.TestCase):
    def test_modified_numeric_value_is_structurally_valid_not_authenticated(self):
        original = count()
        changed = {**original, "value": 6000}
        self.assertEqual(m.validate_institution_enrollment_record(changed), changed)

    def test_modified_review_flag_rejected_when_non_boolean(self):
        with self.assertRaises(ValueError):
            m.validate_institution_enrollment_record({**count(), "independently_reviewed": "true"})

    def test_publication_status_cannot_be_changed(self):
        with self.assertRaises(ValueError):
            m.enrollment_evidence_preference(
                {**count(), "publication_status": "PUBLISH"},
                definition="undergraduate", minimum=1000)

    def test_missing_count_cannot_claim_reviewed(self):
        with self.assertRaises(ValueError):
            m.validate_institution_enrollment(
                definition="undergraduate", unitid="123456",
                status="unknown", independently_reviewed=True)

    def test_unreviewed_count_is_not_a_filter_failure(self):
        result = m.enrollment_evidence_preference(
            count(reviewed=False), definition="undergraduate",
            minimum=9000, mode="filter")
        self.assertIsNone(result["match"])
        self.assertEqual(result["reason"], "enrollment_source_unverified")

    def test_enrollment_vintage_is_not_release_date(self):
        with self.assertRaises(ValueError):
            m.validate_institution_enrollment(
                1000, definition="total", unitid="123456",
                source_url="https://nces.ed.gov", reporting_year=None)

    def test_total_count_does_not_satisfy_undergraduate_filter(self):
        result = m.enrollment_evidence_preference(
            count(definition="total"), definition="undergraduate",
            minimum=1)
        self.assertIsNone(result["match"])


if __name__ == "__main__":
    unittest.main()
