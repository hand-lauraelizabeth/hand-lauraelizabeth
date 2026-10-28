"""Source-free mapping-drift regression tests; never include NYC 311 counts."""
import copy
import unittest
from reviewed_mapping_binding_gate import SCHEMA, audit, fingerprint


class MappingBindingTests(unittest.TestCase):
    def setUp(self):
        labels = ['Access', 'Housing', 'Mobility', 'Environment']
        self.candidate = {
            'schema_version': SCHEMA, 'dataset_id': 'erm2-nwe9',
            'reporting_month': '2026-09', 'group_labels': labels,
            'agency_to_group': {f'SYNTHETIC_{i:02}': labels[i // 4 if i < 12 else 3]
                                for i in range(14)}}
        self.reviewed = fingerprint(self.candidate)

    def test_exact_fingerprint_match_is_still_hold(self):
        result = audit(self.candidate, self.reviewed)
        self.assertIn('FINGERPRINT_MATCH_NOT_PROVENANCE_PROOF', result['codes'])
        self.assertFalse(result['publication_approved'])
        self.assertEqual('HOLD', result['status'])

    def test_map_order_does_not_change_fingerprint(self):
        data = copy.deepcopy(self.candidate)
        data['agency_to_group'] = dict(reversed(list(data['agency_to_group'].items())))
        self.assertEqual(fingerprint(data), self.reviewed)

    def test_single_agency_reassignment_detected(self):
        data = copy.deepcopy(self.candidate)
        data['agency_to_group']['SYNTHETIC_02'] = 'Housing'
        self.assertIn('MAPPING_FINGERPRINT_MISMATCH', audit(data, self.reviewed)['codes'])

    def test_label_reordering_detected(self):
        data = copy.deepcopy(self.candidate)
        data['group_labels'].reverse()
        self.assertIn('MAPPING_FINGERPRINT_MISMATCH', audit(data, self.reviewed)['codes'])

    def test_missing_independent_digest_fails_closed(self):
        self.assertIn('REVIEWED_MAPPING_FINGERPRINT_REQUIRED', audit(self.candidate, None)['codes'])

    def test_malformed_digest_fails_closed(self):
        self.assertIn('REVIEWED_MAPPING_FINGERPRINT_REQUIRED', audit(self.candidate, 'f' * 63)['codes'])

    def test_undocumented_extra_field_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['verified'] = True
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_duplicate_label_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['group_labels'][1] = data['group_labels'][0]
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_unused_group_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['agency_to_group'] = {k: 'Access' for k in data['agency_to_group']}
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_wrong_month_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['reporting_month'] = '2026-10'
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_wrong_dataset_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['dataset_id'] = 'other'
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_missing_agency_rejected(self):
        data = copy.deepcopy(self.candidate)
        del data['agency_to_group']['SYNTHETIC_13']
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_whitespace_agency_rejected(self):
        data = copy.deepcopy(self.candidate)
        data['agency_to_group'][' SYNTHETIC_00'] = data['agency_to_group'].pop('SYNTHETIC_00')
        self.assertIn('INVALID_MAPPING_BINDING_CONTRACT', audit(data, self.reviewed)['codes'])

    def test_output_redacted_no_labels_or_digest(self):
        result = str(audit(self.candidate, self.reviewed))
        self.assertNotIn('SYNTHETIC_', result)
        self.assertNotIn('Housing', result)
        self.assertNotIn(self.reviewed, result)


if __name__ == '__main__':
    unittest.main()
