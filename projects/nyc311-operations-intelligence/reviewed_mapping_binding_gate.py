"""Review-only NYC 311 editorial mapping fingerprint gate.

Detects drift from an independently recorded editorial mapping artifact.
A SHA-256 comparison is not an attestation of artifact provenance, does not
authenticate any source snapshot, and never authorizes publication.
No source request counts, fine cells, or identifiers are accepted or emitted.
"""
import hashlib
import json
import re

SCHEMA = 'nyc311-reviewed-mapping-binding-v1'
DATASET = 'erm2-nwe9'
MONTH = '2026-09'
BASE_CODES = {'REVIEWED_ARTIFACT_PROVENANCE_NOT_AUTHENTICATED',
              'SOURCE_COHORT_AND_DISCLOSURE_QA_REQUIRED'}


def _canonical_bytes(candidate):
    """Return a stable editorial mapping serialization; raise on invalid input."""
    if not isinstance(candidate, dict) or set(candidate) != {
            'schema_version', 'dataset_id', 'reporting_month',
            'group_labels', 'agency_to_group'}:
        raise ValueError('invalid mapping fields')
    labels = candidate['group_labels']
    mapping = candidate['agency_to_group']
    if (candidate['schema_version'] != SCHEMA
            or candidate['dataset_id'] != DATASET
            or candidate['reporting_month'] != MONTH
            or not isinstance(labels, list) or len(labels) != 4
            or any(not isinstance(x, str) or not x or x != x.strip()
                   or len(x) > 120 for x in labels)
            or len(set(labels)) != 4
            or not isinstance(mapping, dict) or len(mapping) != 14
            or any(not isinstance(k, str) or not k or k != k.strip()
                   or len(k) > 120 or not isinstance(v, str)
                   or v not in labels for k, v in mapping.items())
            or set(mapping.values()) != set(labels)):
        raise ValueError('invalid mapping values')
    return json.dumps(candidate, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def fingerprint(candidate):
    """For PRIVATE reviewer tooling only. Do not publish fingerprint as proof."""
    return hashlib.sha256(_canonical_bytes(candidate)).hexdigest()


def audit(candidate, independently_recorded_sha256):
    """Compare editorial mapping with a separately obtained artifact digest.

    Digest supplied by the same unverified caller is NOT proof of independent
    review; the result is always HOLD, even when the digests match.
    """
    codes = set(BASE_CODES)
    try:
        actual = fingerprint(candidate)
    except (ValueError, TypeError, OverflowError):
        codes.add('INVALID_MAPPING_BINDING_CONTRACT')
        return {'status': 'HOLD', 'publication_approved': False,
                'codes': sorted(codes)}
    if (not isinstance(independently_recorded_sha256, str)
            or not re.fullmatch(r'[0-9a-f]{64}', independently_recorded_sha256)):
        codes.add('REVIEWED_MAPPING_FINGERPRINT_REQUIRED')
    elif actual != independently_recorded_sha256:
        codes.add('MAPPING_FINGERPRINT_MISMATCH')
    else:
        codes.add('FINGERPRINT_MATCH_NOT_PROVENANCE_PROOF')
    return {'status': 'HOLD', 'publication_approved': False,
            'codes': sorted(codes)}
