"""Private complete-page Scorecard ingestion preserving source missingness.

Structural checks do not independently verify institutions or authorize publication.
Only synthetic or privately staged API responses should be passed to this module.
"""
from __future__ import annotations

from scorecard_missingness_contract import normalize_scorecard_page_preserving_missingness


def normalize_scorecard_batch_preserving_missingness(*, pages, enrollment_year,
                                                    field_years, release_date,
                                                    collection_period, source_url):
    """Require an exact zero-based snapshot and retain NA/PS/null/omitted/zero."""
    if not isinstance(pages, list) or not 1 <= len(pages) <= 10000:
        raise ValueError('A bounded, nonempty list of pages is required')
    records, seen = [], set()
    expected_total = expected_per_page = None
    for index, page in enumerate(pages):
        normalized = normalize_scorecard_page_preserving_missingness(
            response=page, enrollment_year=enrollment_year, field_years=field_years,
            release_date=release_date, collection_period=collection_period,
            source_url=source_url)
        meta = normalized['pagination']
        if meta['page'] != index:
            raise ValueError('Pages must be ordered, complete and zero-based')
        if index == 0:
            expected_total, expected_per_page = meta['total'], meta['per_page']
            expected_pages = max(1, (expected_total + expected_per_page - 1) // expected_per_page)
            if len(pages) != expected_pages:
                raise ValueError('Missing or extra pages')
        elif meta['total'] != expected_total or meta['per_page'] != expected_per_page:
            raise ValueError('Pagination changed between pages')
        expected_rows = max(0, min(expected_per_page, expected_total - index * expected_per_page))
        if len(page['results']) != expected_rows:
            raise ValueError('Incomplete or oversized page')
        for record in normalized['records']:
            if record['field'] == 'control':
                if record['unitid'] in seen:
                    raise ValueError('Duplicate UNITID across pages')
                seen.add(record['unitid'])
        records.extend(normalized['records'])
    if len(seen) != expected_total or len(records) != expected_total * 3:
        raise ValueError('Incomplete institutional evidence')
    return {'records': records, 'institution_count': len(seen),
            'page_count': len(pages), 'source_total': expected_total,
            'publication_status': 'DO_NOT_PUBLISH',
            'public_export_allowed': False, 'independently_verified': False,
            'admissions_probability': None}
