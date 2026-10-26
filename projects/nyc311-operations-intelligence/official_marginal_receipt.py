"""Private source-only reconciliation of four official NYC 311 SoQL aggregate responses.

Inputs are *saved public aggregate responses*, not service-request records.
This detects inconsistent totals/query scopes but cannot prove that separate
live queries observed one atomic source snapshot, nor authenticate a CSV export.
Never print aggregate values or use a clean result as publication clearance.
"""
import argparse
import calendar
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

BASE = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
DIMENSIONS = ("borough", "agency", "status")


def _count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r"(0|[1-9][0-9]*)", value):
        return int(value)
    raise ValueError("invalid aggregate count")


def _scope(url, month, dimension):
    try:
        year, number = map(int, month.split("-"))
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", month):
            return False
        first = dt.date(year, number, 1)
        last = dt.date(year + (number == 12), (number % 12) + 1, 1)
        where = ("created_date >= '%sT00:00:00' AND "
                 "created_date < '%sT00:00:00'") % (first, last)
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.netloc != "data.cityofnewyork.us" or parsed.path != "/resource/erm2-nwe9.json" or parsed.fragment:
            return False
        params = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
        select = ("count(*) as records, count(distinct unique_key) as distinct_keys"
                  if dimension == "cohort" else dimension + ", count(*) as records")
        expected = {"$select": [select], "$where": [where]}
        if dimension != "cohort":
            expected["$group"] = [dimension]
            expected["$order"] = [dimension]
        return params == expected
    except (ValueError, TypeError, AttributeError, OverflowError):
        return False


def audit(receipt):
    """Return risk codes only; never expose counts, categories, or source URLs."""
    issues = {"source_queries_not_atomic", "official_csv_origin_not_authenticated",
              "privacy_and_temporal_release_review_pending"}
    if not isinstance(receipt, dict) or set(receipt) != {"dataset_id", "reporting_month", "queries"}:
        return sorted(issues | {"invalid_receipt_schema"})
    month = receipt["reporting_month"]
    queries = receipt["queries"]
    if receipt["dataset_id"] != "erm2-nwe9" or not isinstance(month, str) or not isinstance(queries, dict) or set(queries) != {"cohort", *DIMENSIONS}:
        return sorted(issues | {"invalid_receipt_schema"})
    totals = {}
    for dimension in ("cohort", *DIMENSIONS):
        query = queries[dimension]
        if not isinstance(query, dict) or set(query) != {"url", "rows"} or not _scope(query["url"], month, dimension):
            issues.add("unverified_or_mismatched_query_scope")
            continue
        rows = query["rows"]
        if not isinstance(rows, list) or not rows or len(rows) > 1000:
            issues.add("invalid_aggregate_response")
            continue
        seen = set()
        subtotal = 0
        valid = True
        for row in rows:
            fields = {"records", "distinct_keys"} if dimension == "cohort" else {dimension, "records"}
            if not isinstance(row, dict) or set(row) != fields:
                valid = False
                break
            if dimension != "cohort":
                label = row[dimension]
                if not isinstance(label, str) or not label.strip() or label in seen:
                    valid = False
                    break
                seen.add(label)
            try:
                subtotal += _count(row["records"])
                if dimension == "cohort":
                    distinct = _count(row["distinct_keys"])
                    if distinct > subtotal:
                        issues.add("distinct_key_count_exceeds_rows")
            except ValueError:
                valid = False
                break
        if not valid or (dimension == "cohort" and len(rows) != 1):
            issues.add("invalid_aggregate_response")
            continue
        if dimension == "cohort":
            totals["distinct"] = distinct
        totals[dimension] = subtotal
    if "cohort" in totals and "distinct" in totals and totals["cohort"] != totals["distinct"]:
        issues.add("cohort_duplicate_or_missing_unique_keys")
    if "cohort" in totals:
        for dimension in DIMENSIONS:
            if dimension in totals and totals[dimension] != totals["cohort"]:
                issues.add("mismatched_" + dimension + "_marginal")
    return sorted(issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_receipt", type=Path)
    args = parser.parse_args()
    try:
        findings = audit(json.loads(args.private_receipt.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        findings = ["unreadable_or_invalid_receipt"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
