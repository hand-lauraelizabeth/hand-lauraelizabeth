"""Synthetic regression cases for accessibility evidence and release gate."""
import unittest
from accessibility_filter_synthetic import (
    AccessibilityEvidence, FeatureState, FEATURES, classify_feature, matches_feature, public_filter
)

def fixture(**kwargs):
    data = dict(unitid="123456", feature="building_access",
                state=FeatureState.OBSERVED_YES,
                source_url="https://example.edu/access", reviewed_at="2026-10-08",
                independently_verified=True)
    data.update(kwargs)
    return AccessibilityEvidence(**data)

class AccessibilityFilterTests(unittest.TestCase):
    def test_each_feature_supported(self):
        for feature in FEATURES:
            with self.subTest(feature=feature):
                self.assertTrue(classify_feature(fixture(feature=feature))["supported_yes"])
    def test_documented_no_not_unknown(self):
        x = classify_feature(fixture(state=FeatureState.OBSERVED_NO))
        self.assertTrue(x["supported_no"])
        self.assertFalse(matches_feature(fixture(state=FeatureState.OBSERVED_NO), "building_access", True))
    def test_missing_source_is_unknown(self):
        x = classify_feature(fixture(source_url=None))
        self.assertEqual(x["state"], "UNKNOWN")
        self.assertFalse(x["supported_no"])
    def test_unverified_negative_is_unknown(self):
        x = classify_feature(fixture(state=FeatureState.OBSERVED_NO, independently_verified=False))
        self.assertEqual(x["state"], "UNKNOWN")
    def test_unknown_optional(self):
        x = fixture(state=FeatureState.UNKNOWN)
        self.assertFalse(matches_feature(x, "building_access"))
        self.assertTrue(matches_feature(x, "building_access", True))
    def test_wrong_feature_does_not_match(self):
        self.assertFalse(matches_feature(fixture(), "accessible_housing_process", True))
    def test_not_published_is_not_yes(self):
        self.assertFalse(matches_feature(fixture(state=FeatureState.NOT_PUBLISHED), "building_access"))
    def test_no_public_release_by_default(self):
        self.assertEqual(public_filter([fixture()]), [])
    def test_owner_and_allowlist_required(self):
        r = fixture(publication_status="APPROVED", owner_approved=True)
        self.assertEqual(public_filter([r]), [])
        self.assertEqual(public_filter([r], {"123456"}), [r])
        self.assertEqual(public_filter([fixture(publication_status="APPROVED")], {"123456"}), [])
    def test_unverified_not_released(self):
        r = fixture(publication_status="APPROVED", owner_approved=True, independently_verified=False)
        self.assertEqual(public_filter([r], {"123456"}), [])

if __name__ == "__main__":
    unittest.main()
