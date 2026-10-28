"""Synthetic, source-free adversarial tests for known-support inference."""
import unittest
from known_support_disclosure_gate import audit, SCHEMA, ALL_BOROUGHS


class KnownSupportDisclosureGateTests(unittest.TestCase):
    def fixture(self, missing=True):
        agencies = [f'AGENCY_{i:02}' for i in range(14)]
        groups = ['A', 'B', 'C', 'D']
        mapping = {a: ('A' if i < 2 else 'B' if i < 6
                       else 'C' if i < 10 else 'D')
                   for i, a in enumerate(agencies)}
        rows = []
        for borough in ALL_BOROUGHS:
            for agency in agencies:
                if missing and borough == 'BRONX' and agency == agencies[1]:
                    continue
                rows.append({'borough': borough, 'agency': agency,
                             'requests': 1 if borough == 'BRONX' and agency == agencies[0] else 20})
        return {'schema_version': SCHEMA, 'dataset_id': 'erm2-nwe9',
                'group_labels': groups, 'agency_to_group': mapping,
                'fine_rows': rows, 'minimum_cell_count': 10}

    def test_structural_zero_changes_inference(self):
        codes = audit(self.fixture())['codes']
        self.assertIn('KNOWN_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)
        self.assertNotIn('ALL_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)

    def test_full_support_does_not_force_small_cell(self):
        codes = audit(self.fixture(missing=False))['codes']
        self.assertNotIn('KNOWN_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)
        self.assertNotIn('ALL_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)

    def test_singleton_editorial_group_forces_both_models(self):
        data = self.fixture(missing=False)
        data['agency_to_group']['AGENCY_01'] = 'B'
        codes = audit(data)['codes']
        self.assertIn('ALL_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)
        self.assertIn('KNOWN_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE', codes)

    def test_duplicate_fine_pair_fails_closed(self):
        data = self.fixture()
        data['fine_rows'].append(dict(data['fine_rows'][0]))
        self.assertIn('DUPLICATE_SOURCE_GROUP', audit(data)['codes'])

    def test_unmapped_source_agency_fails_closed(self):
        data = self.fixture()
        data['fine_rows'][0]['agency'] = 'UNMAPPED'
        self.assertIn('INVALID_KNOWN_SUPPORT_CONTRACT', audit(data)['codes'])

    def test_boolean_count_fails_closed(self):
        data = self.fixture()
        data['fine_rows'][0]['requests'] = True
        self.assertIn('INVALID_KNOWN_SUPPORT_CONTRACT', audit(data)['codes'])

    def test_incomplete_group_coverage_fails_closed(self):
        data = self.fixture()
        data['fine_rows'] = [r for r in data['fine_rows']
                             if r['agency'] != 'AGENCY_13']
        self.assertIn('INCOMPLETE_SOURCE_GROUP_COVERAGE', audit(data)['codes'])

    def test_order_invariant_and_redacted(self):
        data = self.fixture()
        before = audit(data)
        data['fine_rows'].reverse()
        self.assertEqual(before, audit(data))
        self.assertEqual(before['status'], 'HOLD')
        self.assertFalse(before['publication_approved'])
        self.assertNotIn('AGENCY_00', str(before))
        self.assertNotIn('BRONX', str(before))
        self.assertNotIn("'requests'", str(before))


if __name__ == '__main__':
    unittest.main()
