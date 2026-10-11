"""Private, explicit crosswalk for eight-digit branch/extension identifiers.

Never derive a six-digit UNITID by truncation. An externally sourced mapping
is only review-ready with separate identity, vintage and verification evidence.
This module does not authenticate evidence, establish accreditation or publish.
"""
from __future__ import annotations

from datetime import date
from collections.abc import Mapping, Sequence
from urllib.parse import urlsplit
import re

_ID6 = re.compile(r'^[0-9]{6}$')
_ID8 = re.compile(r'^[0-9]{8}$')
_CAMPUS = re.compile(r'^[A-Za-z0-9_.:-]{1,80}$')
_STATES = frozenset({'unresolved', 'independently_verified', 'rejected'})


def _iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _source_url(value):
    if not isinstance(value, str) or any(c.isspace() or ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ''
        return (parsed.scheme == 'https' and host.endswith('.gov') and host != '.gov'
                and not parsed.username and not parsed.password and parsed.port in (None, 443))
    except ValueError:
        return False


def reconcile_branch_identity(*, raw_id, source_system, status='unresolved',
                              unitid=None, campus_id=None, source_url=None,
                              reporting_year=None, verification_reference=None,
                              verification_date=None):
    """Return a private crosswalk decision; unknown remains explicitly unknown.

    The source-specific eight-digit identifier is never treated as a UNITID.
    Independent verification must be evidenced before mapping is usable; a
    reference string alone is not proof of independent authentication.
    """
    if not isinstance(raw_id, str) or not _ID8.fullmatch(raw_id):
        raise ValueError('Branch/extension identifier must be an exact eight-digit string')
    if not isinstance(source_system, str) or not source_system.strip():
        raise ValueError('Source namespace required')
    if status not in _STATES:
        raise ValueError('Invalid crosswalk status')
    if status == 'independently_verified':
        if not isinstance(unitid, str) or not _ID6.fullmatch(unitid):
            raise ValueError('Verified mapping requires an explicit six-digit UNITID')
        if not isinstance(campus_id, str) or not _CAMPUS.fullmatch(campus_id):
            raise ValueError('Verified mapping requires separate campus identifier')
        if (not _source_url(source_url) or isinstance(reporting_year, bool)
                or not isinstance(reporting_year, int) or not 1990 <= reporting_year <= 2100
                or not isinstance(verification_reference, str)
                or not verification_reference.strip() or not _iso_date(verification_date)):
            raise ValueError('Verified mapping requires source vintage and review evidence')
    elif any(value is not None for value in (unitid, campus_id, verification_reference, verification_date)):
        raise ValueError('Unresolved/rejected mappings cannot assert normalized identities or verification')
    if source_url is not None and not _source_url(source_url):
        raise ValueError('Invalid source URL')
    if reporting_year is not None and (isinstance(reporting_year, bool)
            or not isinstance(reporting_year, int) or not 1990 <= reporting_year <= 2100):
        raise ValueError('Invalid reporting year')
    return {
        'raw_source_id': raw_id, 'source_system': source_system,
        'status': status, 'unitid': unitid, 'campus_id': campus_id,
        'source_url': source_url, 'reporting_year': reporting_year,
        'verification_reference': verification_reference,
        'verification_date': verification_date,
        'crosswalk_review_ready': status == 'independently_verified',
        'accreditation_verified': False,
        'publication_status': 'DO_NOT_PUBLISH',
        'public_export_allowed': False,
        'admissions_probability': None,
    }


def audit_branch_crosswalks(rows):
    """Fail on ambiguous duplicate source identities; never infer a mapping."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise ValueError('Expected crosswalk rows')
    seen = set()
    reviewed = 0
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError('Crosswalk rows must be mappings')
        expected = reconcile_branch_identity(
            raw_id=row.get('raw_source_id'), source_system=row.get('source_system'),
            status=row.get('status'), unitid=row.get('unitid'), campus_id=row.get('campus_id'),
            source_url=row.get('source_url'), reporting_year=row.get('reporting_year'),
            verification_reference=row.get('verification_reference'),
            verification_date=row.get('verification_date'))
        key = (expected['source_system'], expected['raw_source_id'])
        if key in seen:
            raise ValueError('Duplicate source-scoped branch identity')
        seen.add(key)
        reviewed += expected['crosswalk_review_ready']
    return {'source_identity_count': len(seen), 'review_ready_count': reviewed,
            'unresolved_or_rejected_count': len(seen) - reviewed,
            'publication_status': 'DO_NOT_PUBLISH', 'public_export_allowed': False}
