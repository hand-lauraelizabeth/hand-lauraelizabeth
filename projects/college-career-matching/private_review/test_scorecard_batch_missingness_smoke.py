"""Synthetic regression: Scorecard source missingness remains private."""
import unittest
from scorecard_batch_missingness_contract import normalize_scorecard_batch_preserving_missingness

class BatchMissingnessSmoke(unittest.TestCase):
    def test_zero_and_privacy_suppression_are_distinct(self):
        rows = [
            {'id': '000123', 'school.state': 'NY', 'school.ownership': 1,
             'school.locale': 11, '2024.student.size': 0},
            {'id': '000124', 'school.state': 'NY', 'school.ownership': 1,
             'school.locale': 11, '2024.student.size': 'PS'},
        ]
        result = normalize_scorecard_batch_preserving_missingness(
            pages=[{'metadata': {'page': 0, 'per_page': 2, 'total': 2},
                    'results': rows}],
            enrollment_year=2024,
            field_years={'school.ownership': 2025, 'school.locale': 2023},
            release_date='2026-06-10', collection_period='Fall 2024',
            source_url='https://collegescorecard.ed.gov/data/')
        values = [r for r in result['records'] if r['field'] == 'undergraduate_enrollment']
        self.assertEqual([r['source_data_status'] for r in values],
                         ['provided', 'privacy_suppressed'])
        self.assertEqual([r['value'] for r in values], [0, None])
        self.assertFalse(result['public_export_allowed'])
        self.assertIsNone(result['admissions_probability'])

if __name__ == '__main__':
    unittest.main()
