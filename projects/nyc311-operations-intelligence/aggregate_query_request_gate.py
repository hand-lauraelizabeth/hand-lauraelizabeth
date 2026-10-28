"""Fail-closed NYC 311 query-request provenance *syntax* challenge.

This only checks claimed URL strings, not server response provenance, cache
consistency, or disclosure safety. Keep official source records private.
"""
from urllib.parse import parse_qsl, urlsplit

from aggregate_query_variant_gate import HOLD, VERIFIED, audit

ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
MONTH = ("created_date >= '2026-09-01T00:00:00' AND "
         "created_date < '2026-10-01T00:00:00'")
COUNT_SELECT = "count(*) as records,count(distinct unique_key) as distinct_keys"


def _parse(url):
    if not isinstance(url, str) or len(url) > 4096:
        raise ValueError("invalid URL")
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "data.cityofnewyork.us"
            or parts.path != "/resource/erm2-nwe9.json"
            or parts.fragment or not parts.query):
        raise ValueError("unexpected endpoint")
    pairs = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    if not pairs or len(pairs) != len(set(key for key, _ in pairs)):
        raise ValueError("missing or repeated parameter")
    if any(not key.startswith("$") for key, _ in pairs):
        raise ValueError("unexpected parameter")
    return dict(pairs)


def _check(url, dimensions=None):
    params = _parse(url)
    if dimensions is None:
        if params != {"$select": COUNT_SELECT, "$where": MONTH}:
            raise ValueError("unexpected cohort query")
        return None
    if dimensions == 2:
        select = "borough,agency,count(*) as n"
        group = "borough,agency"
        orders = {"borough,agency", "agency,borough"}
    elif dimensions == 3:
        select = "borough,agency,status,count(*) as n"
        group = "borough,agency,status"
        orders = {"borough,agency,status", "status,borough,agency"}
    else:
        raise ValueError("unsupported dimensions")
    allowed = {"$select", "$where", "$group", "$order", "$limit", "$offset"}
    if set(params) - allowed or not (allowed - {"$offset"}).issubset(params):
        raise ValueError("unexpected or missing query parameter")
    if (params["$select"] != select or params["$where"] != MONTH
            or params["$group"] != group or params["$order"] not in orders
            or params["$limit"] != "50000"
            or params.get("$offset", "0") != "0"):
        raise ValueError("query semantics not on reviewed allowlist")
    return params["$order"]


def audit_with_requests(metadata_before, metadata_after, cohort,
                        pairs_primary, pairs_alternate,
                        triples_primary, triples_alternate, urls):
    """Validate claimed URLs before arithmetic audit; always retain HOLD.

    urls is a dict with cohort, pairs_primary, pairs_alternate,
    triples_primary, triples_alternate. The caller still must establish that
    each response actually came from the claimed URL and same source version.
    """
    try:
        if not isinstance(urls, dict) or set(urls) != {
            "cohort", "pairs_primary", "pairs_alternate",
            "triples_primary", "triples_alternate"
        }:
            raise ValueError("missing or unexpected request")
        _check(urls["cohort"])
        p1 = _check(urls["pairs_primary"], 2)
        p2 = _check(urls["pairs_alternate"], 2)
        t1 = _check(urls["triples_primary"], 3)
        t2 = _check(urls["triples_alternate"], 3)
        if p1 == p2 or t1 == t2:
            raise ValueError("variants not independent")
    except (ValueError, TypeError, AttributeError):
        return [HOLD, "QUERY_REQUEST_EVIDENCE_INVALID"]
    codes = set(audit(metadata_before, metadata_after, cohort,
                      pairs_primary, pairs_alternate,
                      triples_primary, triples_alternate))
    return sorted(codes)
