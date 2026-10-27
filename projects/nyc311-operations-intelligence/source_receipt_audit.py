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
        if (receipt.get("dataset") != "erm2-nwe9"
                or receipt.get("publisher") != "https://data.cityofnewyork.us/d/erm2-nwe9"
                or receipt.get("fields") != list(FIELDS)
                or receipt.get("ordered_by") != "unique_key ASC"
                or receipt.get("cross_aggregate_verified") is not True
                or receipt.get("release_status") != "HOLD"):
            raise ValueError("receipt contract mismatch")
        n = receipt.get("rows")
        if (type(n) is not int or n <= 0
                or type(receipt.get("distinct_keys")) is not int
                or receipt["distinct_keys"] != n
                or type(receipt.get("aggregate_cells")) is not int
                or receipt["aggregate_cells"] <= 0
                or type(receipt.get("publisher_rows_updated_at")) is not int
                or receipt["publisher_rows_updated_at"] <= 0):
            raise ValueError("receipt counts invalid")
        if (not isinstance(receipt.get("csv_sha256"), str)
                or not HEX64.fullmatch(receipt["csv_sha256"])
                or not isinstance(receipt.get("aggregate_sha256"), str)
                or not HEX64.fullmatch(receipt["aggregate_sha256"])):
            raise ValueError("receipt digests invalid")
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError, KeyError):
        return ["INVALID_OR_UNREADABLE_RECEIPT"]

    try:
        digest = hashlib.sha256()
        with Path(csv_path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != receipt["csv_sha256"]:
            codes.add("CSV_SHA256_MISMATCH")
        pairs = Counter()
        seen = set()
        last = None
        rows = 0
        with Path(csv_path).open("r", encoding="utf-8", newline="") as stream:
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
                pairs[(record["borough"], record["agency"])] += 1
                rows += 1
        if rows != n or len(seen) != receipt["distinct_keys"]:
            codes.add("ROW_OR_DISTINCT_KEY_COUNT_MISMATCH")
        if len(pairs) != receipt["aggregate_cells"]:
            codes.add("AGGREGATE_CELL_COUNT_MISMATCH")
        aggregate_digest = hashlib.sha256(json.dumps(
            [[b, a, count] for (b, a), count in sorted(pairs.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        if aggregate_digest != receipt["aggregate_sha256"]:
            codes.add("AGGREGATE_SHA256_MISMATCH")
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
