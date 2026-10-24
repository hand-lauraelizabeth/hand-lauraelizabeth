"""Synthetic-only regression for NYC 311 floating created_date month grain.

Official schema: https://data.cityofnewyork.us/resource/erm2-nwe9
Unique Key = text; Created Date = floating timestamp. These tests do not
authenticate an official export or establish completeness.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import private_release_gate as gate
from source_unique_key_audit import audit_unique_keys


class SourceCreatedMonthAuditTests(unittest.TestCase):
    def audit(self, payload, *, month='2026-09', expected_rows=2):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'synthetic.csv'
            path.write_bytes(payload)
            return audit_unique_keys(path, expected_rows=expected_rows,
                                     expected_month=month)

    def test_api_iso_floating_timestamp_boundaries(self):
        csv = (b'unique_key,created_date\n'
               b'001,2026-09-01T00:00:00.000\n'
               b'002,2026-09-30T23:59:59.999\n')
        self.assertEqual(self.audit(csv),
                         ['SOURCE_UNIQUE_KEYS_DISTINCT', 'SOURCE_ROW_COUNT_MATCHED',
                          'SOURCE_CREATED_DATE_MONTH_MATCHED'])

    def test_portal_display_date_with_am_pm(self):
        csv = (b'Unique Key,Created Date\r\n'
               b'001,09/01/2026 12:00:00 AM\r\n'
               b'002,09/30/2026 11:59:59 PM\r\n')
        self.assertIn('SOURCE_CREATED_DATE_MONTH_MATCHED', self.audit(csv))

    def test_october_boundary_rejected(self):
        csv = (b'unique_key,created_date\n'
               b'001,2026-09-30T23:59:59\n'
               b'002,2026-10-01T00:00:00\n')
        self.assertEqual(self.audit(csv), ['SOURCE_CREATED_DATE_OUTSIDE_MONTH'])

    def test_august_boundary_rejected(self):
        csv = (b'unique_key,created_date\n'
               b'001,2026-08-31T23:59:59\n'
               b'002,2026-09-01T00:00:00\n')
        self.assertEqual(self.audit(csv), ['SOURCE_CREATED_DATE_OUTSIDE_MONTH'])

    def test_malformed_and_date_only_rejected(self):
        for date in ('2026-09-31T00:00:00', '2026-09-01', '',
                     ' 2026-09-01T00:00:00', '09/01/2026'):
            with self.subTest(date=date):
                csv = ('unique_key,created_date\n001,' + date +
                       '\n002,2026-09-02T00:00:00\n').encode()
                self.assertEqual(self.audit(csv), ['SOURCE_CREATED_DATE_INVALID'])

    def test_timezone_inference_prohibited(self):
        for date in ('2026-09-01T00:00:00Z',
                     '2026-09-01T00:00:00+00:00'):
            with self.subTest(date=date):
                csv = ('unique_key,created_date\n001,' + date +
                       '\n002,2026-09-02T00:00:00\n').encode()
                self.assertEqual(self.audit(csv), ['SOURCE_CREATED_DATE_INVALID'])

    def test_missing_created_date_column(self):
        self.assertEqual(self.audit(b'unique_key,borough\n001,Queens\n002,Bronx\n'),
                         ['SOURCE_CREATED_DATE_COLUMN_MISSING'])

    def test_month_contract_rejected(self):
        for value in (True, '2026-9', '2026-13', '2026-09-01', 202609):
            with self.subTest(value=value):
                self.assertEqual(self.audit(b'unique_key\n001\n', month=value),
                                 ['SOURCE_CREATED_MONTH_CONTRACT_INVALID'])

    def test_legacy_unscoped_audit_still_passes(self):
        csv = b'unique_key\n001\n002\n'
        self.assertEqual(self.audit(csv, month=None),
                         ['SOURCE_UNIQUE_KEYS_DISTINCT', 'SOURCE_ROW_COUNT_MATCHED'])

    def test_gate_rejects_out_of_month_even_with_matching_hash(self):
        csv = (b'unique_key,created_date\n'
               b'001,2026-09-30T23:59:59\n'
               b'002,2026-10-01T00:00:00\n')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, candidate, report = (root / 'source.csv',
                                         root / 'candidate.json',
                                         root / 'report.json')
            source.write_bytes(csv)
            candidate.write_text(json.dumps({
                'source_sha256': hashlib.sha256(csv).hexdigest(),
                'source_bytes': len(csv), 'source_rows': 2,
            }), encoding='utf-8')
            with patch.object(gate, 'audit_release', return_value={
                'status': 'HOLD', 'manual_review_required': True,
                'release_authorized': False, 'codes': []
            }):
                self.assertEqual(gate.main([str(candidate), '--source-csv',
                                            str(source), '--created-month', '2026-09',
                                            '--report', str(report)]), 2)
            result = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(result['status'], 'HOLD')
            self.assertFalse(result['release_authorized'])
            self.assertIn('SOURCE_CREATED_DATE_OUTSIDE_MONTH', result['codes'])
            self.assertNotIn('001', report.read_text(encoding='utf-8'))

    def test_gate_explicitly_flags_unscoped_source(self):
        csv = b'unique_key\n001\n002\n'
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, candidate, report = (root / 'source.csv',
                                         root / 'candidate.json',
                                         root / 'report.json')
            source.write_bytes(csv)
            candidate.write_text(json.dumps({
                'source_sha256': hashlib.sha256(csv).hexdigest(),
                'source_bytes': len(csv), 'source_rows': 2,
            }), encoding='utf-8')
            with patch.object(gate, 'audit_release', return_value={
                'status': 'HOLD', 'manual_review_required': True,
                'release_authorized': False, 'codes': []
            }):
                self.assertEqual(gate.main([str(candidate), '--source-csv',
                                            str(source), '--report', str(report)]), 2)
            self.assertIn('SOURCE_CREATED_DATE_MONTH_NOT_BOUND',
                          json.loads(report.read_text(encoding='utf-8'))['codes'])


if __name__ == '__main__':
    unittest.main()
