"""Synthetic regression: pipeline's boolean provenance field is valid, not an integer counter."""
import copy
import unittest
from release_disclosure_audit import audit_single, audit_pair


def fixture():
    return {
        'source': 'https://data.cityofnewyork.us/d/erm2-nwe9',
        'dataset_id': 'erm2-nwe9',
        'source_sha256': 'a' * 64,
        'source_bytes': 128,
        'snapshot_as_of': '2026-09-30',
        'rules': {'display_minimum_cell_count': 10},
        'quality': {'rows_read': 12, 'valid_records': 12,
                    'unique_keys_verified': 12, 'small_cells_suppressed': 0,
                    'supplied_manifest_verified': True},
        'aggregates': [{'month': '2026-09', 'borough': 'QUEENS',
                        'agency': 'SYNTHETIC', 'problem': 'SYNTHETIC',
                        'requests': 12, 'closed_with_valid_interval': 12}]
    }


class ProvenanceFlagTests(unittest.TestCase):
    def test_true_flag_does_not_invalidate_aggregate_contract(self):
        result = audit_single(fixture())
        self.assertTrue(result['structural_valid'])
        self.assertEqual(result['status'], 'HOLD')

    def test_false_flag_does_not_imply_source_authentication(self):
        payload = fixture()
        payload['quality']['supplied_manifest_verified'] = False
        result = audit_single(payload)
        self.assertTrue(result['structural_valid'])
        self.assertEqual(result['status'], 'HOLD')

    def test_nonboolean_flag_rejected(self):
        payload = fixture()
        payload['quality']['supplied_manifest_verified'] = 1
        self.assertFalse(audit_single(payload)['structural_valid'])

    def test_changed_flag_reported_without_numeric_delta(self):
        previous = fixture()
        current = copy.deepcopy(previous)
        current['quality']['supplied_manifest_verified'] = False
        result = audit_pair(previous, current)
        self.assertIn('SOURCE_MANIFEST_VERIFICATION_CHANGED', result['codes'])
        self.assertEqual(result['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
