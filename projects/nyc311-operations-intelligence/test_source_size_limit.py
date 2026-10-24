"""Synthetic-only regression: untrusted source CSVs cannot exhaust snapshot storage.

The cap is a private operational guard, not proof of official provenance,
publisher completeness, or disclosure safety. No real 311 rows are included.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class BoundedSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.csv'
        self.snapshot = self.root / 'snapshot.csv'
        self.candidate_path = self.root / 'candidate.json'
        self.report = self.root / 'report.json'

    @staticmethod
    def claim(data, *, source_bytes=None):
        return {
            'source_sha256': hashlib.sha256(data).hexdigest(),
            'source_bytes': len(data) if source_bytes is None else source_bytes,
        }

    def test_declared_oversize_rejected_before_snapshot_creation(self):
        data = b'unique_key\n001\n'
        self.source.write_bytes(data)
        with patch.object(gate, 'MAX_SOURCE_BYTES', 12):
            codes = gate._source_binding_codes(
                self.claim(data, source_bytes=13), self.source,
                snapshot_path=self.snapshot)
        self.assertEqual(codes, ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED'])
        self.assertFalse(self.snapshot.exists())
        self.assertEqual(self.source.read_bytes(), data)

    def test_underreported_source_cannot_write_past_cap(self):
        data = b'A' * 257
        self.source.write_bytes(data)
        with patch.object(gate, 'MAX_SOURCE_BYTES', 128):
            codes = gate._source_binding_codes(
                self.claim(data, source_bytes=100), self.source,
                snapshot_path=self.snapshot)
        self.assertEqual(codes, ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED'])
        self.assertLessEqual(self.snapshot.stat().st_size, 128)
        self.assertEqual(self.source.read_bytes(), data)

    def test_exact_byte_limit_is_accepted_but_not_authenticated(self):
        data = b'B' * 128
        self.source.write_bytes(data)
        with patch.object(gate, 'MAX_SOURCE_BYTES', 128):
            codes = gate._source_binding_codes(
                self.claim(data), self.source, snapshot_path=self.snapshot)
        self.assertEqual(codes, [
            'SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM',
            'SOURCE_ORIGIN_NOT_AUTHENTICATED'])
        self.assertEqual(self.snapshot.read_bytes(), data)

    def test_oversize_is_detected_without_snapshot_argument(self):
        data = b'C' * 129
        self.source.write_bytes(data)
        with patch.object(gate, 'MAX_SOURCE_BYTES', 128):
            codes = gate._source_binding_codes(
                self.claim(data, source_bytes=128), self.source)
        self.assertEqual(codes, ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED'])

    def test_integrated_preflight_holds_and_does_not_audit_oversize(self):
        data = b'unique_key,created_date\n' + b'X' * 128
        self.source.write_bytes(data)
        self.candidate_path.write_text(json.dumps(self.claim(
            data, source_bytes=50)), encoding='utf-8')
        with (patch.object(gate, 'MAX_SOURCE_BYTES', 64),
              patch.object(gate, 'audit_release', return_value={
                  'status': 'HOLD', 'manual_review_required': True,
                  'release_authorized': False, 'codes': []
              }),
              patch.object(gate, 'audit_unique_keys') as audit):
            rc = gate.main([
                str(self.candidate_path), '--source-csv', str(self.source),
                '--created-month', '2026-09', '--report', str(self.report)])
            audit.assert_not_called()
        self.assertEqual(rc, 2)
        report_text = self.report.read_text(encoding='utf-8')
        result = json.loads(report_text)
        self.assertEqual(result['status'], 'HOLD')
        self.assertFalse(result['release_authorized'])
        self.assertIn('SOURCE_CSV_SIZE_LIMIT_EXCEEDED', result['codes'])
        self.assertNotIn('unique_key', report_text)
        self.assertNotIn('2026-09', report_text)
        self.assertEqual(self.source.read_bytes(), data)

    def test_oversize_claim_rejected_without_source_read(self):
        with patch.object(gate, 'MAX_SOURCE_BYTES', 32):
            codes = gate._source_binding_codes(
                {'source_bytes': 33, 'source_sha256': '0' * 64},
                self.root / 'nonexistent.csv', snapshot_path=self.snapshot)
        self.assertEqual(codes, ['SOURCE_CSV_SIZE_LIMIT_EXCEEDED'])
        self.assertFalse(self.snapshot.exists())


if __name__ == '__main__':
    unittest.main()
