"""Private, HOLD-only coarsened NYC 311 aggregate candidate.

Call with the complete *pre-suppression* month/borough/agency/problem counters
retained in memory during local ingestion. Never coarsen the already-suppressed
JSON output: its omitted small categories make its denominators incomplete.

This generates a candidate for independent privacy review, NOT publication.
It intentionally omits exact quality marginals, raw source checksums, bytes,
suppression counts, identifiers, problem labels and request-level fields.
External marginals, combined cross-tabs and temporal differencing are untested.
"""
import datetime as dt
import re
from collections import Counter

MONTH = re.compile(r"[0-9]{4}-(0[1-9]|1[0-2])\Z")
GRAIN = ("month", "borough", "agency")
SCHEMA = "nyc311-private-coarse-candidate-v1"


def build_candidate(request_counts, closed_counts, *, as_of, min_cell=10):
    """Project complete, private source-grain counters to coarser review cells.

    Fails closed on malformed counters. Caller must retain the original
    counters only in its private environment; neither input is serialized.
    """
    if type(min_cell) is not int or min_cell < 10:
        raise ValueError("Private candidate threshold must be an integer >= 10")
    if not isinstance(as_of, str):
        raise ValueError("Invalid snapshot cutoff")
    try:
        date = dt.date.fromisoformat(as_of)
    except ValueError:
        raise ValueError("Invalid snapshot cutoff") from None
    if date.isoformat() != as_of:
        raise ValueError("Invalid snapshot cutoff")
    if not isinstance(request_counts, (dict, Counter)) or not request_counts:
        raise ValueError("Complete source counters are required")
    if not isinstance(closed_counts, (dict, Counter)):
        raise ValueError("Invalid closure counters")

    def validate_key(key):
        if (not isinstance(key, tuple) or len(key) != 4 or
                any(not isinstance(part, str) or not part or
                    part != part.strip() for part in key)):
            raise ValueError("Invalid source group")
        if not MONTH.fullmatch(key[0]) or key[0] > as_of[:7]:
            raise ValueError("Invalid source month")

    groups, outcomes = Counter(), Counter()
    for key, n in request_counts.items():
        validate_key(key)
        if type(n) is not int or n <= 0:
            raise ValueError("Invalid source count")
        groups[key[:3]] += n
    for key, n in closed_counts.items():
        validate_key(key)
        if key not in request_counts or type(n) is not int or not 0 <= n <= request_counts[key]:
            raise ValueError("Invalid closure count")
        outcomes[key[:3]] += n

    rows = []
    for key, n in sorted(groups.items()):
        if n < min_cell:
            continue
        c = outcomes[key]
        withheld = 0 < c < min_cell or 0 < n - c < min_cell
        rows.append(dict(zip(GRAIN, key),
                         requests=n,
                         closed_with_valid_interval=None if withheld else c))
    return {
        "schema": SCHEMA, "dataset_id": "erm2-nwe9",
        "snapshot_as_of": as_of,
        "rules": {"grain": list(GRAIN), "display_minimum_cell_count": min_cell},
        "aggregates": rows, "publication_approved": False,
    }
