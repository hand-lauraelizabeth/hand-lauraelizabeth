"""Private NYC 311 paired-release differencing screen (review-only).

Checks whether two proposed 20-cell September 2026 releases could disclose
small changes via subtraction. This is a necessary-only test: even a clean
result does NOT clear auxiliary-table, repeated-release, or source-level risk.
Never returns group labels, cell values, deltas, or individual identities.
"""
from datetime import datetime, timezone
import re

SCHEMA = 'nyc311-paired-release-difference-v1'
BOROUGHS = ('BRONX', 'BROOKLYN', 'MANHATTAN', 'QUEENS', 'STATEN ISLAND')
BASE_CODES = {'SOURCE_COHORT_NOT_AUTHENTICATED',
              'MAPPING_PROVENANCE_NOT_AUTHENTICATED',
              'AUXILIARY_AND_MULTI_RELEASE_PRIVACY_REVIEW_REQUIRED'}


def _invalid():
    return {'status': 'HOLD', 'publication_approved': False,
            'codes': sorted(BASE_CODES | {'INVALID_PAIRED_RELEASE_CONTRACT'})}


def _read_snapshot(snapshot, groups):
    if not isinstance(snapshot, dict) or set(snapshot) != {
            'as_of', 'source_revision', 'mapping_sha256', 'cells'}:
        raise ValueError('invalid snapshot fields')
    stamp = snapshot['as_of']
    if not isinstance(stamp, str) or not stamp or 'T' not in stamp:
        raise ValueError('invalid time')
    try:
        moment = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('invalid time') from exc
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError('naive time')
    revision = snapshot['source_revision']
    digest = snapshot['mapping_sha256']
    if (not isinstance(revision, str) or not revision.strip() or len(revision) > 128
            or not isinstance(digest, str)
            or re.fullmatch(r'[0-9a-f]{64}', digest) is None):
        raise ValueError('invalid provenance fields')
    rows = snapshot['cells']
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError('invalid cell count')
    values = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'borough', 'group', 'requests'}:
            raise ValueError('invalid cell')
        borough, group, count = row['borough'], row['group'], row['requests']
        if borough not in BOROUGHS or group not in groups or type(count) is not int or count < 0:
            raise ValueError('invalid cell values')
        key = (borough, group)
        if key in values:
            raise ValueError('duplicate cell')
        values[key] = count
    if set(values) != {(b, g) for b in BOROUGHS for g in groups}:
        raise ValueError('missing cell')
    return moment.astimezone(timezone.utc), revision, digest, values


def audit(payload):
    """Always HOLD; identify small paired differences without leaking counts."""
    if not isinstance(payload, dict) or set(payload) != {
            'schema_version', 'dataset_id', 'reporting_month',
            'group_labels', 'minimum_disclosure_delta', 'earlier', 'later'}:
        return _invalid()
    groups = payload['group_labels']
    threshold = payload['minimum_disclosure_delta']
    if (payload['schema_version'] != SCHEMA
            or payload['dataset_id'] != 'erm2-nwe9'
            or payload['reporting_month'] != '2026-09'
            or not isinstance(groups, list) or len(groups) != 4
            or any(not isinstance(g, str) or not g or g != g.strip() or len(g) > 120
                   for g in groups) or len(set(groups)) != 4
            or type(threshold) is not int or threshold < 10):
        return _invalid()
    try:
        early = _read_snapshot(payload['earlier'], groups)
        late = _read_snapshot(payload['later'], groups)
    except (ValueError, TypeError, OverflowError):
        return _invalid()
    e_time, e_rev, e_hash, e_cells = early
    l_time, l_rev, l_hash, l_cells = late
    codes = set(BASE_CODES)
    if e_time >= l_time:
        codes.add('INVALID_SNAPSHOT_ORDER')
    if e_hash != l_hash:
        codes.add('MAPPING_FINGERPRINT_MISMATCH')
        # Different mappings make arithmetic differences incomparable.
        return {'status': 'HOLD', 'publication_approved': False, 'codes': sorted(codes)}
    differences = {key: l_cells[key] - value for key, value in e_cells.items()}
    if any(0 < abs(value) < threshold for value in differences.values()):
        codes.add('SMALL_CELL_DIFFERENCE_EXPOSED')
    if any(value < 0 for value in differences.values()):
        codes.add('NEGATIVE_CELL_DIFFERENCE_REVIEW_REQUIRED')
    if any(value != 0 for value in differences.values()):
        codes.add('CHANGED_PUBLIC_RELEASE_REQUIRES_REVIEW')
        if e_rev == l_rev:
            codes.add('UNCHANGED_SOURCE_REVISION_WITH_CHANGED_COUNTS')
    for borough in BOROUGHS:
        delta = sum(differences[(borough, g)] for g in groups)
        if 0 < abs(delta) < threshold:
            codes.add('SMALL_BOROUGH_MARGINAL_DIFFERENCE_EXPOSED')
    for group in groups:
        delta = sum(differences[(b, group)] for b in BOROUGHS)
        if 0 < abs(delta) < threshold:
            codes.add('SMALL_GROUP_MARGINAL_DIFFERENCE_EXPOSED')
    return {'status': 'HOLD', 'publication_approved': False, 'codes': sorted(codes)}
