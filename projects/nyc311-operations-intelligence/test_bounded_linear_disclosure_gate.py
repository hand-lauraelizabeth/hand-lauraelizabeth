"""Adversarial synthetic checks for bounded multi-release linear inference."""
import unittest
from bounded_linear_disclosure_gate import audit, _contrasts
from multi_release_disclosure_gate import audit as earlier_audit, SCHEMA
from paired_release_differencing_gate import BOROUGHS


class BoundedLinearTests(unittest.TestCase):
    def fixture(self, values):
        groups = ['A', 'B', 'C', 'D']
        snapshots = []
        for i, value in enumerate(values):
            cells = [{'borough': b, 'group': g, 'requests': value}
                     for b in BOROUGHS for g in groups]
            snapshots.append({'as_of': f'2026-10-28T{10+i:02d}:00:00-04:00',
                              'source_revision': f'rev-{i}',
                              'mapping_sha256': 'a' * 64, 'cells': cells})
        return {'schema_version': SCHEMA, 'dataset_id': 'erm2-nwe9',
                'reporting_month': '2026-09', 'group_labels': groups,
                'minimum_disclosure_delta': 10, 'snapshots': snapshots}

    def test_six_release_contrast_hidden_from_existing_gate(self):
        # Every pair, 3-release second difference and 4-release 2+2
        # contrast is >=10 or zero; 337+625+682-350-532-764 = -2.
        data = self.fixture([337, 350, 532, 625, 682, 764])
        old = earlier_audit(data)['codes']
        self.assertFalse(any(code.startswith('SMALL_') for code in old))
        new = audit(data)['codes']
        self.assertIn('SMALL_BOUNDED_LINEAR_CELL_CONTRAST', new)
        self.assertIn('SMALL_BOUNDED_LINEAR_BOROUGH_CONTRAST', new)
        self.assertIn('SMALL_BOUNDED_LINEAR_GROUP_CONTRAST', new)

    def test_no_false_positive_on_multiples_of_twenty(self):
        data = self.fixture([100, 120, 140, 160, 180, 200, 220, 240])
        self.assertFalse(any(code.startswith('SMALL_BOUNDED') for code in audit(data)['codes']))

    def test_primitive_sign_canonical_and_bounded(self):
        contrasts = list(_contrasts(6))
        self.assertIn((1, -1, -1, 1, 1, -1), contrasts)
        self.assertNotIn((-1, 1, 1, -1, -1, 1), contrasts)
        self.assertTrue(all(sum(x) == 0 and sum(map(abs, x)) <= 8 for x in contrasts))

    def test_invalid_contract_is_fail_closed(self):
        data = self.fixture([100, 120, 140])
        data['snapshots'][1]['cells'][0]['requests'] = True
        result = audit(data)
        self.assertIn('INVALID_MULTI_RELEASE_CONTRACT', result['codes'])
        self.assertFalse(result['publication_approved'])

    def test_mapping_drift_is_not_compared(self):
        data = self.fixture([100, 120, 141])
        data['snapshots'][1]['mapping_sha256'] = 'b' * 64
        result = audit(data)
        self.assertIn('MAPPING_FINGERPRINT_MISMATCH', result['codes'])
        self.assertNotIn('SMALL_BOUNDED_LINEAR_CELL_CONTRAST', result['codes'])

    def test_redacted_and_order_independent(self):
        data = self.fixture([337, 350, 532, 625, 682, 764])
        original = audit(data)
        for snapshot in data['snapshots']:
            snapshot['cells'].reverse()
        self.assertEqual(original, audit(data))
        for secret in ('BRONX', '337', '682', 'rev-0', 'aaaa', "'A'"):
            self.assertNotIn(secret, str(original))
        self.assertEqual(original['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
