import unittest
from nces_locale import LOCALE_LABELS, describe_locale

class LocaleTests(unittest.TestCase):
    def test_all_twelve_codes_preserve_granularity_and_privacy(self):
        self.assertEqual(len(LOCALE_LABELS), 12)
        for code, (category, detail) in LOCALE_LABELS.items():
            with self.subTest(code=code):
                record = describe_locale(code)
                self.assertEqual((record.category, record.detail), (category, detail))
                self.assertEqual(record.publication_status, "DO_NOT_PUBLISH")
                self.assertIsNone(record.observation_reporting_year)
                self.assertIsNone(record.observation_source_url)
                self.assertEqual(record.evidence_status, "PENDING_INSTITUTIONAL_VERIFICATION")

    def test_unknown_and_suppressed_codes_never_guess(self):
        for value in (None, -3, "-3", "PS", "14", "20", "", "0", "44", True, 11.0):
            with self.subTest(value=value):
                record = describe_locale(value)
                self.assertEqual(record.category, "Unknown")
                self.assertIsNone(record.detail)
                self.assertEqual(record.publication_status, "DO_NOT_PUBLISH")

    def test_integer_codes_from_ipeds_csv_are_accepted(self):
        self.assertEqual(describe_locale(11).detail, "City: Large")
        self.assertEqual(describe_locale(43).detail, "Rural: Remote")

    def test_whitespace_normalized_without_changing_code(self):
        self.assertEqual(describe_locale(" 43 ").detail, "Rural: Remote")

if __name__ == "__main__":
    unittest.main()
