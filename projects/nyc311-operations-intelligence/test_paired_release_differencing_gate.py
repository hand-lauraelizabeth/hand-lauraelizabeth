"""Synthetic adversarial regression tests for paired-release disclosure risk."""
import copy
import unittest
from paired_release_differencing_gate import audit, SCHEMA, BOROUGHS


class PairedReleaseDifferencingGateTests(unittest.TestCase):
    def fixture(self):
        groups = ['OPERATIONS', 'INFRASTRUCTURE', 'SAFETY', 'OTHER']
        cells = [{'borough': b, 'group': g, 'requests': 100}
                 for b in BOROUGHS for g in groups]
        snap = {'as_of': '2026-10-28T13:00:00-04:00',
                'source_revision': 'revision-1', 'mapping_sha256': 'a' * 64,
                'cells': cells}
        later = copy.deepcopy(snap)
        later['as_of'] = '2026-10-28T14:00:00-04:00'
        later['source_revision'] = 'revision-2'
        return {'schema_version': SCHEMA, 'dataset_id': 'erm2-nwe9',
                'reporting_month': '2026-09', 'group_labels': groups,
                'minimum_disclosure_delta': 10,
                'earlier': snap, 'later': later}

    def test_unchanged_releases_still_hold(self):
        result = audit(self.fixture())
        self.assertEqual(result['status'], 'HOLD')
        self.assertFalse(result['publication_approved'])
        self.assertNotIn('SMALL_CELL_DIFFERENCE_EXPOSED', result['codes'])

    def test_single_small_delta_detected(self):
        data = self.fixture()
        data['later']['cells'][0]['requests'] += 1
        codes = audit(data)['codes']
        self.assertIn('SMALL_CELL_DIFFERENCE_EXPOSED', codes)
        self.assertIn('SMALL_BOROUGH_MARGINAL_DIFFERENCE_EXPOSED', codes)
        self.assertIn('SMALL_GROUP_MARGINAL_DIFFERENCE_EXPOSED', codes)

    def test_small_marginal_even_when_cell_deltas_large(self):
        data = self.fixture()
        data['later']['cells'][0]['requests'] += 20
        data['later']['cells'][1]['requests'] -= 19
        codes = audit(data)['codes']
        self.assertNotIn('SMALL_CELL_DIFFERENCE_EXPOSED', codes)
        self.assertIn('SMALL_BOROUGH_MARGINAL_DIFFERENCE_EXPOSED', codes)

    def test_negative_correction_detected(self):
        data = self.fixture()
        data['later']['cells'][0]['requests'] -= 11
        self.assertIn('NEGATIVE_CELL_DIFFERENCE_REVIEW_REQUIRED', audit(data)['codes'])

    def test_unchanged_revision_with_changed_counts(self):
        data = self.fixture()
        data['later']['source_revision'] = 'revision-1'
        data['later']['cells'][0]['requests'] += 20
        self.assertIn('UNCHANGED_SOURCE_REVISION_WITH_CHANGED_COUNTS', audit(data)['codes'])

    def test_mapping_mismatch_short_circuits_differencing(self):
        data = self.fixture()
        data['later']['mapping_sha256'] = 'b' * 64
        data['later']['cells'][0]['requests'] += 1
        codes = audit(data)['codes']
        self.assertIn('MAPPING_FINGERPRINT_MISMATCH', codes)
        self.assertNotIn('SMALL_CELL_DIFFERENCE_EXPOSED', codes)

    def test_reverse_order_detected(self):
        data = self.fixture()
        data['earlier']['as_of'] = '2026-10-28T16:00:00-04:00'
        self.assertIn('INVALID_SNAPSHOT_ORDER', audit(data)['codes'])

    def test_timezone_equivalent_order_detected(self):
        data = self.fixture()
        data['earlier']['as_of'] = '2026-10-28T18:00:00Z'
        self.assertIn('INVALID_SNAPSHOT_ORDER', audit(data)['codes'])

    def test_naive_time_rejected(self):
        data = self.fixture()
        data['later']['as_of'] = '2026-10-28T14:00:00'
        self.assertIn('INVALID_PAIRED_RELEASE_CONTRACT', audit(data)['codes'])

    def test_duplicate_cell_rejected(self):
        data = self.fixture()
        data['later']['cells'][1] = dict(data['later']['cells'][0])
        self.assertIn('INVALID_PAIRED_RELEASE_CONTRACT', audit(data)['codes'])

    def test_boolean_count_rejected(self):
        data = self.fixture()
        data['later']['cells'][0]['requests'] = True
        self.assertIn('INVALID_PAIRED_RELEASE_CONTRACT', audit(data)['codes'])

    def test_missing_cell_rejected(self):
        data = self.fixture()
        data['later']['cells'].pop()
        self.assertIn('INVALID_PAIRED_RELEASE_CONTRACT', audit(data)['codes'])

    def test_inconsistent_group_labels_rejected(self):
        data = self.fixture()
        data['group_labels'][0] = 'INVALID'
        self.assertIn('INVALID_PAIRED_RELEASE_CONTRACT', audit(data)['codes'])

    def test_output_redacted_and_order_invariant(self):
        data = self.fixture()
        data['later']['cells'][0]['requests'] += 1
        result = audit(data)
        data['later']['cells'].reverse()
        data['earlier']['cells'].reverse()
        self.assertEqual(result, audit(data))
        for forbidden in ('BRONX', 'OPERATIONS', '101', '100', 'revision-1', 'aaaaaaaa'):
            self.assertNotIn(forbidden, str(result))


if __name__ == '__main__':
    unittest.main()
