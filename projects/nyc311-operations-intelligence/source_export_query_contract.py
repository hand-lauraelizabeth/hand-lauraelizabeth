"""Validate a declared September 2026 NYC 311 CSV export query, offline.

This only validates the query's *shape*. It cannot prove that an HTTP request
was made, that returned bytes came from NYC Open Data, or that a mutable dataset
was stable between an export and a separate aggregate query.
"""
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit

DATASET = 'https://data.cityofnewyork.us/resource/erm2-nwe9.csv'
FIELDS = 'unique_key,created_date,closed_date,agency,borough,complaint_type,status'
MONTH = "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'"
MAX_ROWS = 500_000


def canonical_export_url(*, limit):
    """Build one reproducible URL serialization for audit and fingerprinting.

    The URL's SHA-256 identifies the declared request, never publisher origin
    or the response bytes. Use a separately recorded source-file SHA-256.
    """
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS:
        raise ValueError('invalid export row limit')
    return DATASET + '?' + urlencode({
        '$select': FIELDS,
        '$where': MONTH,
        '$order': 'unique_key ASC',
        '$limit': str(limit),
    })


def check_export_query(url, *, reference_rows):
    """Return redacted HOLD-oriented codes, never source rows or query values."""
    if type(url) is not str or type(reference_rows) is not int or reference_rows < 1:
        return ['SOURCE_QUERY_CONTRACT_INVALID']
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.netloc != 'data.cityofnewyork.us'
                or parts.path != '/resource/erm2-nwe9.csv' or parts.fragment):
            return ['SOURCE_QUERY_ENDPOINT_INVALID']
        pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
        params = dict(pairs)
        if len(pairs) != 4 or set(params) != {'$select', '$where', '$order', '$limit'}:
            return ['SOURCE_QUERY_PARAMETERS_INVALID']
        if (params['$select'] != FIELDS or params['$where'] != MONTH
                or params['$order'] != 'unique_key ASC'):
            return ['SOURCE_QUERY_SCOPE_INVALID']
        raw_limit = params['$limit']
        if (not raw_limit.isascii() or not raw_limit.isdecimal()
                or str(int(raw_limit)) != raw_limit or
                not reference_rows < int(raw_limit) <= MAX_ROWS):
            return ['SOURCE_QUERY_LIMIT_INVALID']
        if url != canonical_export_url(limit=int(raw_limit)):
            return ['SOURCE_QUERY_NONCANONICAL']
    except (ValueError, OverflowError):
        return ['SOURCE_QUERY_CONTRACT_INVALID']
    return ['SOURCE_QUERY_SHAPE_VERIFIED_NOT_PROVENANCE']


def query_fingerprint(url):
    """Fingerprint a reviewed, nonsecret query; not an HTTP/source attestation."""
    return sha256(url.encode('utf-8')).hexdigest()
