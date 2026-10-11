"""Synthetic-only Scorecard batch completeness and missingness regressions."""
import unittest
from scorecard_batch_missingness_contract import normalize_scorecard_batch_preserving_missingness

def institution(unitid, size):
    return {'id': unitid, 'school.state': 'NY', 'school.ownership': 1,
            'school.locale': 11, '2024.student.size': size}

def ingest(pages):
    return normalize_scorecard_batch_preserving_missingness(
        pages=pages, enrollment_year=2024,
        field_years={'school.ownership': 2025, 'school.locale': 2023},
        release_date='2026-06-10', collection_period='Fall 2024',
        source_url='https://collegescorecard.ed.gov/data/')

class BatchMissingnessMultisourceTests(unittest.TestCase):
    def test_cross_page_suppressed_unknown_and_zero(self):
        pages = [
            {'metadata': {'page': 0, 'per_page': 2, 'total': 3},
             'results': [institution('000123', 0), institution('000124', 'PS')]},
            {'metadata': {'page': 1, 'per_page': 2, 'total': 3},
             'results': [institution('000125', 'NA')]},
        ]
        result = ingest(pages)
        enroll = [r for r in result['records'] if r['field'] == 'undergraduate_enrollment']
        self.assertEqual([r['source_data_status'] for r in enroll],
                         ['provided', 'privacy_suppressed', 'not_available_unspecified'])
        self.assertEqual([r['value'] for r in enroll], [0, None, None])
        self.assertEqual(result['institution_count'], 3)
        self.assertFalse(result['public_export_allowed'])
        self.assertIsNone(result['admissions_probability'])

    def test_missing_last_page_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest([{'metadata': {'page': 0, 'per_page': 2, 'total': 3},
                     'results': [institution('000123', 100), institution('000124', 200)]}])

    def test_cross_page_duplicate_unitid_is_rejected(self):
        with self.assertRaises(ValueError):
            ingest([
                {'metadata': {'page': 0, 'per_page': 1, 'total': 2},
                 'results': [institution('000123', 0)]},
                {'metadata': {'page': 1, 'per_page': 1, 'total': 2},
                 'results': [institution('000123', 'PS')]},
            ])

if __name__ == '__main__':
    unittest.main()
