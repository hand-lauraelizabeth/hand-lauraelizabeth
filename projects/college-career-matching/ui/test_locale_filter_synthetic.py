"""Synthetic-only NCES locale tests; no real institution data is loaded."""
import unittest
from locale_filter_synthetic import LOCALES, LocaleEvidence, classify_locale, matches_locale

def fixture(**overrides):
    fields = dict(unitid="123456", code=22, source_kind="NCES_IPEDS_UNITID",
                  source_url="https://nces.ed.gov/ipeds/", source_year=2025,
                  independently_verified=True)
    fields.update(overrides)
    return LocaleEvidence(**fields)

class LocaleFilterTests(unittest.TestCase):
    def test_all_twelve_codes(self):
        self.assertEqual(len(LOCALES), 12)
        for code, (group, subtype) in LOCALES.items():
            with self.subTest(code=code):
                x = classify_locale(fixture(code=code))
                self.assertEqual((x["group"], x["subtype"]), (group, subtype))
                self.assertEqual(x["verified_code"], code)
    def test_scorecard_candidate_is_not_verified(self):
        x = classify_locale(fixture(source_kind="SCORECARD_CANDIDATE"))
        self.assertEqual(x["status"], "UNVERIFIED")
        self.assertEqual(x["candidate_code"], 22)
        self.assertIsNone(x["group"])
    def test_default_unverified(self):
        self.assertEqual(classify_locale(LocaleEvidence("123456", 22))["status"], "UNVERIFIED")
    def test_missing_independent_review(self):
        self.assertIsNone(classify_locale(fixture(independently_verified=False))["verified_code"])
    def test_missing_source(self):
        self.assertIsNone(classify_locale(fixture(source_url=None))["verified_code"])
    def test_untrusted_source_scheme(self):
        self.assertIsNone(classify_locale(fixture(source_url="http://example.org"))["verified_code"])
    def test_missing_year(self):
        self.assertIsNone(classify_locale(fixture(source_year=None))["verified_code"])
    def test_invalid_unitid(self):
        self.assertIsNone(classify_locale(fixture(unitid="SYNTHETIC"))["verified_code"])
    def test_invalid_code(self):
        self.assertIsNone(classify_locale(fixture(code=99))["candidate_code"])
    def test_boolean_code_is_not_11(self):
        self.assertIsNone(classify_locale(fixture(code=True))["candidate_code"])
    def test_group_filter(self):
        self.assertTrue(matches_locale(fixture(), group="Suburb"))
        self.assertFalse(matches_locale(fixture(), group="Rural"))
    def test_subtype_filter(self):
        self.assertTrue(matches_locale(fixture(), group="Suburb", subtype="Midsize"))
        self.assertFalse(matches_locale(fixture(), group="Suburb", subtype="Large"))
    def test_unknown_excluded_by_default(self):
        self.assertFalse(matches_locale(fixture(independently_verified=False), group="Suburb"))
    def test_unknown_can_be_explicitly_included(self):
        self.assertTrue(matches_locale(fixture(independently_verified=False), group="Suburb", include_unknown=True))

if __name__ == "__main__":
    unittest.main()
