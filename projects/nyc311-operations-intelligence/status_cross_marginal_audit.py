"""Offline source-QA for NYC 311 borough x agency x status aggregates (HOLD).

Accepts only three independently acquired, month-scoped publisher aggregate
responses. No request-level rows, keys, addresses, small-cell values or source
payloads are printed. Exact arithmetic does not establish a transactional
snapshot, CSV provenance, publication safety or absence of reconstruction.
"""
import argparse
from collections import defaultdict
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

BASE = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
HOLD = {"official_source_queries_not_atomic",
        "official_source_csv_not_authenticated",
        "cross_table_integer_and_temporal_disclosure_pending"}
SHAPES = {
    "three": ("borough,agency,status,count(*) as n",
              "borough,agency,status", "borough,agency,status"),
    "two": ("borough,agency,count(*) as n",
            "borough,agency", "borough,agency"),
    "status": ("status,count(*) as n", "status", "status"),
}
DIMENSIONS = {"three": ("borough", "agency", "status"),
              "two": ("borough", "agency"),
              "status": ("status",)}
MAX_ROWS = 1000


def _expected_where(month):
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("invalid month")
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    end = date(year + (mon == 12), mon % 12 + 1, 1)
    return ("created_date >= '%sT00:00:00' AND "
            "created_date < '%sT00:00:00'") % (start, end)


def _query_ok(url, kind, where):
    try:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.netloc != "data.cityofnewyork.us"
                or parts.path != "/resource/erm2-nwe9.json" or parts.fragment):
            return False
        select, group, order = SHAPES[kind]
        return parse_qs(parts.query, strict_parsing=True) == {
            "$select": [select], "$where": [where],
            "$group": [group], "$order": [order], "$limit": ["50000"]}
    except (TypeError, ValueError, AttributeError):
        return False


def _read_table(payload, kind, where):
    if (not isinstance(payload, dict) or set(payload) != {"url", "rows"}
            or not _query_ok(payload["url"], kind, where)):
        raise ValueError("invalid query scope")
    rows = payload["rows"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError("invalid aggregate size")
    dims = DIMENSIONS[kind]
    expected = set(dims) | {"n"}
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != expected:
            raise ValueError("invalid row schema")
        labels = tuple(row[d] for d in dims)
        if any(type(label) is not str or not label.strip()
               or label != label.strip() for label in labels):
            raise ValueError("invalid dimension label")
        count = row["n"]
        if (type(count) is not str or not re.fullmatch(r"[1-9][0-9]*", count)
                or len(count) > 18 or labels in result):
            raise ValueError("invalid or duplicate aggregate count")
        result[labels] = int(count)
    return result


def audit(three, two, status, *, month="2026-09"):
    """Return redacted codes only. A clean cross-check is ALWAYS HOLD."""
    issues = set(HOLD)
    try:
        where = _expected_where(month)
        three_rows = _read_table(three, "three", where)
        two_rows = _read_table(two, "two", where)
        status_rows = _read_table(status, "status", where)
    except (ValueError, TypeError, KeyError, OverflowError):
        return sorted(issues | {"cross_dimension_input_invalid"})
    by_two = defaultdict(int)
    by_status = defaultdict(int)
    for (borough, agency, state), count in three_rows.items():
        by_two[(borough, agency)] += count
        by_status[(state,)] += count
    if dict(by_two) != two_rows:
        issues.add("cross_dimension_borough_agency_mismatch")
    if dict(by_status) != status_rows:
        issues.add("cross_dimension_status_mismatch")
    if sum(three_rows.values()) != sum(two_rows.values()) or (
            sum(three_rows.values()) != sum(status_rows.values())):
        issues.add("cross_dimension_citywide_total_mismatch")
    if any(count < 10 for count in three_rows.values()):
        issues.add("small_public_three_way_cells_present")
    return sorted(issues)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_three_way_json", type=Path)
    parser.add_argument("private_two_way_json", type=Path)
    parser.add_argument("private_status_json", type=Path)
    parser.add_argument("--month", default="2026-09")
    args = parser.parse_args(argv)
    try:
        inputs = [json.loads(p.read_text(encoding="utf-8")) for p in
                  (args.private_three_way_json, args.private_two_way_json,
                   args.private_status_json)]
        codes = audit(*inputs, month=args.month)
    except (OSError, UnicodeError, ValueError, TypeError):
        codes = sorted(HOLD | {"cross_dimension_input_unreadable"})
    print(json.dumps({"hold": True, "publication_approved": False,
                      "codes": codes}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
