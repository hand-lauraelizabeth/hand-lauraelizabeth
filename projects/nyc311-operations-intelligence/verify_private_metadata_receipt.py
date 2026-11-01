"""Offline, read-only integrity check for a PRIVATE NYC 311 metadata acquisition.

Checks bytes against the capture receipt and reruns the pinned schema contract.
Does not attest publisher origin, reconcile request rows, clear disclosure, or
approve publication. Never upload the raw JSON or receipt to a public repo.
"""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import stat

from source_metadata_contract import MetadataContractError, validate_metadata

SOURCE_URL = 'https://data.cityofnewyork.us/api/views/erm2-nwe9.json'
MAX_BODY_BYTES = 8 * 1024 * 1024
MAX_RECEIPT_BYTES = 128 * 1024


class VerificationError(ValueError):
    """Private acquisition does not pass independent offline verification."""


def _reject_duplicate_json_keys(pairs):
    """Reject ambiguous JSON object members at every nesting level."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _read_private(path, max_bytes):
    path = Path(path)
    if os.name != 'posix':
        raise VerificationError('PRIVATE_FILE_MODE_UNVERIFIABLE')
    if path.is_symlink() or not path.is_file():
        raise VerificationError('MISSING_OR_SYMLINK_FILE')
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise VerificationError('PRIVATE_FILE_PERMISSIONS_UNSAFE')
    parent = path.parent.resolve()
    if stat.S_IMODE(parent.stat().st_mode) & 0o077:
        raise VerificationError('PRIVATE_DIRECTORY_PERMISSIONS_UNSAFE')
    if any((ancestor / '.git').exists() for ancestor in (parent, *parent.parents)):
        raise VerificationError('PRIVATE_FILE_INSIDE_GIT_CHECKOUT')
    with path.open('rb') as handle:
        data = handle.read(max_bytes + 1)
    if not data or len(data) > max_bytes:
        raise VerificationError('PRIVATE_FILE_SIZE_OUT_OF_BOUNDS')
    return data


def verify_pair(raw_path, receipt_path):
    """Return a non-attesting summary, never raw data or receipt content."""
    raw_path, receipt_path = Path(raw_path), Path(receipt_path)
    if (raw_path.parent.resolve() != receipt_path.parent.resolve()
            or not raw_path.name.startswith('nyc311_metadata_')
            or not raw_path.name.endswith('_raw.json')
            or receipt_path.name != raw_path.name[:-9] + '_receipt.json'):
        raise VerificationError('MISMATCHED_RECEIPT_PAIR')
    raw = _read_private(raw_path, MAX_BODY_BYTES)
    receipt_bytes = _read_private(receipt_path, MAX_RECEIPT_BYTES)
    try:
        receipt = json.loads(receipt_bytes.decode('utf-8'),
                             object_pairs_hook=_reject_duplicate_json_keys)
        metadata = json.loads(raw.decode('utf-8'),
                              object_pairs_hook=_reject_duplicate_json_keys)
    except (ValueError, UnicodeError) as exc:
        raise VerificationError('INVALID_JSON') from exc
    if not isinstance(receipt, dict):
        raise VerificationError('INVALID_RECEIPT_OBJECT')
    if (receipt.get('record_type') != 'private_http_metadata_acquisition'
            or receipt.get('source_url') != SOURCE_URL
            or receipt.get('http_status') != 200
            or receipt.get('content_type') != 'application/json'):
        raise VerificationError('RECEIPT_SOURCE_OR_HTTP_MISMATCH')
    if receipt.get('raw_body_bytes') != len(raw) or receipt.get('raw_body_sha256') != hashlib.sha256(raw).hexdigest():
        raise VerificationError('RAW_BODY_DIGEST_OR_LENGTH_MISMATCH')
    for flag in ('publisher_origin_authenticated', 'september_csv_reconciled',
                 'disclosure_approved', 'publication_authorized'):
        if receipt.get(flag) is not False:
            raise VerificationError('UNSUPPORTED_RELEASE_OR_ORIGIN_CLAIM')
    try:
        captured = datetime.fromisoformat(receipt['captured_at_utc'])
        if captured.tzinfo is None or captured.utcoffset().total_seconds() != 0:
            raise ValueError('not UTC')
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationError('INVALID_CAPTURE_TIMESTAMP') from exc
    try:
        schema = validate_metadata(metadata)
    except MetadataContractError as exc:
        raise VerificationError('SCHEMA_CONTRACT_FAILED') from exc
    for key, expected in (
        ('dataset_id', schema['view_id']),
        ('required_schema_sha256', schema['required_schema_sha256']),
        ('required_field_count', schema['required_field_count']),
        ('observed_metadata_columns', schema['publisher_column_count']),
    ):
        if receipt.get(key) != expected:
            raise VerificationError('SCHEMA_RECEIPT_MISMATCH:' + key)
    return {
        'offline_pair_integrity_verified': True,
        'raw_body_bytes': len(raw),
        'raw_body_sha256': hashlib.sha256(raw).hexdigest(),
        'required_field_count': schema['required_field_count'],
        'observed_metadata_columns': schema['publisher_column_count'],
        'publisher_origin_authenticated': False,
        'september_csv_reconciled': False,
        'disclosure_approved': False,
        'publication_authorized': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify_pair(args.raw, args.receipt), sort_keys=True))


if __name__ == '__main__':
    main()
