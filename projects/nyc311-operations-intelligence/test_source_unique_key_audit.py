"""Source-free adversarial tests for disk-backed unique-key validation."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import private_release_gate as gate
from source_unique_key_audit import audit_unique_keys


class UniqueKeySourceAuditTests(unittest.TestCase):
    def run_csv(self, data, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'synthetic.csv'
            path.write_bytes(data)
            return audit_unique_keys(path, **kwargs)

    def test_valid_api_header_and_count(self):
        self.assertEqual(self.run_csv(b'unique_key,borough\n123,Queens\n124,Bronx\n', expected_rows=2),
                         ['SOURCE_UNIQUE_KEYS_DISTINCT', 'SOURCE_ROW_COUNT_MATCHED'])

    def test_valid_display_header_and_bom(self):
        self.assertIn('SOURCE_UNIQUE_KEYS_DISTINCT',
                      self.run_csv(b'\xef\xbb\xbfUnique Key,Borough\r\n123,Queens\r\n'))

    def test_duplicate_key(self):
        self.assertEqual(self.run_csv(b'unique_key\n123\n123\n'), ['SOURCE_UNIQUE_KEY_DUPLICATE'])

    def test_leading_zero_key(self):
        self.assertEqual(self.run_csv(b'unique_key\n0123\n'), ['SOURCE_UNIQUE_KEY_INVALID'])

    def test_non_ascii_key(self):
        self.assertEqual(self.run_csv('unique_key\n１２３\n'.encode()), ['SOURCE_UNIQUE_KEY_INVALID'])

    def test_header_alias_collision(self):
        self.assertEqual(self.run_csv(b'unique_key,Unique Key\n123,123\n'), ['SOURCE_CSV_HEADER_INVALID'])

    def test_missing_key_column(self):
        self.assertEqual(self.run_csv(b'borough\nQueens\n'), ['SOURCE_UNIQUE_KEY_COLUMN_MISSING'])

    def test_malformed_row(self):
        self.assertEqual(self.run_csv(b'unique_key,borough\n123\n'), ['SOURCE_CSV_ROW_STRUCTURE_INVALID'])

    def test_unclosed_quote(self):
        self.assertEqual(self.run_csv(b'unique_key,borough\n123,"Queens\n'), ['SOURCE_UNIQUE_KEY_AUDIT_FAILED_CLOSED'])

    def test_wrong_count(self):
        self.assertEqual(self.run_csv(b'unique_key\n123\n', expected_rows=2), ['SOURCE_ROW_COUNT_MISMATCH'])

    def test_invalid_boolean_expected_count(self):
        self.assertEqual(self.run_csv(b'unique_key\n123\n', expected_rows=True), ['SOURCE_ROW_COUNT_CONTRACT_INVALID'])

    def test_empty_source(self):
        self.assertEqual(self.run_csv(b''), ['SOURCE_CSV_HEADER_INVALID'])

    def test_no_data_rows(self):
        self.assertEqual(self.run_csv(b'unique_key\n'), ['SOURCE_CSV_NO_DATA_ROWS'])

    def test_ten_thousand_rows_disk_backed(self):
        data = ('unique_key,borough\n' + ''.join(f'{i},Queens\n' for i in range(100000, 110000))).encode()
        self.assertEqual(self.run_csv(data, expected_rows=10000),
                         ['SOURCE_UNIQUE_KEYS_DISTINCT', 'SOURCE_ROW_COUNT_MATCHED'])

    def test_missing_file(self):
        self.assertEqual(audit_unique_keys('/not-a-real-311-source-file.csv'),
                         ['SOURCE_UNIQUE_KEY_AUDIT_FAILED_CLOSED'])

    def test_release_gate_integration_valid_keys_remains_hold(self):
        self.assert_gate_codes(b'unique_key,borough\n123,Queens\n124,Bronx\n',
                               ['SOURCE_UNIQUE_KEYS_DISTINCT', 'SOURCE_ROW_COUNT_MATCHED'])

    def test_release_gate_integration_duplicate_key_remains_hold(self):
        self.assert_gate_codes(b'unique_key,borough\n123,Queens\n123,Bronx\n',
                               ['SOURCE_UNIQUE_KEY_DUPLICATE'])

    def assert_gate_codes(self, data, expected):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_file, candidate, report = (root / 'source.csv', root / 'candidate.json',
                                            root / 'report.json')
            csv_file.write_bytes(data)
            candidate.write_text(json.dumps({
                'source_sha256': hashlib.sha256(data).hexdigest(),
                'source_bytes': len(data),
                'source_rows': 2,
            }), encoding='utf-8')
            with patch.object(gate, 'audit_release', return_value={
                'status': 'HOLD', 'manual_review_required': True,
                'release_authorized': False, 'codes': []
            }):
                self.assertEqual(gate.main([str(candidate), '--source-csv', str(csv_file),
                                            '--report', str(report)]), 2)
            outcome = json.loads(report.read_text(encoding='utf-8'))
            self.assertEqual(outcome['status'], 'HOLD')
            self.assertFalse(outcome['release_authorized'])
            for code in expected:
                self.assertIn(code, outcome['codes'])
            self.assertNotIn('Queens', report.read_text(encoding='utf-8'))
            self.assertNotIn('123', report.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
