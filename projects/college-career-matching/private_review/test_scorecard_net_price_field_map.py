import unittest
from scorecard_net_price_field_map import audit_net_price_field

DOC = 'https://collegescorecard.ed.gov/assets/InstitutionDataDocumentation.pdf'
MAP = 'https://collegescorecard.ed.gov/data/data-documentation/'

def row(**overrides):
    d = dict(unitid='900001', source_variable='NPT41_PUB', income_band='0_30k',
             institution_control='public', residency_scope='in_state',
             status='provided', value=10000, metric_year=2024,
             sfa_cohort_year=None, collection_period='2024-25',
             source_release_date='2026-06-10', dictionary_url=DOC,
             cohort_map_url=MAP, verified_cohort_map=False, review_reference=None)
    d.update(overrides)
    return d

class NetPriceFieldMapTests(unittest.TestCase):
    def test_unverified_cohort_never_ready(self):
        x = audit_net_price_field(row())
        self.assertFalse(x['comparison_ready'])
        self.assertEqual(x['publication_status'], 'DO_NOT_PUBLISH')
    def test_explicit_review_not_publication_approval(self):
        x = audit_net_price_field(row(sfa_cohort_year='2023-24', verified_cohort_map=True, review_reference='synthetic review'))
        self.assertTrue(x['review_evidence_complete'])
        self.assertFalse(x['comparison_ready'])
        self.assertFalse(x['independently_verified'])
        self.assertFalse(x['owner_approval'])
    def test_incorrect_income_band_rejected(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(source_variable='NPT43_PUB'))
    def test_public_residency_rejected_when_unknown(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(residency_scope='unknown'))
    def test_private_metric_scope(self):
        x = audit_net_price_field(row(source_variable='NPT41_PRIV', institution_control='private_nonprofit', residency_scope='not_applicable'))
        self.assertEqual(x['scope'], 'private')
    def test_control_metric_mismatch(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(source_variable='NPT41_PRIV'))
    def test_suppression_preserved(self):
        x = audit_net_price_field(row(status='privacy_suppressed', value=None))
        self.assertEqual(x['status'], 'privacy_suppressed')
        self.assertFalse(x['comparison_ready'])
    def test_suppressed_zero_rejected(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(status='privacy_suppressed', value=0))
    def test_zero_provided_valid(self):
        self.assertEqual(audit_net_price_field(row(value=0))['status'], 'provided')
    def test_release_year_not_cohort_year(self):
        self.assertIsNone(audit_net_price_field(row(source_release_date='2026-06-10'))['sfa_cohort_year'])
    def test_review_requires_reference(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(verified_cohort_map=True, sfa_cohort_year='2023-24'))
    def test_invalid_academic_year(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(collection_period='2024-26'))
    def test_bool_year_rejected(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(metric_year=True))
    def test_official_host_exact(self):
        with self.assertRaises(ValueError): audit_net_price_field(row(dictionary_url='https://collegescorecard.ed.gov.evil.example/'))
    def test_unknown_not_filled(self):
        x = audit_net_price_field(row(status='unknown', value=None, verified_cohort_map=True, sfa_cohort_year='2023-24', review_reference='synthetic review'))
        self.assertFalse(x['comparison_ready'])

if __name__ == '__main__': unittest.main()
