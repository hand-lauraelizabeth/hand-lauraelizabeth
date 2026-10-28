"""Fetch and challenge live official NYC 311 aggregates without logging source rows.

Publication remains on HOLD: a successful check is not a transactional
snapshot, a seven-field CSV/key audit, or disclosure approval.
"""
import json
import ssl
from urllib.request import build_opener, HTTPSHandler, HTTPRedirectHandler, Request
from urllib.error import HTTPError, URLError

from aggregate_query_request_gate import _check, audit_with_requests
from aggregate_query_variant_gate import VERIFIED

METADATA_URL = "https://data.cityofnewyork.us/api/views/erm2-nwe9.json"
MAX_JSON_BYTES = 2_000_000
HOLD = "OFFICIAL_SNAPSHOT_PROVENANCE_AND_DISCLOSURE_REVIEW_PENDING"
FETCH_ERROR = "PUBLISHER_RESPONSE_BINDING_FAILED"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _official_json(url):
    """Perform an actual TLS GET; reject redirects, oversize, and non-JSON.

    Never include URL query, response body, or exception detail in diagnostics.
    """
    opener = build_opener(_NoRedirect(), HTTPSHandler(context=ssl.create_default_context()))
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "NYC311-Private-Aggregate-Audit/1.0"})
    with opener.open(request, timeout=25) as response:
        if response.status != 200 or response.geturl() != url:
            raise ValueError("unexpected HTTP response")
        content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type not in ("application/json", "application/vnd.socrata.resource+json"):
            raise ValueError("unexpected response content type")
        body = response.read(MAX_JSON_BYTES + 1)
        if len(body) > MAX_JSON_BYTES:
            raise ValueError("response exceeds reviewed bound")
        return json.loads(body.decode("utf-8"))


def _validate_urls(urls):
    if not isinstance(urls, dict) or set(urls) != {
        "cohort", "pairs_primary", "pairs_alternate",
        "triples_primary", "triples_alternate"
    }:
        raise ValueError("unexpected request set")
    _check(urls["cohort"])
    p1 = _check(urls["pairs_primary"], 2)
    p2 = _check(urls["pairs_alternate"], 2)
    t1 = _check(urls["triples_primary"], 3)
    t2 = _check(urls["triples_alternate"], 3)
    if p1 == p2 or t1 == t2:
        raise ValueError("not independent variants")


def audit_live_requests(urls, *, fetch_json=None):
    """Validate URLs before GET; fetch exact URLs, bracket with metadata.

    fetch_json is only for isolated synthetic tests; production omits it.
    A consistent result remains on HOLD pending source/key and privacy checks.
    """
    try:
        _validate_urls(urls)
        fetch = _official_json if fetch_json is None else fetch_json
        before = fetch(METADATA_URL)
        cohort_rows = fetch(urls["cohort"])
        if not isinstance(cohort_rows, list) or len(cohort_rows) != 1:
            raise ValueError("cohort shape")
        pair_a = fetch(urls["pairs_primary"])
        pair_b = fetch(urls["pairs_alternate"])
        triple_a = fetch(urls["triples_primary"])
        triple_b = fetch(urls["triples_alternate"])
        after = fetch(METADATA_URL)
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise ValueError("metadata shape")
        codes = set(audit_with_requests(before, after, cohort_rows[0], pair_a,
                                       pair_b, triple_a, triple_b, urls))
        # Publisher aggregate queries are not transactional. Re-read the
        # cohort and one variant per dimension, then bracket with metadata
        # again. Even a matching update timestamp cannot establish an
        # immutable snapshot; any repeated-response drift fails closed.
        cohort_repeat = fetch(urls["cohort"])
        pair_repeat = fetch(urls["pairs_primary"])
        triple_repeat = fetch(urls["triples_primary"])
        final_metadata = fetch(METADATA_URL)
        if (cohort_repeat != cohort_rows or pair_repeat != pair_a
                or triple_repeat != triple_a or final_metadata != after):
            codes.discard(VERIFIED)
            codes.add("PUBLISHER_REPEAT_READ_DRIFT")
        return sorted(codes)
    except (ValueError, TypeError, AttributeError, KeyError, UnicodeError,
            HTTPError, URLError, TimeoutError, OSError, OverflowError):
        return [HOLD, FETCH_ERROR]
