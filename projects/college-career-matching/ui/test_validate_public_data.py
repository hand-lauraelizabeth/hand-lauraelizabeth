"""Regression tests for structural bundle validation (stdlib only).

Run: python -m unittest discover -s projects/college-career-matching/ui -p 'test_*.py'
"""
import copy
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("validator", Path(__file__).with_name("validate-public-data.py"))
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

GOOD = {"schema_version": 1, "records": [{
    "name": "Example Institution", "setting": "Urban", "housing": True,
    "access": None, "cost": {"low": 0, "mid": None, "high": 12000},
    "careers": {"data": None, "education": 0, "health": 2, "business": 3},
    "aid": [], "source": "Official dataset, verified separately", "reference_year": 2025,
}]}

class BundleTests(unittest.TestCase):
    def test_valid_nullable_and_zero_cost(self):
        self.assertEqual(validator.validate(copy.deepcopy(GOOD)), [])

    def test_non_object_bundle(self):
        for payload in (None, [], "string", 4):
            with self.subTest(payload=payload):
                self.assertTrue(validator.validate(payload))

    def test_duplicate_names_case_insensitive(self):
        payload = copy.deepcopy(GOOD)
        second = copy.deepcopy(payload["records"][0])
        second["name"] = " example institution "
        payload["records"].append(second)
        self.assertTrue(any("duplicate" in e for e in validator.validate(payload)))

    def test_missing_cost_key(self):
        payload = copy.deepcopy(GOOD)
        del payload["records"][0]["cost"]["mid"]
        self.assertTrue(validator.validate(payload))

    def test_boolean_cost_rejected(self):
        payload = copy.deepcopy(GOOD)
        payload["records"][0]["cost"]["low"] = True
        self.assertTrue(validator.validate(payload))

    def test_missing_career_key(self):
        payload = copy.deepcopy(GOOD)
        del payload["records"][0]["careers"]["data"]
        self.assertTrue(validator.validate(payload))

    def test_invalid_access_rejected(self):
        payload = copy.deepcopy(GOOD)
        payload["records"][0]["access"] = 4
        self.assertTrue(validator.validate(payload))

    def test_invalid_setting_type(self):
        payload = copy.deepcopy(GOOD)
        payload["records"][0]["setting"] = []
        self.assertTrue(validator.validate(payload))

    def test_bool_schema_version_rejected(self):
        payload = copy.deepcopy(GOOD)
        payload["schema_version"] = True
        self.assertTrue(validator.validate(payload))

if __name__ == "__main__":
    unittest.main()
