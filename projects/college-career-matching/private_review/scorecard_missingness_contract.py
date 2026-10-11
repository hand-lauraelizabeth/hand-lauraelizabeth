"""Preserve College Scorecard NA/PS/null/omitted distinctions in private ingestion.

The Scorecard's NA means *not available*, not necessarily not applicable;
PS means privacy-suppressed. Both are unknown for downstream filtering but
retain separate source statuses. Neither can be coerced to zero, and no
records may be published from this structural normalization alone.
"""
from __future__ import annotations

from copy import deepcopy

from scorecard_page_contract import normalize_scorecard_page

MISSING_CODES = {'NA': 'not_available_unspecified', 'PS': 'privacy_suppressed'}


def normalize_scorecard_page_preserving_missingness(*, response, enrollment_year,
                                                     field_years, release_date,
                                                     collection_period, source_url):
    """Normalize one staged page without losing source missingness semantics.

    This adapter is intentionally separate from the strict official-source
    field contract. It records source_missingness *after* core validation,
    leaving the private publication gate and evidence schema unchanged.
    """
    if not isinstance(response, dict) or not isinstance(response.get('results'), list):
        raise ValueError('Expected staged Scorecard page')
    staged = deepcopy(response)
    missingness = {}
    expected = ('school.ownership', 'school.locale', f'{enrollment_year}.student.size')
    for index, row in enumerate(staged['results']):
        if not isinstance(row, dict):
            raise ValueError('Expected institution row')
        for field in expected:
            if field not in row:
                state = 'not_returned'
            elif row[field] is None:
                state = 'null'
            elif isinstance(row[field], str) and row[field] in MISSING_CODES:
                state = MISSING_CODES[row[field]]
                row[field] = None
            else:
                state = 'provided'
            missingness[(index, field)] = state
    result = normalize_scorecard_page(
        response=staged, enrollment_year=enrollment_year,
        field_years=field_years, release_date=release_date,
        collection_period=collection_period, source_url=source_url)
    # Normalizer produces exactly three field records per institution in
    # control, locale, undergraduate enrollment order; index by variable.
    for index, row in enumerate(response['results']):
        unitid = str(row['id']).zfill(6)
        for record in result['records'][index * 3: index * 3 + 3]:
            if record['unitid'] != unitid:
                raise ValueError('Unexpected evidence order')
            source_state = missingness[(index, record['source_variable'])]
            if source_state != 'provided' and record['status'] != 'unknown':
                raise ValueError('Missing source value cannot be provided')
            record['source_data_status'] = source_state
            record['source_missing_code'] = {
                'not_available_unspecified': 'NA',
                'privacy_suppressed': 'PS',
            }.get(source_state)
            record['privacy_suppressed'] = source_state == 'privacy_suppressed'
            record['publication_status'] = 'DO_NOT_PUBLISH'
            record['public_export_allowed'] = False
            record['independently_verified'] = False
    result['publication_status'] = 'DO_NOT_PUBLISH'
    result['public_export_allowed'] = False
    result['independently_verified'] = False
    return result
