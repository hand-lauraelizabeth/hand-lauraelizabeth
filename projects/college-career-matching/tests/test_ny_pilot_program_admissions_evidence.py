import unittest
from copy import deepcopy
from ny_pilot_program_admissions_evidence import (
    REVIEW_RECORDS, build_review_summary, validate_record,
)


class HunterAdmissionsStageEvidenceTests(unittest.TestCase):
    def test_t01_general_optional_generic_nex_required(self):
        s = build_review_summary(route="generic_bs")
        self.assertIn("optional", s["general_admissions"])
        self.assertIn("required", s["program_selection"])

    def test_t02_a2d_has_separate_nex_requirement(self):
        s = build_review_summary(route="accelerated_second_degree_bs")
        self.assertIn("required", s["program_selection"])
        self.assertIn("non-nursing", s["prior_qualification"])

    def test_t03_rn_completion_requires_existing_license(self):
        s = build_review_summary(route="rn_to_bs")
        self.assertIn("existing New York RN license", s["prior_qualification"])
        self.assertFalse(s["rn_license_guaranteed"])

    def test_t04_rn_to_bs_nex_not_inferred(self):
        self.assertIn("not been established",
                      build_review_summary(route="rn_to_bs")["program_selection"])

    def test_t05_nex_not_nclex(self):
        s = build_review_summary()
        self.assertIn("NEX is not the NCLEX-RN", s["licensure"])
        self.assertFalse(s["rn_license_guaranteed"])

    def test_t06_same_cip_does_not_collapse_distinct_routes(self):
        self.assertEqual({r["cip_code"] for r in REVIEW_RECORDS[1:]}, {"51.3801"})
        self.assertEqual(len({r["route"] for r in REVIEW_RECORDS[1:]}), 3)
        self.assertNotEqual(build_review_summary(route="generic_bs")["route"],
                            build_review_summary(route="rn_to_bs")["route"])

    def test_t07_general_admission_not_nursing_admission(self):
        s = build_review_summary()
        self.assertIn("Separate nursing-major application", s["prior_qualification"])
        self.assertFalse(s["nursing_admission_guaranteed"])

    def test_t08_a2d_not_freshman_path(self):
        self.assertIn("prior non-nursing bachelor's",
                      build_review_summary(route="accelerated_second_degree_bs")["prior_qualification"])

    def test_t09_missing_scorecard_scores_never_determine_policy(self):
        records = deepcopy(REVIEW_RECORDS)
        records[0]["requirement"] = "unknown"
        s = build_review_summary(records, scorecard_sat=None, scorecard_act=None)
        self.assertIn("not been established", s["general_admissions"])
        self.assertEqual(s["applicant_cycle"], "unverified")

    def test_t10_honors_preference_does_not_override_general_optional(self):
        s = build_review_summary()
        self.assertIn("optional", s["general_admissions"])
        self.assertIn("does not make general admission test-required", s["honors_score_preference"])

    def test_t11_institutional_licensure_statement_not_regulator_proof(self):
        s = build_review_summary()
        self.assertFalse(s["regulator_verified"])
        self.assertIn("independent regulator program-code verification is pending", s["licensure"])

    def test_t12_cycle_specific_deadline_not_inferred(self):
        s = build_review_summary()
        self.assertIsNone(s["program_deadline"])
        self.assertEqual(s["applicant_cycle"], "unverified")

    def test_t13_missing_source_fails_closed(self):
        records = deepcopy(REVIEW_RECORDS)
        records[1]["source"] = ""
        with self.assertRaises(ValueError):
            build_review_summary(records)

    def test_t14_wrong_stage_fails_closed(self):
        records = deepcopy(REVIEW_RECORDS)
        records[1]["stage"] = "institution_freshman"
        with self.assertRaises(ValueError):
            build_review_summary(records)

    def test_t15_selection_weights_not_propagated(self):
        records = deepcopy(REVIEW_RECORDS)
        records[3]["nex_weight"] = 0.5
        with self.assertRaises(ValueError):
            build_review_summary(records)

    def test_t16_no_mutation_of_source_records(self):
        records = deepcopy(REVIEW_RECORDS)
        original = deepcopy(records)
        build_review_summary(records)
        self.assertEqual(records, original)

    def test_t17_no_automatic_publication(self):
        self.assertFalse(build_review_summary()["publication_cleared"])

    def test_t18_duplicate_routes_rejected(self):
        with self.assertRaises(ValueError):
            build_review_summary(REVIEW_RECORDS + (REVIEW_RECORDS[1],))

    def test_t19_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            build_review_summary(route="unverified_route")

    def test_t20_date_required(self):
        record = deepcopy(REVIEW_RECORDS[0])
        record["verified_on"] = "yesterday"
        with self.assertRaises(ValueError):
            validate_record(record)


if __name__ == "__main__":
    unittest.main()
