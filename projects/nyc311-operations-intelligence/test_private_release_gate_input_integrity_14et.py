"""Synthetic adversarial tests: source-file preservation and strict JSON parsing."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class PrivateGateInputIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.hold = {'status': 'HOLD', 'manual_review_required': True, 'codes': []}

    def test_report_same_as_candidate_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            candidate = Path(td) / 'candidate.json'
            original = '{"private":"PRESERVE"}'
            candidate.write_text(original)
            code = gate.main([str(candidate), '--report', str(candidate)])
            self.assertEqual(code, 2)
            self.assertEqual(candidate.read_text(), original)

    def test_relative_alias_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / 'candidate.json'
            candidate.write_text('{"private":"PRESERVE"}')
            report = root / 'sub' / '..' / 'candidate.json'
            (root / 'sub').mkdir()
            code = gate.main([str(candidate), '--report', str(report)])
            self.assertEqual(code, 2)
            self.assertIn('PRESERVE', candidate.read_text())

    def test_symlink_alias_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / 'candidate.json'
            candidate.write_text('{"private":"PRESERVE"}')
            report = root / 'report.json'
            report.symlink_to(candidate)
            code = gate.main([str(candidate), '--report', str(report)])
            self.assertEqual(code, 2)
            self.assertTrue(report.is_symlink())
            self.assertIn('PRESERVE', candidate.read_text())

    def test_hardlink_alias_never_overwrites(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / 'candidate.json'
            candidate.write_text('{"private":"PRESERVE"}')
            report = root / 'report.json'
            os.link(candidate, report)
            code = gate.main([str(candidate), '--report', str(report)])
            self.assertEqual(code, 2)
            self.assertEqual(candidate.read_text(), report.read_text())

    def test_report_aliases_previous_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, previous = root / 'candidate.json', root / 'previous.json'
            candidate.write_text('{}')
            previous.write_text('{"private":"PRESERVE"}')
            code = gate.main([str(candidate), '--previous-json', str(previous),
                              '--report', str(previous)])
            self.assertEqual(code, 2)
            self.assertIn('PRESERVE', previous.read_text())

    def test_report_aliases_evidence_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, evidence = root / 'candidate.json', root / 'evidence.json'
            candidate.write_text('{}')
            evidence.write_text('{"private":"PRESERVE"}')
            code = gate.main([str(candidate), '--marginal-evidence-json', str(evidence),
                              '--report', str(evidence)])
            self.assertEqual(code, 2)
            self.assertIn('PRESERVE', evidence.read_text())

    def test_duplicate_top_level_key_rejected(self):
        self._assert_parse_rejected('{"source":"synthetic","source":"PRIVATE"}')

    def test_duplicate_nested_key_rejected(self):
        self._assert_parse_rejected('{"quality":{"a":1,"a":2}}')

    def test_nonfinite_nan_rejected(self):
        self._assert_parse_rejected('{"quality":{"counter":NaN}}')

    def test_nonfinite_infinity_rejected(self):
        self._assert_parse_rejected('{"quality":{"counter":Infinity}}')

    def _assert_parse_rejected(self, payload):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, report = root / 'candidate.json', root / 'report.json'
            candidate.write_text(payload)
            with patch.object(gate, 'audit_single') as audit:
                code = gate.main([str(candidate), '--report', str(report)])
            self.assertEqual(code, 2)
            audit.assert_not_called()
            result = json.loads(report.read_text())
            self.assertIn('INPUT_READ_OR_PARSE_FAILED_CLOSED', result['codes'])
            self.assertNotIn('PRIVATE', report.read_text())

    def test_valid_json_still_runs_hold_audit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate, report = root / 'candidate.json', root / 'report.json'
            candidate.write_text('{"source":"synthetic"}')
            with patch.object(gate, 'audit_single', return_value=self.hold) as audit:
                code = gate.main([str(candidate), '--report', str(report)])
            self.assertEqual(code, 2)
            audit.assert_called_once()
            result = json.loads(report.read_text())
            self.assertFalse(result['release_authorized'])
            self.assertEqual(result['status'], 'HOLD')


if __name__ == '__main__':
    unittest.main()
