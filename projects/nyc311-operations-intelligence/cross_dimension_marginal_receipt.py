"""Private NYC 311 borough-by-agency public-marginal cross-check (HOLD).

Input: an existing four-query public-marginal receipt plus a separately saved
borough-by-agency aggregate response. This catches cross-dimension errors that
matching citywide totals conceal. No service-request records or identifiers.
Even matching row/column marginals do not prove atomic snapshots, cell
authenticity, source-CSV provenance, or disclosure safety. Never publish on pass.
"""
import argparse
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from official_marginal_receipt import BASE, _count, audit as base_audit

BASE_HOLDS = {
    "source_queries_not_atomic",
    "official_csv_origin_not_authenticated",
    "privacy_and_temporal_release_review_pending",
}
HOLDS = BASE_HOLDS | {
    "cross_query_not_atomic",
    "cross_cells_not_independently_authenticated",
}


def _scope(url, month):
    """Require an exact, bounded, month-matched official SoQL aggregate query."""
    try:
        if type(url) is not str or type(month) is not str or not re.fullmatch(r"\d{4}-\d{2}", month):
            return False
        year, number = map(int, month.split("-"))
        first = dt.date(year, number, 1)
        next_month = dt.date(year + (number == 12), number % 12 + 1, 1)
        where = ("created_date >= '%sT00:00:00' AND "
                 "created_date < '%sT00:00:00'") % (first, next_month)
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.netloc != "data.cityofnewyork.us"
                or parsed.path != "/resource/erm2-nwe9.json" or parsed.fragment):
            return False
        actual = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        return actual == {
            "$select": ["borough, agency, count(*) as records"],
            "$where": [where],
            "$group": ["borough, agency"],
            "$order": ["borough, agency"],
            "$limit": ["1000"],
        }
    except (TypeError, ValueError, OverflowError, AttributeError):
        return False


def _marginal(receipt, dimension):
    """Return one-dimensional public totals by category, or None on invalid data."""
    try:
        q = receipt["queries"][dimension]
        rows = q["rows"]
        if not isinstance(rows, list) or not rows or len(rows) > 1000:
            return None
        out = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {dimension, "records"}:
                return None
            label = row[dimension]
            if type(label) is not str or not label.strip() or label in out:
                return None
            out[label] = _count(row["records"])
        return out
    except (TypeError, ValueError, KeyError):
        return None


def audit(receipt, cross_query):
    """Return diagnostic codes only. Never return counts, labels, or query URLs."""
    issues = set(HOLDS)
    if not isinstance(receipt, dict):
        return sorted(issues | {"invalid_base_receipt"})
    base = set(base_audit(receipt))
    if base - BASE_HOLDS:
        issues.add("base_marginals_invalid")
    borough = _marginal(receipt, "borough") if "base_marginals_invalid" not in issues else None
    agency = _marginal(receipt, "agency") if "base_marginals_invalid" not in issues else None
    if borough is None or agency is None:
        issues.add("base_marginals_invalid")
    if (not isinstance(cross_query, dict) or set(cross_query) != {"url", "rows"}
            or not _scope(cross_query["url"], receipt.get("reporting_month"))):
        return sorted(issues | {"cross_query_scope_invalid"})
    rows = cross_query["rows"]
    if not isinstance(rows, list) or not rows or len(rows) > 1000:
        return sorted(issues | {"cross_response_invalid"})
    by_borough = defaultdict(int)
    by_agency = defaultdict(int)
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"borough", "agency", "records"}:
            return sorted(issues | {"cross_response_invalid"})
        b, a = row["borough"], row["agency"]
        if (type(b) is not str or not b.strip() or type(a) is not str
                or not a.strip() or (b, a) in seen):
            return sorted(issues | {"cross_response_invalid"})
        try:
            n = _count(row["records"])
        except ValueError:
            return sorted(issues | {"cross_response_invalid"})
        seen.add((b, a))
        by_borough[b] += n
        by_agency[a] += n
    if borough is not None and agency is not None:
        if set(by_borough) - set(borough) or set(by_agency) - set(agency):
            issues.add("cross_category_not_in_marginals")
        if set(by_borough) != set(borough) or any(by_borough.get(k) != v for k, v in borough.items()):
            issues.add("cross_borough_marginal_mismatch")
        if set(by_agency) != set(agency) or any(by_agency.get(k) != v for k, v in agency.items()):
            issues.add("cross_agency_marginal_mismatch")
    return sorted(issues)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_four_query_receipt", type=Path)
    p.add_argument("private_cross_query", type=Path)
    args = p.parse_args()
    try:
        base = json.loads(args.private_four_query_receipt.read_text(encoding="utf-8"))
        cross = json.loads(args.private_cross_query.read_text(encoding="utf-8"))
        findings = audit(base, cross)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        findings = sorted(HOLDS | {"unreadable_or_invalid_input"})
    print(json.dumps({"hold": True, "publication_approved": False, "findings": findings}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
