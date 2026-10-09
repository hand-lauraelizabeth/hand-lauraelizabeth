import unittest
from admissions_profile import validate_profile, school_size_match, testing_context

class AdmissionsProfileTests(unittest.TestCase):
    def test_optional_inputs(self):
        self.assertEqual(validate_profile({}), [])
    def test_gpa_scale(self):
        self.assertEqual(validate_profile({"gpa":3.8,"gpa_scale":"4.0","gpa_weighting":"unweighted"}), [])
        self.assertTrue(validate_profile({"gpa":4.7,"gpa_scale":"4.0"}))
        self.assertTrue(validate_profile({"gpa":3.9}))
    def test_sat_act_boundaries(self):
        self.assertEqual(validate_profile({"sat_total":400,"act_composite":36}), [])
        self.assertTrue(validate_profile({"sat_total":401}))
        self.assertTrue(validate_profile({"act_composite":37}))
    def test_size_and_unknown(self):
        p={"min_undergrad_enrollment":1000,"max_undergrad_enrollment":5000}
        self.assertIsNone(school_size_match(p,{}))
        self.assertTrue(school_size_match(p,{"undergraduate_enrollment":3000}))
        self.assertFalse(school_size_match(p,{"undergraduate_enrollment":9000}))
        self.assertTrue(validate_profile({"min_undergrad_enrollment":5000,"max_undergrad_enrollment":1000}))
    def test_testing_policies(self):
        self.assertEqual(testing_context({"sat_total":1500},{"test_policy":"test_blind"}),"SCORES_NOT_CONSIDERED")
        self.assertEqual(testing_context({},{"test_policy":"test_optional"}),"OPTIONAL_SCORES_OMITTED")
        self.assertEqual(testing_context({},{}),"POLICY_UNKNOWN")
        self.assertEqual(testing_context({"act_composite":28},{"test_policy":"test_required"}),"SCORES_PROVIDED_NO_ODDS_ESTIMATE")

if __name__=="__main__":
    unittest.main()
