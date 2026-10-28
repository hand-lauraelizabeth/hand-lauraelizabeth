"""Synthetic privacy tests for all-pair and four-release contrasts."""
import copy
import unittest
from multi_release_disclosure_gate import audit, SCHEMA
from paired_release_differencing_gate import BOROUGHS


class MultiReleaseTests(unittest.TestCase):
    def fixture(self, values=(100, 120, 141, 162)):
        groups = ['A', 'B', 'C', 'D']
        snapshots = []
        for i, value in enumerate(values):
            cells = [{'borough': b, 'group': g, 'requests': value}
                     for b in BOROUGHS for g in groups]
            snapshots.append({'as_of': f'2026-10-28T{10+i:02d}:00:00-04:00',
                              'source_revision': f'rev-{i}',
                              'mapping_sha256': 'a'*64, 'cells': cells})
        return {'schema_version': SCHEMA, 'dataset_id': 'erm2-nwe9',
                'reporting_month': '2026-09', 'group_labels': groups,
                'minimum_disclosure_delta': 10, 'snapshots': snapshots}

    def test_four_release_hidden_small_contrast(self):
        data = self.fixture()
        codes = audit(data)['codes']
        self.assertIn('SMALL_FOUR_RELEASE_CELL_CONTRAST', codes)
        self.assertNotIn('SMALL_PAIR_CELL_DIFFERENCE', codes)
        self.assertIn('SMALL_FOUR_RELEASE_BOROUGH_CONTRAST', codes)
        self.assertIn('SMALL_FOUR_RELEASE_GROUP_CONTRAST', codes)

    def test_nonadjacent_pair(self):
        data = self.fixture((100, 140, 103))
        self.assertIn('SMALL_PAIR_CELL_DIFFERENCE', audit(data)['codes'])

    def test_no_approval_for_identical_releases(self):
        result = audit(self.fixture((100,100,100)))
        self.assertEqual(result['status'], 'HOLD')
        self.assertFalse(result['publication_approved'])
        self.assertNotIn('SMALL_PAIR_CELL_DIFFERENCE', result['codes'])

    def test_mapping_drift_short_circuits(self):
        data = self.fixture()
        data['snapshots'][-1]['mapping_sha256'] = 'b'*64
        codes = audit(data)['codes']
        self.assertIn('MAPPING_FINGERPRINT_MISMATCH', codes)
        self.assertNotIn('SMALL_FOUR_RELEASE_CELL_CONTRAST', codes)

    def test_revision_inconsistency(self):
        data = self.fixture((100, 120, 141))
        data['snapshots'][1]['source_revision'] = 'rev-0'
        self.assertIn('UNCHANGED_REVISION_WITH_CHANGED_COUNTS', audit(data)['codes'])

    def test_invalid_snapshot_order(self):
        data = self.fixture((100,120,141))
        data['snapshots'][1]['as_of'] = '2026-10-28T14:00:00Z'
        self.assertIn('INVALID_SNAPSHOT_ORDER', audit(data)['codes'])

    def test_bad_contracts(self):
        for mutation in ('bool', 'too_many', 'missing', 'duplicate', 'negative'):
            with self.subTest(mutation=mutation):
                data = self.fixture()
                if mutation == 'bool': data['minimum_disclosure_delta'] = True
                if mutation == 'too_many': data['snapshots'] *= 3
                if mutation == 'missing': data['snapshots'][1]['cells'].pop()
                if mutation == 'duplicate': data['snapshots'][1]['cells'][1] = dict(data['snapshots'][1]['cells'][0])
                if mutation == 'negative': data['snapshots'][1]['cells'][0]['requests'] = -1
                self.assertIn('INVALID_MULTI_RELEASE_CONTRACT', audit(data)['codes'])

    def test_redaction_and_row_order(self):
        data = self.fixture()
        original = audit(data)
        for snap in data['snapshots']: snap['cells'].reverse()
        self.assertEqual(original, audit(data))
        for secret in ('BRONX', '100', '162', 'rev-0', 'aaaa', "'A'"):
            self.assertNotIn(secret, str(original))

    def test_marginal_contrast_without_small_cells(self):
        data = self.fixture((100,120,141,162))
        for i, snap in enumerate(data['snapshots']):
            snap['cells'][1]['requests'] += (0, 0, 0, 19)[i]
        self.assertIn('SMALL_FOUR_RELEASE_BOROUGH_CONTRAST', audit(data)['codes'])


if __name__ == '__main__':
    unittest.main()
