"""Boundary checks for descriptive applicant test evidence."""
import importlib.util
import unittest
from pathlib import Path

file = Path(__file__).resolve().parents[1] / "applicant_input_contract.py"
spec = importlib.util.spec_from_file_location("applicant_input_contract", file)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ScoreBoundaryTests(unittest.TestCase):
    def test_forged_sat_total_rejected(self):
        for policy in m.TEST_POLICIES:
            with self.assertRaises(ValueError):
                m.testing_evidence(policy, {"test":"SAT","status":"provided","total":1700,"sections":{}})

    def test_forged_act_composite_rejected(self):
        for policy in m.TEST_POLICIES:
            with self.assertRaises(ValueError):
                m.testing_evidence(policy, {"test":"ACT","status":"provided","composite":40,"sections":{}})

    def test_omitted_and_valid_scores(self):
        self.assertFalse(m.testing_evidence("optional", m.validate_sat(status="missing"))["consider_scores"])
        self.assertTrue(m.testing_evidence("optional", m.validate_act(30))["consider_scores"])
        self.assertFalse(m.testing_evidence("blind", m.validate_sat(1500))["consider_scores"])

if __name__ == "__main__":
    unittest.main()
