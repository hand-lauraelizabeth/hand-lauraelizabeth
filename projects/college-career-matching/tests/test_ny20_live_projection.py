"""Tests for evidence-limited institution projection integrated into the existing matcher page."""
from pathlib import Path
import json, unittest
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'ny20-institution-evidence.v1.json'

class LiveInstitutionReferenceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text(encoding='utf-8'))
        cls.items=cls.data['institutions']
    def test_exact_roster(self):
        self.assertEqual(len(self.items),20)
        self.assertEqual(len(set(x['unitid'] for x in self.items)),20)
    def test_descriptive_not_predictive(self):
        d=self.data
        self.assertEqual(d['projection_kind'],'institution_reference')
        self.assertEqual(d['data_publication_scope'],'DESCRIPTIVE_INSTITUTION_REFERENCE_ONLY')
        for field in ['scoring_authorized','admission_predictions_authorized','program_ranking_authorized']:
            self.assertIs(d[field],False)
    def test_exhaustive_programs_not_asserted(self):
        for x in self.items:
            self.assertIsNone(x['programs'])
            self.assertIsNone(x['transfer_rules'])
            self.assertIs(x['score_authorized'],False)
    def test_provenance_and_reporting_vintage(self):
        for x in self.items:
            for field in ('size','tuition_in','net_price'):
                v=x[field]
                self.assertIn(v['status'],('source_reconciled_year_not_verified','source_missing'))
                self.assertIsNone(v['reference_year'])
                self.assertEqual(v['source_release'],'2026-06-10')
    def test_missing_and_zero_not_conflated(self):
        self.assertTrue(any(x['admissions']['hs_admitted_mean'] is None for x in self.items))
        self.assertTrue(any(x['admissions']['historical_admit_rate']['value'] is None for x in self.items))
    def test_housing_vacancies_unverified(self):
        for x in self.items:
            self.assertIs(x['housing']['vacancy_verified'],False)
            self.assertIs(x['housing']['accessible_vacancy_verified'],False)
    def test_admissions_scale_and_no_probability(self):
        for x in self.items:
            self.assertIsNone(x['admissions']['probability'])
            hs=x['admissions']['hs_admitted_mean'];gpa=x['admissions']['transfer_mean']
            if hs:self.assertEqual(hs['scale'],'hs_percent_100')
            if gpa:self.assertEqual(gpa['scale'],'college_gpa_4')
    def test_locale_not_footprinted_as_independently_verified(self):
        for x in self.items:self.assertIs(x['location']['locale_independently_verified'],False)

if __name__=='__main__':unittest.main()