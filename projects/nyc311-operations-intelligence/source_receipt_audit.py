"""Independent offline check of a private NYC 311 source-export CSV and receipt.

No API access or source rows leave the private machine. A passing audit checks
internal consistency only: it NEVER authenticates NYC's mutable source, proves
an immutable snapshot, clears disclosure risk, or authorizes publication.
"""
import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode

FIELDS = ("unique_key", "created_date", "closed_date", "agency",
          "complaint_type", "borough", "status")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
FLOATING_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\Z")


def parse_source_timestamp(value):
    """Require full timezone-free Socrata floating timestamp, not date-only."""
    if not FLOATING_TIMESTAMP.fullmatch(value):
        raise ValueError("not a floating timestamp")
    return dt.datetime.fromisoformat(value)


def audit(csv_path, receipt_path):
    """Return safe diagnostic codes, not source values or fine-grained counts."""
    codes = set()
    try:
        receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        if not isinstance(receipt, dict):
            raise ValueError("receipt must be an object")
        month = receipt.get("reporting_month")
        if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
            raise ValueError("invalid month")
        start = dt.date.fromisoformat(month + "-01")
        end = (dt.date(start.year + 1, 1, 1) if start.month == 12
               else dt.date(start.year, start.month + 1, 1))
        # Reconstruct the exact publisher queries independently of the exporter.
        # A receipt with altered month, source, or aggregation query must not
        # pass even when its local CSV and digest are internally consistent.
        lower = start.isoformat() + "T00:00:00"
        upper = end.isoformat() + "T00:00:00"
        predicate = f"created_date >= '{lower}' AND created_date < '{upper}'"
        base = "https://data.cityofnewyork.us"
        resource = base + "/resource/erm2-nwe9.json"
        count_query = resource + "?" + urlencode({
            "$select": "count(*) as records, count(distinct unique_key) as distinct_keys",
            "$where": predicate,
        })
        aggregate_query = resource + "?" + urlencode({
            "$select": "borough,agency,count(*) as n", "$where": predicate,
            "$group": "borough,agency", "$order": "borough,agency",
            "$limit": 50000,
        })
        three_way_query = resource + "?" + urlencode({
            "$select": "borough,agency,status,count(*) as n", "$where": predicate,
            "$group": "borough,agency,status", "$order": "borough,agency,status",
            "$limit": 50000,
        })
        # Reconstruct the publisher's closure completeness query independently.
        closure_query = resource + "?" + urlencode({
            "$select": "count(*) as records,count(closed_date) as populated",
            "$where": predicate,
        })
        # Reconstruct the two source checks added after the original audit.
        complaint_query = resource + "?" + urlencode({
            "$select": "complaint_type,count(*) as n", "$where": predicate,
            "$group": "complaint_type", "$order": "complaint_type",
            "$limit": 50000,
        })
        key_query = resource + "?" + urlencode({
            "$select": "unique_key", "$where": predicate,
            "$order": "unique_key ASC",
        })
        checked_at = receipt.get("verified_at_utc")
        if not isinstance(checked_at, str):
            raise ValueError("missing verification timestamp")
        try:
            checked_dt = dt.datetime.fromisoformat(checked_at)
        except ValueError:
            raise ValueError("invalid verification timestamp") from None
        if checked_dt.tzinfo is None or checked_dt.utcoffset() != dt.timedelta(0):
            raise ValueError("verification timestamp must be UTC")
        if (receipt.get("dataset") != "erm2-nwe9"
                or receipt.get("publisher") != "https://data.cityofnewyork.us/d/erm2-nwe9"
                or receipt.get("fields") != list(FIELDS)
                or receipt.get("ordered_by") != "unique_key ASC"
                or receipt.get("cross_aggregate_verified") is not True
                or receipt.get("three_way_cross_aggregate_verified") is not True
                or receipt.get("closure_completeness_verified") is not True
                or receipt.get("closure_completeness_query_url") != closure_query
                or receipt.get("complaint_distribution_verified") is not True
                or receipt.get("key_membership_verified") is not True
                or receipt.get("complaint_query_url") != complaint_query
                or receipt.get("key_membership_query_url") != key_query
                or receipt.get("release_status") != "HOLD"
                or receipt.get("where") != predicate
                or receipt.get("metadata_url") != base + "/api/views/erm2-nwe9.json"
                or receipt.get("count_query_url") != count_query
                or receipt.get("aggregate_query_url") != aggregate_query
                or receipt.get("three_way_aggregate_query_url") != three_way_query):
            raise ValueError("receipt contract mismatch")
        n = receipt.get("rows")
        if (type(n) is not int or n <= 0
                or type(receipt.get("distinct_keys")) is not int
                or receipt["distinct_keys"] != n
                or type(receipt.get("populated_closure_dates")) is not int
                or not 0 <= receipt["populated_closure_dates"] <= n
                or type(receipt.get("missing_closure_dates")) is not int
                or receipt["missing_closure_dates"] != n - receipt["populated_closure_dates"]
                or type(receipt.get("aggregate_cells")) is not int
                or receipt["aggregate_cells"] <= 0
                or type(receipt.get("complaint_aggregate_cells")) is not int
                or not 1 <= receipt["complaint_aggregate_cells"] <= n
                or type(receipt.get("three_way_aggregate_cells")) is not int
                or receipt["three_way_aggregate_cells"] <= 0
                or type(receipt.get("publisher_rows_updated_at")) is not int
                or receipt["publisher_rows_updated_at"] <= 0
                or type(receipt.get("page_size")) is not int
                or not 1 <= receipt["page_size"] <= 50000
                or type(receipt.get("pages")) is not int
                or not ( (n + receipt["page_size"] - 1) // receipt["page_size"]
                         <= receipt["pages"] <= n)):
            raise ValueError("receipt counts invalid")
        if (type(receipt.get("key_membership_pages")) is not int
                or not ((n + receipt["page_size"] - 1) // receipt["page_size"]
                        <= receipt["key_membership_pages"] <= n)):
            raise ValueError("receipt key-membership page count invalid")
        # A receipt cannot have verified a publisher update that occurs
        # after its verification clock. Five minutes allow clock skew only.
        try:
            publisher_updated = dt.datetime.fromtimestamp(
                receipt["publisher_rows_updated_at"], dt.timezone.utc)
        except (ValueError, OverflowError, OSError):
            raise ValueError("invalid publisher update clock") from None
        if (publisher_updated > checked_dt + dt.timedelta(minutes=5)
                or checked_dt > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)):
            raise ValueError("impossible source verification chronology")
        if (not isinstance(receipt.get("csv_sha256"), str)
                or not HEX64.fullmatch(receipt["csv_sha256"])
                or not isinstance(receipt.get("aggregate_sha256"), str)
                or not HEX64.fullmatch(receipt["aggregate_sha256"])
                or not isinstance(receipt.get("three_way_aggregate_sha256"), str)
                or not HEX64.fullmatch(receipt["three_way_aggregate_sha256"])
                or not isinstance(receipt.get("complaint_aggregate_sha256"), str)
                or not HEX64.fullmatch(receipt["complaint_aggregate_sha256"])
                or not isinstance(receipt.get("key_membership_sha256"), str)
                or not HEX64.fullmatch(receipt["key_membership_sha256"])):
            raise ValueError("receipt digests invalid")
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, KeyError):
        return ["INVALID_OR_UNREADABLE_RECEIPT"]

    try:
        with tempfile.TemporaryDirectory(prefix="nyc311-audit-") as scratch:
            snapshot = Path(scratch) / "source.csv"
            digest = hashlib.sha256()
            with Path(csv_path).open("rb") as stream, snapshot.open("wb") as copy:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    copy.write(chunk)
            if digest.hexdigest() != receipt["csv_sha256"]:
                codes.add("CSV_SHA256_MISMATCH")
            pairs = Counter()
            triples = Counter()
            complaints = Counter()
            key_membership = hashlib.sha256()
            seen = set()
            last = None
            rows = 0
            populated_closures = 0
            with snapshot.open("r", encoding="utf-8", newline="") as stream:
                reader = csv.reader(stream, strict=True)
                if tuple(next(reader)) != FIELDS:
                    raise ValueError("CSV header mismatch")
                for row in reader:
                    if len(row) != len(FIELDS):
                        raise ValueError("CSV column mismatch")
                    record = dict(zip(FIELDS, row))
                    key = record["unique_key"]
                    if not key or key in seen or (last is not None and key <= last):
                        codes.add("KEY_DUPLICATE_OR_ORDER_INVALID")
                    seen.add(key)
                    encoded_key = key.encode("utf-8")
                    key_membership.update(len(encoded_key).to_bytes(4, "big"))
                    key_membership.update(encoded_key)
                    last = key
                    try:
                        created = parse_source_timestamp(record["created_date"])
                    except ValueError:
                        codes.add("CREATED_DATE_INVALID")
                    else:
                        if (created.tzinfo is not None or not
                                dt.datetime.combine(start, dt.time.min)
                                <= created < dt.datetime.combine(end, dt.time.min)):
                            codes.add("CREATED_DATE_OUTSIDE_MONTH")
                    if record["closed_date"]:
                        try:
                            parse_source_timestamp(record["closed_date"])
                        except ValueError:
                            codes.add("CLOSED_DATE_INVALID")
                        else:
                            populated_closures += 1
                    complaints[record["complaint_type"]] += 1
                    pairs[(record["borough"], record["agency"])] += 1
                    triples[(record["borough"], record["agency"], record["status"])] += 1
                    rows += 1
            if populated_closures != receipt["populated_closure_dates"]:
                codes.add("CLOSURE_COMPLETENESS_MISMATCH")
            if rows != n or len(seen) != receipt["distinct_keys"]:
                codes.add("ROW_OR_DISTINCT_KEY_COUNT_MISMATCH")
            if key_membership.hexdigest() != receipt["key_membership_sha256"]:
                codes.add("KEY_MEMBERSHIP_SHA256_MISMATCH")
            if len(complaints) != receipt["complaint_aggregate_cells"]:
                codes.add("COMPLAINT_CELL_COUNT_MISMATCH")
            complaint_digest = hashlib.sha256(json.dumps(
                [[label, count] for label, count in sorted(complaints.items())],
                separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")).hexdigest()
            if complaint_digest != receipt["complaint_aggregate_sha256"]:
                codes.add("COMPLAINT_SHA256_MISMATCH")
            if len(pairs) != receipt["aggregate_cells"]:
                codes.add("AGGREGATE_CELL_COUNT_MISMATCH")
            if len(triples) != receipt["three_way_aggregate_cells"]:
                codes.add("THREE_WAY_CELL_COUNT_MISMATCH")
            aggregate_digest = hashlib.sha256(json.dumps(
                [[b, a, count] for (b, a), count in sorted(pairs.items())],
                separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")).hexdigest()
            if aggregate_digest != receipt["aggregate_sha256"]:
                codes.add("AGGREGATE_SHA256_MISMATCH")
            three_way_digest = hashlib.sha256(json.dumps(
                [[b, a, status, count] for (b, a, status), count in sorted(triples.items())],
                separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")).hexdigest()
            if three_way_digest != receipt["three_way_aggregate_sha256"]:
                codes.add("THREE_WAY_SHA256_MISMATCH")
            # The parsed snapshot and the source must still contain identical
            # bytes after the audit; a pathname swap after capture is a HOLD.
            current = hashlib.sha256()
            with Path(csv_path).open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    current.update(chunk)
            if current.digest() != digest.digest():
                codes.add("CSV_CHANGED_DURING_AUDIT")
    except (OSError, UnicodeError, ValueError, csv.Error, OverflowError, StopIteration):
        codes.add("CSV_UNREADABLE_OR_MALFORMED")
    if not codes:
        codes.add("INTERNAL_RECEIPT_CONSISTENCY_VERIFIED")
    codes.add("OFFICIAL_SOURCE_ORIGIN_NOT_AUTHENTICATED")
    codes.add("DISCLOSURE_AND_TEMPORAL_REVIEW_PENDING")
    return sorted(codes)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_csv")
    parser.add_argument("private_receipt")
    args = parser.parse_args(argv)
    codes = audit(args.private_csv, args.private_receipt)
    print(json.dumps({"hold": True, "publication_approved": False,
                      "codes": codes}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
