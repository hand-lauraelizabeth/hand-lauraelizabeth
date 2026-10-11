"""Nonpublishing IPEDS ADM score-distribution evidence validator.

IPEDS 2024 Admissions: SAT EBRW/math and ACT composite/sections; do not
report percentiles for fewer than five students. School values, source fields,
and current-cycle testing policies require independent verification.
https://nces.ed.gov/ipeds/use-the-data/download-survey-material/2024/admissions/package_14_102.pdf
"""
from datetime import date
from urllib.parse import urlsplit
import re

METRICS = {'SAT_EBRW': (200, 800, 10), 'SAT_MATH': (200, 800, 10),
           'ACT_COMPOSITE': (1, 36, 1), 'ACT_ENGLISH': (1, 36, 1),
           'ACT_MATH': (1, 36, 1), 'ACT_READING': (1, 36, 1),
           'ACT_SCIENCE': (1, 36, 1)}
STATUSES = {'provided', 'missing', 'unknown', 'privacy_suppressed', 'not_applicable'}
KEYS = {'unitid', 'metric', 'status', 'percentiles', 'reporting_n',
        'source_variable', 'source_url', 'dictionary_url', 'reporting_year',
        'admissions_cohort', 'source_release_date', 'applicant_scope',
        'source_system', 'review_reference'}

def _official(url):
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        return False
    try:
        u = urlsplit(url)
        return (u.scheme == 'https' and u.hostname in {'nces.ed.gov', 'data.ed.gov',
                'collegescorecard.ed.gov'} and not u.username and not u.password
                and u.port in (None, 443) and not u.fragment)
    except ValueError:
        return False

def audit_score_distribution(row):
    """Validate supplied metadata, not institutional truth or publication rights."""
    if not isinstance(row, dict) or set(row) != KEYS:
        raise ValueError('All field-level percentile metadata required')
    if not isinstance(row['unitid'], str) or not re.fullmatch(r'\d{6}', row['unitid']):
        raise ValueError('UNITID must be six digits; no branch truncation')
    if row['metric'] not in METRICS or row['status'] not in STATUSES:
        raise ValueError('Unsupported metric or missingness')
    if row['applicant_scope'] != 'first_time_degree_seeking_undergraduate':
        raise ValueError('First-time undergraduate cohort required')
    if row['source_system'] not in {'IPEDS_ADM', 'COLLEGE_SCORECARD'}:
        raise ValueError('Official source system required')
    if not _official(row['source_url']) or not _official(row['dictionary_url']):
        raise ValueError('Official evidence and dictionary URLs required')
    year = row['reporting_year']
    if isinstance(year, bool) or not isinstance(year, int) or not 1990 <= year <= date.today().year:
        raise ValueError('Valid reporting year required')
    if not isinstance(row['admissions_cohort'], str) or not re.fullmatch(r'Fall 20\d{2}', row['admissions_cohort']):
        raise ValueError('Explicit fall cohort required')
    if abs(int(row['admissions_cohort'][-4:]) - year) > 1:
        raise ValueError('Cohort/reporting-year mismatch')
    try:
        release = date.fromisoformat(row['source_release_date']) if isinstance(row['source_release_date'], str) else None
    except ValueError:
        release = None
    if release is None or release > date.today() or release.year < year:
        raise ValueError('Invalid or future release date')
    if not isinstance(row['source_variable'], str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]{1,79}', row['source_variable']):
        raise ValueError('Traceable source variable required')
    if row['review_reference'] is not None and (not isinstance(row['review_reference'], str) or not row['review_reference'].strip()):
        raise ValueError('Review reference must be nonempty or null')
    n = row['reporting_n']
    if n is not None and (isinstance(n, bool) or not isinstance(n, int) or n < 0):
        raise ValueError('Sample size must be nonnegative integer or unknown')
    pct = row['percentiles']
    if row['status'] == 'provided':
        if not isinstance(pct, dict) or set(pct) != {'p25', 'p50', 'p75'}:
            raise ValueError('All three separately reported percentiles required')
        low, high, step = METRICS[row['metric']]
        vals = [pct[k] for k in ('p25', 'p50', 'p75')]
        if any(isinstance(v, bool) or not isinstance(v, int) or v < low or v > high
               or v % step for v in vals) or vals != sorted(vals):
            raise ValueError('Invalid or nonmonotonic percentile scores')
        if n is not None and n < 5:
            raise ValueError('IPEDS suppresses percentiles for fewer than five')
    elif pct is not None:
        raise ValueError('Unknown or suppressed percentiles must remain null')
    return {'unitid': row['unitid'], 'metric': row['metric'],
            'status': row['status'], 'percentiles': dict(pct) if pct is not None else None,
            'reporting_n': n, 'reporting_year': year,
            'admissions_cohort': row['admissions_cohort'],
            'source_system': row['source_system'], 'source_variable': row['source_variable'],
            'source_url': row['source_url'], 'dictionary_url': row['dictionary_url'],
            'source_release_date': row['source_release_date'],
            'review_reference': row['review_reference'],
            'sample_size_confirmed': n is not None and n >= 5,
            'source_shape_valid': True, 'institution_value_independently_verified': False,
            'current_cycle_testing_policy_verified': False, 'comparison_ready': False,
            'admissions_probability': None, 'admissions_cutoff': None,
            'publication_status': 'DO_NOT_PUBLISH', 'owner_approval': False}
