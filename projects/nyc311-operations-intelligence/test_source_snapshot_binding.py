"""Synthetic-only regression: hash and audit the same private source bytes.

Publisher schema: https://data.cityofnewyork.us/d/erm2-nwe9
A matching digest is not independent authentication of official provenance.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate


class ImmutableSourceSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.csv'
        self.candidate = self.root / 'candidate.json'
        self.report = self.root / 'report.json'
        self.csv = (b'unique_key,created_date\n'
                    b'001,2026-09-01T00:00:00\n'
                    b'002,2026-09-30T23:59:59\n')
        self.source.write_bytes(self.csv)
        self.candidate.write_text(json.dumps({
            'source_sha256': hashlib.sha256(self.csv).hexdigest(),
            'source_bytes': len(self.csv), 'source_rows': 2,
        }), encoding='utf-8')

    def run_gate(self):
        with patch.object(gate, 'audit_release', return_value={
            'status': 'HOLD', 'manual_review_required': True,
            'release_authorized': False, 'codes': []
        }):
            return gate.main([str(self.candidate), '--source-csv', str(self.source),
                              '--created-month', '2026-09',
                              '--report', str(self.report)])

    def test_mutation_between_hash_and_audit_cannot_change_audited_bytes(self):
        observed = []
        original_audit = gate.audit_unique_keys

        def replace_original_before_audit(snapshot, **kwargs):
            snapshot = Path(snapshot)
            self.assertNotEqual(snapshot.resolve(), self.source.resolve())
            self.assertEqual(snapshot.read_bytes(), self.csv)
            self.source.write_bytes(b'unique_key,created_date\n999,2026-10-01T00:00:00\n')
            observed.append(snapshot)
            return original_audit(snapshot, **kwargs)

        with patch.object(gate, 'audit_unique_keys', side_effect=replace_original_before_audit):
            self.assertEqual(self.run_gate(), 2)
        self.assertEqual(len(observed), 1)
        self.assertFalse(observed[0].exists(), 'private snapshot must be deleted')
        codes = json.loads(self.report.read_text(encoding='utf-8'))['codes']
        self.assertIn('SOURCE_CREATED_DATE_MONTH_MATCHED', codes)
        self.assertIn('SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM', codes)
        self.assertIn('SOURCE_ORIGIN_NOT_AUTHENTICATED', codes)
        self.assertNotIn('999', self.report.read_text(encoding='utf-8'))

    def test_modified_source_does_not_pass_binding(self):
        self.source.write_bytes(b'unique_key,created_date\n999,2026-10-01T00:00:00\n')
        with patch.object(gate, 'audit_unique_keys') as audit:
            self.assertEqual(self.run_gate(), 2)
            audit.assert_not_called()
        self.assertIn('SOURCE_CSV_BINDING_FAILED',
                      json.loads(self.report.read_text(encoding='utf-8'))['codes'])

    def test_missing_source_fails_closed_without_audit(self):
        self.source.unlink()
        with patch.object(gate, 'audit_unique_keys') as audit:
            self.assertEqual(self.run_gate(), 2)
            audit.assert_not_called()
        self.assertIn('SOURCE_CSV_READ_FAILED_CLOSED',
                      json.loads(self.report.read_text(encoding='utf-8'))['codes'])

    def test_chunked_snapshot_exact_bytes_and_no_origin_claim(self):
        payload = b'a' * (2 * 1024 * 1024 + 17)
        self.source.write_bytes(payload)
        self.candidate.write_text(json.dumps({
            'source_sha256': hashlib.sha256(payload).hexdigest(),
            'source_bytes': len(payload),
        }), encoding='utf-8')
        snapshot = self.root / 'snapshot.csv'
        candidate = json.loads(self.candidate.read_text(encoding='utf-8'))
        codes = gate._source_binding_codes(candidate, self.source,
                                            snapshot_path=snapshot)
        self.assertEqual(snapshot.read_bytes(), payload)
        self.assertEqual(codes, ['SOURCE_CSV_BYTES_MATCH_CANDIDATE_CLAIM',
                                 'SOURCE_ORIGIN_NOT_AUTHENTICATED'])


if __name__ == '__main__':
    unittest.main()
