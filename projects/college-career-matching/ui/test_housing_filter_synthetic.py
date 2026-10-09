"""Regression tests for synthetic housing evidence. Run: python -m unittest discover -s projects/college-career-matching/ui -p 'test_housing_filter_synthetic.py'"""
import unittest
from housing_filter_synthetic import HousingEvidence, HousingType, Availability, classify_housing, public_filter

def evidence(**overrides):
    base = dict(housing_type=HousingType.ON_CAMPUS, availability=Availability.CONFIRMED_FOR_TERM,
                availability_term="2027-FALL", source_url="https://example.edu/housing",
                unitid="SYNTHETIC-001", verified=True, publication_status="DO_NOT_PUBLISH",
                owner_approved=False)
    base.update(overrides)
    return HousingEvidence(**base)

class HousingFilterTests(unittest.TestCase):
    def test_default_denies_publication(self):
        self.assertEqual(public_filter([evidence()]), [])
    def test_approval_requires_owner(self):
        self.assertEqual(public_filter([evidence(publication_status="APPROVED")]), [])
    def test_approval_requires_verified(self):
        self.assertEqual(public_filter([evidence(publication_status="APPROVED", owner_approved=True, verified=False)]), [])
    def test_approval_requires_source(self):
        self.assertEqual(public_filter([evidence(publication_status="APPROVED", owner_approved=True, source_url=None)]), [])
    def test_approval_requires_unitid(self):
        self.assertEqual(public_filter([evidence(publication_status="APPROVED", owner_approved=True, unitid=None)]), [])
    def test_approved_record_is_eligible_in_isolated_fixture(self):
        e = evidence(publication_status="APPROVED", owner_approved=True)
        self.assertEqual(public_filter([e]), [])
        self.assertEqual(public_filter([e], approved_unitids={"SYNTHETIC-001"}), [e])
    def test_allowlist_without_record_approval_denied(self):
        self.assertEqual(public_filter([evidence()], approved_unitids={"SYNTHETIC-001"}), [])
    def test_other_unitid_denied(self):
        e = evidence(publication_status="APPROVED", owner_approved=True)
        self.assertEqual(public_filter([e], approved_unitids={"SYNTHETIC-002"}), [])
    def test_unverified_housing_is_unknown(self):
        d = classify_housing(evidence(verified=False))
        self.assertTrue(d["unknown_housing"])
        self.assertFalse(d["on_campus"])
    def test_missing_provenance_is_unknown(self):
        d = classify_housing(evidence(source_url=None))
        self.assertTrue(d["unknown_housing"])
        self.assertFalse(d["confirmed_vacancy"])
    def test_unverified_negative_not_documented(self):
        d = classify_housing(evidence(housing_type=HousingType.DOCUMENTED_NONE, verified=False))
        self.assertFalse(d["documented_none"])
        self.assertTrue(d["unknown_housing"])
    def test_matching_term_confirmed(self):
        self.assertTrue(classify_housing(evidence(), "2027-FALL")["confirmed_vacancy"])
    def test_mismatched_term_not_confirmed(self):
        self.assertFalse(classify_housing(evidence(), "2028-SPRING")["confirmed_vacancy"])
    def test_missing_term_not_confirmed(self):
        self.assertFalse(classify_housing(evidence(), None)["confirmed_vacancy"])
    def test_unverified_vacancy_not_confirmed(self):
        self.assertFalse(classify_housing(evidence(verified=False), "2027-FALL")["confirmed_vacancy"])
    def test_waitlist_not_confirmed(self):
        self.assertFalse(classify_housing(evidence(availability=Availability.WAITLIST), "2027-FALL")["confirmed_vacancy"])
    def test_affiliated_not_on_campus(self):
        self.assertFalse(classify_housing(evidence(housing_type=HousingType.AFFILIATED_OFF_CAMPUS), "2027-FALL")["on_campus"])
    def test_referral_not_on_campus(self):
        self.assertFalse(classify_housing(evidence(housing_type=HousingType.REFERRAL_ONLY), "2027-FALL")["on_campus"])
    def test_unknown_not_documented_none(self):
        d = classify_housing(evidence(housing_type=HousingType.UNKNOWN))
        self.assertTrue(d["unknown_housing"])
        self.assertFalse(d["documented_none"])
    def test_documented_none_not_unknown(self):
        d = classify_housing(evidence(housing_type=HousingType.DOCUMENTED_NONE))
        self.assertTrue(d["documented_none"])
        self.assertFalse(d["unknown_housing"])

if __name__ == "__main__":
    unittest.main()
