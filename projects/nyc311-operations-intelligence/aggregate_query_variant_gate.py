"""Private NYC 311 aggregate-query variant consistency gate (publication HOLD).

This is a *challenge* for nontransactional/cached Socrata reads: it compares
independently obtained query-order variants, cross-dimensional marginals,
and publisher metadata. It does not retrieve data or prove an immutable
publisher snapshot. Never place raw small cells or unique keys in reports.
"""
from collections import defaultdict

HOLD = "OFFICIAL_SNAPSHOT_PROVENANCE_AND_DISCLOSURE_REVIEW_PENDING"
VERIFIED = "PRIVATE_QUERY_VARIANTS_ARITHMETICALLY_CONSISTENT"
EXPECTED_ID = "erm2-nwe9"
EXPECTED_ROW_ID = 623546861


def _count(value):
    if type(value) is int and value > 0:
        return value
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        n = int(value)
        if n > 0 and str(n) == value:
            return n
    raise ValueError("invalid positive count")


def _metadata(metadata):
    if not isinstance(metadata, dict):
        raise ValueError("invalid metadata")
    if metadata.get("id") != EXPECTED_ID:
        raise ValueError("wrong dataset")
    if metadata.get("publicationStage") != "published":
        raise ValueError("unpublished dataset")
    if metadata.get("rowIdentifierColumnId") != EXPECTED_ROW_ID:
        raise ValueError("wrong row identity")
    updated = metadata.get("rowsUpdatedAt")
    if type(updated) is not int or updated <= 0:
        raise ValueError("invalid update clock")
    return (metadata["id"], metadata["publicationStage"],
            metadata["rowIdentifierColumnId"], updated)


def _groups(rows, dimensions):
    if not isinstance(rows, list) or not rows:
        raise ValueError("empty or invalid aggregate")
    parsed = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid row")
        key = tuple(row.get(k) for k in dimensions)
        if any(not isinstance(k, str) or not k.strip() for k in key):
            raise ValueError("invalid group")
        if key in parsed:
            raise ValueError("duplicate group")
        parsed[key] = _count(row.get("n"))
    return parsed


def audit(metadata_before, metadata_after, cohort,
          pairs_primary, pairs_alternate, triples_primary, triples_alternate):
    """Return redacted finding codes, never source labels, counts or keys.

    The caller must independently verify that each supplied query used the
    same September created-date predicate, official dataset, and distinct
    ORDER BY. These arguments alone cannot authenticate request provenance.
    """
    codes = {HOLD}
    try:
        before = _metadata(metadata_before)
        after = _metadata(metadata_after)
        if before != after:
            codes.add("PUBLISHER_METADATA_CHANGED")
        if not isinstance(cohort, dict):
            raise ValueError("invalid cohort")
        total = _count(cohort.get("records"))
        distinct = _count(cohort.get("distinct_keys"))
        if total != distinct:
            codes.add("COHORT_KEYS_NOT_UNIQUE")
        pair_a = _groups(pairs_primary, ("borough", "agency"))
        pair_b = _groups(pairs_alternate, ("borough", "agency"))
        triple_a = _groups(triples_primary, ("borough", "agency", "status"))
        triple_b = _groups(triples_alternate, ("borough", "agency", "status"))
        if pair_a != pair_b:
            codes.add("TWO_WAY_QUERY_VARIANTS_DISAGREE")
        if triple_a != triple_b:
            codes.add("THREE_WAY_QUERY_VARIANTS_DISAGREE")
        for triples in (triple_a, triple_b):
            marginal = defaultdict(int)
            for (borough, agency, _status), n in triples.items():
                marginal[(borough, agency)] += n
            for pairs in (pair_a, pair_b):
                if dict(marginal) != pairs:
                    codes.add("CROSS_DIMENSION_MARGINAL_MISMATCH")
        if any(sum(groups.values()) != total for groups in
               (pair_a, pair_b, triple_a, triple_b)):
            codes.add("COHORT_TOTAL_MISMATCH")
        if codes == {HOLD}:
            codes.add(VERIFIED)
    except (ValueError, TypeError, KeyError, OverflowError):
        codes.add("AGGREGATE_EVIDENCE_INVALID")
    return sorted(codes)
