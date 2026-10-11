"""Fail-closed private field-level release assessment.

This module never publishes data. It assesses a specific immutable snapshot
for independent field review and separate, version-scoped owner authorization.
Synthetic fixtures only; publishing requires manual deployment review.
"""
from __future__ import annotations

import re
import hashlib
import json
from urllib.parse import urlsplit
from datetime import date
from collections.abc import Mapping, Sequence

_SHA = re.compile(r'^[0-9a-f]{64}$')
_UNITID = re.compile(r'^\d{6}$')
_FIELD = re.compile(r'^[a-z][a-z0-9_]{1,80}$')
_STATES = frozenset({'provided', 'unknown', 'not_applicable', 'privacy_suppressed', 'not_returned'})
_REVIEW = frozenset({'independently_verified', 'reviewed_missing', 'pending', 'rejected'})

def _date(value):
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False

def canonical_evidence_sha256(fields):
    """Bind approval to exact field values, missingness and provenance.

    Order-independent for field records; rejects non-JSON values. The hash is
    an integrity identifier, not evidence of independent verification.
    """
    if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes)):
        raise ValueError('Expected field records')
    try:
        serialized = [json.dumps(record, sort_keys=True, separators=(',', ':'),
                                 ensure_ascii=True, allow_nan=False) for record in fields]
    except (TypeError, ValueError) as exc:
        raise ValueError('Field evidence must be canonical JSON') from exc
    return hashlib.sha256(('[' + ','.join(sorted(serialized)) + ']').encode('utf-8')).hexdigest()

def _source_url(url):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        return False
    try:
        parts = urlsplit(url)
        return (parts.scheme == 'https' and bool(parts.hostname)
                and not parts.username and not parts.password
                and parts.port in (None, 443))
    except ValueError:
        return False

def assess_private_release(*, snapshot, fields, owner_approval=None):
    """Return blockers; missing attestations never imply approval.

    One private record per (UNITID, campus_id, program_id, field).
    Approval must match exact snapshot SHA, version and field set.
    """
    if not isinstance(snapshot, Mapping):
        raise ValueError('Snapshot must be a mapping')
    dataset_id, version, digest = (snapshot.get(k) for k in ('dataset_id', 'version', 'sha256'))
    if (not isinstance(dataset_id, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{2,79}', dataset_id)
            or not isinstance(version, str) or not re.fullmatch(r'v[1-9]\d*', version)
            or not isinstance(digest, str) or not _SHA.fullmatch(digest)
            or snapshot.get('publication_status') != 'DO_NOT_PUBLISH'):
        raise ValueError('Private immutable snapshot metadata required')
    if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes)) or not fields:
        raise ValueError('Nonempty field evidence required')
    blockers, keys, field_names = [], set(), set()
    if canonical_evidence_sha256(fields) != digest:
        blockers.append('snapshot_digest_does_not_match_evidence')
    for idx, record in enumerate(fields):
        if not isinstance(record, Mapping):
            raise ValueError('Field evidence must be a mapping')
        unitid, field = record.get('unitid'), record.get('field')
        if not isinstance(unitid, str) or not _UNITID.fullmatch(unitid):
            raise ValueError('Invalid UNITID')
        if not isinstance(field, str) or not _FIELD.fullmatch(field):
            raise ValueError('Invalid field identifier')
        for optional_id in ('campus_id', 'program_id'):
            value = record.get(optional_id)
            if value is not None and (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,80}', value)):
                raise ValueError('Invalid campus/program identifier')
        key = (unitid, record.get('campus_id'), record.get('program_id'), field)
        if key in keys:
            raise ValueError('Duplicate institution/campus/program/field evidence')
        keys.add(key)
        field_names.add(field)
        state, review = record.get('value_status'), record.get('review_status')
        if state not in _STATES or review not in _REVIEW:
            raise ValueError('Unknown value/review status')
        if state != 'provided' and record.get('value') is not None:
            raise ValueError('Unknown/suppressed/not-applicable field cannot contain a value')
        if state == 'provided' and record.get('value') is None:
            raise ValueError('Provided field must contain a value, including legitimate zero')
        if (not isinstance(record.get('source_system'), str) or not record['source_system'].strip()
                or not _source_url(record.get('source_url'))
                or not _date(record.get('source_release_date'))
                or isinstance(record.get('reporting_year'), bool)
                or not isinstance(record.get('reporting_year'), int)
                or not 1990 <= record['reporting_year'] <= 2100):
            blockers.append(f'field[{idx}]:missing_or_invalid_source_vintage')
        if (record.get('publication_status') != 'DO_NOT_PUBLISH'
                or record.get('public_export_allowed') is not False):
            blockers.append(f'field[{idx}]:not_private')
        if review == 'independently_verified' and state != 'provided':
            blockers.append(f'field[{idx}]:missing_value_requires_reviewed_missing')
        elif review == 'reviewed_missing' and state == 'provided':
            blockers.append(f'field[{idx}]:provided_value_requires_independent_verification')
        elif review in {'pending', 'rejected'}:
            blockers.append(f'field[{idx}]:{review}')
        if review in {'independently_verified', 'reviewed_missing'}:
            if (not isinstance(record.get('verification_reference'), str)
                    or not record['verification_reference'].strip()
                    or not _date(record.get('verification_date'))):
                blockers.append(f'field[{idx}]:missing_independent_review_evidence')
    if not isinstance(owner_approval, Mapping):
        blockers.append('owner_approval_missing')
    else:
        approved = (owner_approval.get('decision') == 'approve_for_release_review'
                    and owner_approval.get('dataset_id') == dataset_id
                    and owner_approval.get('version') == version
                    and owner_approval.get('sha256') == digest
                    and owner_approval.get('fields') == sorted(field_names)
                    and _date(owner_approval.get('decision_date'))
                    and isinstance(owner_approval.get('approval_reference'), str)
                    and bool(owner_approval['approval_reference'].strip()))
        if not approved:
            blockers.append('owner_approval_not_valid_for_snapshot')
    return {'snapshot_id': dataset_id, 'snapshot_version': version,
            'field_count': len(keys), 'fields': sorted(field_names),
            'release_review_ready': not blockers,
            'blockers': blockers, 'publication_status': 'DO_NOT_PUBLISH',
            'automated_publication_performed': False,
            'admissions_probability': None}
