"""Private field-level audit for Scorecard/IPEDS net-price evidence.

Validates supplied metadata, not the truth of a cited institutional value.
FAFSA application year and dataset release year never substitute for SFA cohort.
Never publishes, predicts admission, or guesses missing years.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlsplit
import re

BANDS = {'0_30k': 1, '30_48k': 2, '48_75k': 3, '75_110k': 4, '110k_plus': 5}
SCOPES = {'PUB': 'public_in_state', 'PRIV': 'private',
          'PROG': 'program_calendar', 'OTHER': 'other_calendar'}
STATES = {'provided', 'unknown', 'missing', 'privacy_suppressed', 'not_applicable'}
OFFICIAL_HOSTS = {'collegescorecard.ed.gov', 'nces.ed.gov', 'data.ed.gov'}

def _official_url(url):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        return False
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and p.hostname in OFFICIAL_HOSTS and not p.username and not p.password and p.port in (None, 443) and not p.fragment
    except ValueError:
        return False

def _year(y):
    return isinstance(y, int) and not isinstance(y, bool) and 2009 <= y <= 2100

def _academic_year(s):
    if not isinstance(s, str):
        return False
    m = re.fullmatch(r'(20\d{2})-(\d{2})', s)
    return bool(m and int(m[2]) == (int(m[1]) + 1) % 100)

def audit_net_price_field(row):
    """Validate field metadata and return an explicitly nonpublishing audit."""
    keys = {'unitid', 'source_variable', 'income_band', 'institution_control',
            'residency_scope', 'status', 'value', 'metric_year', 'sfa_cohort_year',
            'collection_period', 'source_release_date', 'dictionary_url',
            'cohort_map_url', 'verified_cohort_map', 'review_reference'}
    if not isinstance(row, dict) or set(row) != keys:
        raise ValueError('Explicit field-level metadata required; no latest-year inference')
    if not isinstance(row['unitid'], str) or not re.fullmatch(r'\d{6}', row['unitid']):
        raise ValueError('UNITID must be six digits')
    if row['income_band'] not in BANDS or row['status'] not in STATES:
        raise ValueError('Invalid income band or value state')
    match = re.fullmatch(r'NPT4([1-5])_(PUB|PRIV|PROG|OTHER)', row['source_variable'] or '')
    if not match or int(match[1]) != BANDS[row['income_band']]:
        raise ValueError('Official net-price variable must match income band')
    scope = match[2]
    if row['institution_control'] not in {'public', 'private_nonprofit', 'private_for_profit'}:
        raise ValueError('Control must be explicit')
    if (scope == 'PUB') != (row['institution_control'] == 'public'):
        raise ValueError('Public/private net-price metric scope mismatch')
    if row['residency_scope'] != ('in_state' if scope == 'PUB' else 'not_applicable'):
        raise ValueError('Public net-price requires in-state residency scope')
    if not _year(row['metric_year']) or not _academic_year(row['collection_period']):
        raise ValueError('Metric year and academic-year collection period required')
    if row['sfa_cohort_year'] is not None and not _academic_year(row['sfa_cohort_year']):
        raise ValueError('Malformed SFA cohort year')
    if not all(_official_url(row[k]) for k in ('dictionary_url', 'cohort_map_url')):
        raise ValueError('Official dictionary and cohort-map citations required')
    try:
        if not isinstance(row['source_release_date'], str):
            raise ValueError
        date.fromisoformat(row['source_release_date'])
    except ValueError:
        raise ValueError('Release date must be ISO formatted') from None
    if row['status'] == 'provided':
        if isinstance(row['value'], bool) or not isinstance(row['value'], (int, float)) or not 0 <= row['value'] < float('inf'):
            raise ValueError('Provided net price must be finite nonnegative numeric')
    elif row['value'] is not None:
        raise ValueError('Unknown/suppressed/missing values cannot become zero')
    if not isinstance(row['verified_cohort_map'], bool):
        raise ValueError('Review flag must be explicit boolean')
    if row['verified_cohort_map'] and (not row['sfa_cohort_year'] or not isinstance(row['review_reference'], str) or not row['review_reference'].strip()):
        raise ValueError('Cohort-map review requires year and review reference')
    return {'unitid': row['unitid'], 'source_variable': row['source_variable'],
            'metric_year': row['metric_year'], 'sfa_cohort_year': row['sfa_cohort_year'],
            'scope': SCOPES[scope], 'status': row['status'],
            'cohort_map_reviewed': row['verified_cohort_map'],
            'review_evidence_complete': row['status'] == 'provided' and row['verified_cohort_map'],
            'comparison_ready': False, 'independently_verified': False,
            'publication_status': 'DO_NOT_PUBLISH', 'owner_approval': False,
            'admissions_probability': None}
