"""Synthetic offline integrity and privacy regression for NYC 311 receipts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from source_metadata_contract import REQUIRED_TYPES, validate_metadata
from verify_private_metadata_receipt import VerificationError, verify_pair


class ReceiptVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'private'
        self.root.mkdir(mode=0o700)
        self.raw = self.root / 'nyc311_metadata_20261031T190000Z_raw.json'
        self.receipt = self.root / 'nyc311_metadata_20261031T190000Z_receipt.json'
        self.payload = {
            'id': 'erm2-nwe9', 'name': '311 Service Requests from 2020 to Present',
            'columns': [{'fieldName': name, 'dataTypeName': dtype, 'name': name}
                        for name, dtype in REQUIRED_TYPES.items()],
        }
        self.make_pair()

    def make_pair(self):
        data = json.dumps(self.payload, sort_keys=True).encode('utf-8')
        schema = validate_metadata(self.payload)
        manifest = {
            'record_type': 'private_http_metadata_acquisition',
            'source_url': 'https://data.cityofnewyork.us/api/views/erm2-nwe9.json',
            'http_status': 200, 'content_type': 'application/json',
            'captured_at_utc': '2026-10-31T23:00:00+00:00',
            'raw_body_bytes': len(data), 'raw_body_sha256': hashlib.sha256(data).hexdigest(),
            'dataset_id': schema['view_id'],
            'required_schema_sha256': schema['required_schema_sha256'],
            'required_field_count': schema['required_field_count'],
            'observed_metadata_columns': schema['publisher_column_count'],
            'publisher_origin_authenticated': False, 'september_csv_reconciled': False,
            'disclosure_approved': False, 'publication_authorized': False,
        }
        self.raw.write_bytes(data)
        self.receipt.write_text(json.dumps(manifest), encoding='utf-8')
        self.raw.chmod(0o600)
        self.receipt.chmod(0o600)
        return manifest

    def edit_receipt(self, **changes):
        obj = json.loads(self.receipt.read_text())
        obj.update(changes)
        self.receipt.write_text(json.dumps(obj))

    def test_valid_pair_rechecks_schema_and_digest(self):
        r = verify_pair(self.raw, self.receipt)
        self.assertTrue(r['offline_pair_integrity_verified'])
        self.assertEqual(r['required_field_count'], 7)
        self.assertFalse(r['publisher_origin_authenticated'])
        self.assertNotIn('raw_body', r)

    def test_modified_raw_rejected(self):
        self.raw.write_bytes(self.raw.read_bytes() + b' ')
        with self.assertRaisesRegex(VerificationError, 'RAW_BODY_DIGEST_OR_LENGTH_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_modified_digest_rejected(self):
        self.edit_receipt(raw_body_sha256='0'*64)
        with self.assertRaisesRegex(VerificationError, 'RAW_BODY_DIGEST_OR_LENGTH_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_wrong_source_rejected(self):
        self.edit_receipt(source_url='https://example.org/fake.json')
        with self.assertRaisesRegex(VerificationError, 'RECEIPT_SOURCE_OR_HTTP_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_release_claim_rejected(self):
        self.edit_receipt(publication_authorized=True)
        with self.assertRaisesRegex(VerificationError, 'UNSUPPORTED_RELEASE_OR_ORIGIN_CLAIM'):
            verify_pair(self.raw, self.receipt)

    def test_missing_false_origin_flag_rejected(self):
        obj = json.loads(self.receipt.read_text())
        del obj['publisher_origin_authenticated']
        self.receipt.write_text(json.dumps(obj))
        with self.assertRaisesRegex(VerificationError, 'UNSUPPORTED_RELEASE_OR_ORIGIN_CLAIM'):
            verify_pair(self.raw, self.receipt)

    def test_schema_changed_but_digest_updated_still_rejected(self):
        self.payload['columns'][0]['dataTypeName'] = 'number'
        data = json.dumps(self.payload, sort_keys=True).encode('utf-8')
        self.raw.write_bytes(data)
        self.edit_receipt(raw_body_bytes=len(data), raw_body_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(VerificationError, 'SCHEMA_CONTRACT_FAILED'):
            verify_pair(self.raw, self.receipt)

    def test_schema_receipt_mismatch_rejected(self):
        self.edit_receipt(observed_metadata_columns=999)
        with self.assertRaisesRegex(VerificationError, 'SCHEMA_RECEIPT_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_public_permissions_rejected(self):
        self.raw.chmod(0o644)
        with self.assertRaisesRegex(VerificationError, 'PRIVATE_FILE_PERMISSIONS_UNSAFE'):
            verify_pair(self.raw, self.receipt)

    def test_public_directory_rejected(self):
        self.root.chmod(0o755)
        with self.assertRaisesRegex(VerificationError, 'PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE'):
            verify_pair(self.raw, self.receipt)

    def test_symlink_raw_rejected(self):
        link = self.root / 'elsewhere.json'
        self.raw.rename(link)
        self.raw.symlink_to(link)
        with self.assertRaisesRegex(VerificationError, 'MISSING_OR_SYMLINK_FILE'):
            verify_pair(self.raw, self.receipt)

    def test_mismatched_names_rejected(self):
        with self.assertRaisesRegex(VerificationError, 'MISMATCHED_RECEIPT_PAIR'):
            verify_pair(self.raw, self.raw)

    def test_invalid_timestamp_rejected(self):
        self.edit_receipt(captured_at_utc='2026-10-31T23:00:00')
        with self.assertRaisesRegex(VerificationError, 'INVALID_CAPTURE_TIMESTAMP'):
            verify_pair(self.raw, self.receipt)

    def test_malformed_receipt_rejected(self):
        self.receipt.write_text('{bad-json')
        with self.assertRaisesRegex(VerificationError, 'INVALID_JSON'):
            verify_pair(self.raw, self.receipt)

    def test_git_checkout_rejected(self):
        (Path(self.temp.name) / '.git').mkdir()
        with self.assertRaisesRegex(VerificationError, 'PRIVATE_FILE_INSIDE_GIT_CHECKOUT'):
            verify_pair(self.raw, self.receipt)

    def test_duplicate_receipt_key_rejected(self):
        original = self.receipt.read_text(encoding='utf-8')
        duplicate = original.replace(
            '"http_status": 200',
            '"http_status": 200, "http_status": 200', 1)
        self.assertNotEqual(original, duplicate)
        self.receipt.write_text(duplicate, encoding='utf-8')
        with self.assertRaisesRegex(VerificationError, 'DUPLICATE_JSON_KEY'):
            verify_pair(self.raw, self.receipt)

    def test_duplicate_raw_top_level_key_even_with_matching_digest_rejected(self):
        original = self.raw.read_text(encoding='utf-8')
        duplicate = original.replace(
            '"id": "erm2-nwe9"',
            '"id": "erm2-nwe9", "id": "erm2-nwe9"', 1)
        self.assertNotEqual(original, duplicate)
        data = duplicate.encode('utf-8')
        self.raw.write_bytes(data)
        self.edit_receipt(raw_body_bytes=len(data),
                          raw_body_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(VerificationError, 'DUPLICATE_JSON_KEY'):
            verify_pair(self.raw, self.receipt)

    def test_duplicate_nested_metadata_key_even_with_matching_digest_rejected(self):
        original = self.raw.read_text(encoding='utf-8')
        duplicate = original.replace(
            '"dataTypeName": "text"',
            '"dataTypeName": "text", "dataTypeName": "text"', 1)
        self.assertNotEqual(original, duplicate)
        data = duplicate.encode('utf-8')
        self.raw.write_bytes(data)
        self.edit_receipt(raw_body_bytes=len(data),
                          raw_body_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(VerificationError, 'DUPLICATE_JSON_KEY'):
            verify_pair(self.raw, self.receipt)

    def test_nonfinite_receipt_constant_rejected(self):
        original = self.receipt.read_text(encoding='utf-8')
        self.receipt.write_text(original[:-1] + ', "unused_probe": NaN}',
                                encoding='utf-8')
        with self.assertRaisesRegex(VerificationError, 'NONFINITE_JSON_NUMBER'):
            verify_pair(self.raw, self.receipt)

    def test_negative_infinity_receipt_constant_rejected(self):
        original = self.receipt.read_text(encoding='utf-8')
        self.receipt.write_text(original[:-1] + ', "unused_probe": -Infinity}',
                                encoding='utf-8')
        with self.assertRaisesRegex(VerificationError, 'NONFINITE_JSON_NUMBER'):
            verify_pair(self.raw, self.receipt)

    def test_nonfinite_raw_constant_with_matching_digest_rejected(self):
        original = self.raw.read_text(encoding='utf-8')
        data = (original[:-1] + ', "unused_probe": Infinity}').encode('utf-8')
        self.raw.write_bytes(data)
        self.edit_receipt(raw_body_bytes=len(data),
                          raw_body_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(VerificationError, 'NONFINITE_JSON_NUMBER'):
            verify_pair(self.raw, self.receipt)

    def test_numeric_exponent_overflow_with_matching_digest_rejected(self):
        original = self.raw.read_text(encoding='utf-8')
        data = (original[:-1] + ', "unused_probe": 1e999}').encode('utf-8')
        self.raw.write_bytes(data)
        self.edit_receipt(raw_body_bytes=len(data),
                          raw_body_sha256=hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(VerificationError, 'NONFINITE_JSON_NUMBER'):
            verify_pair(self.raw, self.receipt)

    def test_extra_unrelated_metadata_field_accepted(self):
        self.payload['columns'].append({'fieldName':'new_public_column','dataTypeName':'text'})
        self.make_pair()
        self.assertEqual(verify_pair(self.raw, self.receipt)['observed_metadata_columns'], 8)


    def test_undeclared_row_identifier_is_explicitly_unverified(self):
        result = verify_pair(self.raw, self.receipt)
        self.assertFalse(result['row_identifier_unique_key_verified'])

    def test_declared_row_identifier_propagates_from_raw_metadata(self):
        for index, col in enumerate(self.payload['columns']):
            col['id'] = 100 + index
        self.payload['rowIdentifierColumnId'] = 100
        self.make_pair()
        result = verify_pair(self.raw, self.receipt)
        self.assertTrue(result['row_identifier_unique_key_verified'])
        self.assertFalse(result['publisher_origin_authenticated'])

    def test_matching_explicit_row_identifier_claim_accepted(self):
        for index, col in enumerate(self.payload['columns']):
            col['id'] = 100 + index
        self.payload['rowIdentifierColumnId'] = 100
        self.make_pair()
        self.edit_receipt(row_identifier_unique_key_verified=True)
        self.assertTrue(verify_pair(self.raw, self.receipt)['row_identifier_unique_key_verified'])

    def test_false_positive_row_identifier_receipt_rejected(self):
        self.edit_receipt(row_identifier_unique_key_verified=True)
        with self.assertRaisesRegex(VerificationError, 'ROW_IDENTIFIER_RECEIPT_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_false_negative_row_identifier_receipt_rejected(self):
        for index, col in enumerate(self.payload['columns']):
            col['id'] = 100 + index
        self.payload['rowIdentifierColumnId'] = 100
        self.make_pair()
        self.edit_receipt(row_identifier_unique_key_verified=False)
        with self.assertRaisesRegex(VerificationError, 'ROW_IDENTIFIER_RECEIPT_MISMATCH'):
            verify_pair(self.raw, self.receipt)

    def test_nonboolean_row_identifier_claim_rejected(self):
        self.edit_receipt(row_identifier_unique_key_verified='false')
        with self.assertRaisesRegex(VerificationError, 'ROW_IDENTIFIER_RECEIPT_MISMATCH'):
            verify_pair(self.raw, self.receipt)


if __name__ == '__main__':
    unittest.main()
