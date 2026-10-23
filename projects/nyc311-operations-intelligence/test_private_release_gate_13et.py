"""Synthetic-only private gate integration and adversarial contract tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import private_release_gate as gate


class PrivateReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.candidate = {'source': 'synthetic'}
        self.evidence = {'coefficients': [[1, 1]], 'totals': [2],
                         'suppressed': [0, 1], 'sensitive_groups': [[0, 1]]}
        self.hold = {'status': 'HOLD', 'manual_review_required': True, 'codes': []}

    def test_missing_evidence_is_not_clearance(self):
        with patch.object(gate, 'audit_single', return_value=self.hold):
            result = gate.audit_release(self.candidate)
        self.assertIn('MARGINAL_EVIDENCE_NOT_SUPPLIED', result['codes'])
        self.assertIn('INTEGER_EVIDENCE_NOT_SUPPLIED', result['codes'])
        self.assertFalse(result['release_authorized'])

    def test_both_screens_invoked(self):
        with patch.object(gate, 'audit_single', return_value=self.hold), \
             patch.object(gate, 'audit_marginals', return_value={**self.hold, 'codes': ['LINEAR_RISK']}) as linear, \
             patch.object(gate, 'audit_integer_feasibility', return_value={**self.hold, 'codes': ['INTEGER_RISK']}) as integer:
            result = gate.audit_release(self.candidate, evidence=self.evidence)
        linear.assert_called_once()
        integer.assert_called_once()
        self.assertIn('LINEAR_RISK', result['codes'])
        self.assertIn('INTEGER_RISK', result['codes'])

    def test_previous_candidate_uses_temporal_screen(self):
        with patch.object(gate, 'audit_pair', return_value=self.hold) as pair:
            gate.audit_release(self.candidate, previous={'source': 'earlier'})
        pair.assert_called_once()

    def test_unexpected_evidence_fields_fail_closed(self):
        with patch.object(gate, 'audit_single', return_value=self.hold), \
             patch.object(gate, 'audit_marginals') as linear:
            result = gate.audit_release(self.candidate, evidence={**self.evidence, 'identifiers': ['secret']})
        self.assertIn('INVALID_MARGINAL_EVIDENCE_CONTRACT', result['codes'])
        linear.assert_not_called()

    def test_untrusted_dependency_cannot_approve(self):
        with patch.object(gate, 'audit_single', return_value={'status': 'APPROVED', 'codes': ['OK']}):
            result = gate.audit_release(self.candidate)
        self.assertIn('INVALID_AUDIT_RESPONSE', result['codes'])
        self.assertFalse(result['release_authorized'])

    def test_dependency_exception_redacted(self):
        with patch.object(gate, 'audit_single', side_effect=RuntimeError('PRIVATE_VALUE')):
            result = gate.audit_release(self.candidate)
        self.assertIn('AGGREGATE_AUDIT_FAILED_CLOSED', result['codes'])
        self.assertNotIn('PRIVATE_VALUE', json.dumps(result))

    def test_real_marginal_and_integer_screens_are_called(self):
        with patch.object(gate, 'audit_single', return_value=self.hold):
            result = gate.audit_release(self.candidate, evidence=self.evidence)
        self.assertIn('SENSITIVE_GROUP_SUM_RECONSTRUCTIBLE_FROM_MARGINALS', result['codes'])
        self.assertIn('SENSITIVE_GROUP_SUM_INTEGER_RECONSTRUCTIBLE', result['codes'])
        self.assertFalse(result['release_authorized'])

    def test_redacted_report_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'candidate.json').write_text(json.dumps({'secret': 'DO_NOT_LEAK'}))
            with patch.object(gate, 'audit_single', return_value=self.hold):
                exit_code = gate.main([str(root / 'candidate.json'), '--report', str(root / 'report.json')])
            report = (root / 'report.json').read_text()
            self.assertEqual(exit_code, 2)
            self.assertNotIn('DO_NOT_LEAK', report)
            self.assertEqual(json.loads(report)['status'], 'HOLD')

    def test_malformed_json_does_not_leak(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'bad.json').write_text('PRIVATE_INVALID_JSON')
            code = gate.main([str(root / 'bad.json'), '--report', str(root / 'report.json')])
            report = (root / 'report.json').read_text()
            self.assertEqual(code, 2)
            self.assertIn('INPUT_READ_OR_PARSE_FAILED_CLOSED', report)
            self.assertNotIn('PRIVATE_INVALID_JSON', report)

    def test_invalid_code_shape_redacted(self):
        self.assertEqual(gate._codes({'status': 'HOLD', 'manual_review_required': True,
                                      'codes': ['private group name']}), ['INVALID_AUDIT_RESPONSE'])


if __name__ == '__main__':
    unittest.main()
