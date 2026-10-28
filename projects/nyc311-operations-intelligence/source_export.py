"""Acquire a private, reproducible NYC 311 month cohort; never publish row data.

This utility uses the publisher's SODA 2 API and records source metadata
before and after an ordered paginated export. A matching receipt is necessary
for downstream QA, but does NOT establish a transactional/immutable snapshot.
The resulting CSV and receipt must remain in private storage.
"""
import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from urllib.request import urlopen

DATASET = "erm2-nwe9"
BASE = "https://data.cityofnewyork.us"
FIELDS = ("unique_key", "created_date", "closed_date", "agency",
          "complaint_type", "borough", "status")
PAGE_MAX = 50000
# Socrata floating timestamps are local wall-clock date-times, never dates alone
# or timezone-bearing instants. Seconds and fractional seconds are supported.
FLOATING_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\Z")


def parse_floating_timestamp(value, *, required=False):
    if value is None or value == "":
        if required:
            raise ValueError("Missing publisher created_date")
        return None
    if not isinstance(value, str) or not FLOATING_TIMESTAMP.fullmatch(value):
        raise ValueError("Malformed publisher floating timestamp")
    try:
        return dt.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Malformed publisher floating timestamp") from None


def parse_publisher_count(value):
    """Accept exact nonnegative integer counts, never coerced booleans/floats."""
    if type(value) is int:
        return value
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        return int(value)
    raise ValueError("Invalid publisher count representation")


def validate_utc_verification_time(value):
    """Require a real UTC receipt clock, never a future or naive timestamp."""
    if not isinstance(value, str):
        raise ValueError("Invalid UTC verification timestamp")
    try:
        checked = dt.datetime.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid UTC verification timestamp") from None
    if (checked.tzinfo is None or checked.utcoffset() != dt.timedelta(0)
            or checked > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5)):
        raise ValueError("Invalid UTC verification timestamp")
    return checked


def fetch_json(url, *, opener=urlopen):
    with opener(url, timeout=90) as response:
        data = response.read()
    return json.loads(data.decode("utf-8"))


def month_bounds(month):
    if not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Expected YYYY-MM reporting month")
    try:
        start = dt.date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError("Invalid reporting month") from None
    end = (dt.date(start.year + 1, 1, 1) if start.month == 12
           else dt.date(start.year, start.month + 1, 1))
    return start.isoformat() + "T00:00:00", end.isoformat() + "T00:00:00"


def api_url(path, params=None):
    return BASE + path + ("?" + urlencode(params) if params else "")


def download(month, csv_path, receipt_path, *, page_size=50000,
             fetch=fetch_json, verified_at=None):
    """Download exactly seven columns; fail closed on count/order/source drift.

    This checks internal integrity of a non-atomic series of public API reads,
    NOT official file provenance or completeness at an immutable point in time.
    """
    if type(page_size) is not int or not 1 <= page_size <= PAGE_MAX:
        raise ValueError("Invalid page size")
    lower, upper = month_bounds(month)
    if verified_at is not None:
        validate_utc_verification_time(verified_at)
    csv_path, receipt_path = Path(csv_path), Path(receipt_path)
    if csv_path.resolve() == receipt_path.resolve():
        raise ValueError("CSV and receipt paths must differ")
    if csv_path.exists() or receipt_path.exists():
        raise FileExistsError("Refusing to overwrite an existing source artifact")
    if not csv_path.parent.is_dir() or not receipt_path.parent.is_dir():
        raise ValueError("Output directories must exist")
    predicate = f"created_date >= '{lower}' AND created_date < '{upper}'"
    meta_url = api_url("/api/views/" + DATASET + ".json")
    count_url = api_url("/resource/" + DATASET + ".json", {
        "$select": "count(*) as records, count(distinct unique_key) as distinct_keys",
        "$where": predicate
    })

    aggregate_url = api_url("/resource/" + DATASET + ".json", {
        "$select": "borough,agency,count(*) as n", "$where": predicate,
        "$group": "borough,agency", "$order": "borough,agency",
        "$limit": PAGE_MAX
    })

    three_way_url = api_url("/resource/" + DATASET + ".json", {
        "$select": "borough,agency,status,count(*) as n", "$where": predicate,
        "$group": "borough,agency,status", "$order": "borough,agency,status",
        "$limit": PAGE_MAX
    })

    def official_pairs(expected_rows):
        data = fetch(aggregate_url)
        if not isinstance(data, list) or not data or len(data) >= PAGE_MAX:
            raise ValueError("Invalid or potentially truncated official aggregate")
        pairs = {}
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Malformed official aggregate")
            borough, agency = item.get("borough", ""), item.get("agency", "")
            # SoQL omits null grouping fields in some JSON responses.
            borough = "" if borough is None else borough
            agency = "" if agency is None else agency
            if not isinstance(borough, str) or not isinstance(agency, str):
                raise ValueError("Invalid official aggregate dimension")
            try:
                n = parse_publisher_count(item["n"])
            except (KeyError, TypeError, ValueError):
                raise ValueError("Invalid official aggregate count") from None
            key = (borough, agency)
            if n <= 0 or key in pairs:
                raise ValueError("Duplicate or nonpositive official aggregate")
            pairs[key] = n
        if sum(pairs.values()) != expected_rows:
            raise ValueError("Official aggregate total differs from source count")
        return pairs

    def official_triples(expected_rows):
        """Read full borough/agency/status evidence without logging small cells."""
        data = fetch(three_way_url)
        if not isinstance(data, list) or not data or len(data) >= PAGE_MAX:
            raise ValueError("Invalid or potentially truncated official three-way aggregate")
        triples = {}
        for item in data:
            if not isinstance(item, dict):
                raise ValueError("Malformed official three-way aggregate")
            labels = tuple("" if item.get(dim) is None else item.get(dim, "")
                           for dim in ("borough", "agency", "status"))
            if any(not isinstance(label, str) for label in labels):
                raise ValueError("Invalid official three-way dimension")
            try:
                n = parse_publisher_count(item["n"])
            except (KeyError, TypeError, ValueError):
                raise ValueError("Invalid official three-way count") from None
            if n <= 0 or labels in triples:
                raise ValueError("Duplicate or nonpositive official three-way aggregate")
            triples[labels] = n
        if sum(triples.values()) != expected_rows:
            raise ValueError("Official three-way total differs from source count")
        return triples

    def metadata():
        obj = fetch(meta_url)
        stamp = obj.get("rowsUpdatedAt") if isinstance(obj, dict) else None
        if type(stamp) is not int or stamp <= 0:
            raise ValueError("Publisher source-update timestamp unavailable")
        # A stable update clock is not enough: schema changes can silently
        # alter the meaning of an otherwise arithmetically consistent export.
        expected_types = {
            "unique_key": "text", "created_date": "calendar_date",
            "closed_date": "calendar_date", "agency": "text",
            "complaint_type": "text", "borough": "text", "status": "text"
        }
        if (obj.get("id") != DATASET or obj.get("provenance") != "official"
                or obj.get("publicationStage") != "published"
                or obj.get("assetType") != "dataset"):
            raise ValueError("Publisher schema identity invalid")
        columns = obj.get("columns")
        if not isinstance(columns, list) or not columns:
            raise ValueError("Publisher schema columns invalid")
        observed = {}
        used_ids = set()
        for column in columns:
            if not isinstance(column, dict):
                raise ValueError("Publisher schema column invalid")
            name, cid, kind = (column.get("fieldName"),
                               column.get("id"), column.get("dataTypeName"))
            if (not isinstance(name, str) or not name
                    or type(cid) is not int or cid <= 0
                    or not isinstance(kind, str) or not kind
                    or name in observed or cid in used_ids):
                raise ValueError("Publisher schema column identity invalid")
            observed[name] = (cid, kind)
            used_ids.add(cid)
        if (any(observed.get(name, (None, None))[1] != kind
                for name, kind in expected_types.items())
                or obj.get("rowIdentifierColumnId") != observed["unique_key"][0]):
            raise ValueError("Publisher schema required field invalid")
        signature = tuple(sorted((name, cid, kind)
                                 for name, (cid, kind) in observed.items()))
        return stamp, signature

    def counts():
        obj = fetch(count_url)
        if not isinstance(obj, list) or len(obj) != 1:
            raise ValueError("Unexpected publisher count response")
        try:
            n = parse_publisher_count(obj[0]["records"])
            k = parse_publisher_count(obj[0]["distinct_keys"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid publisher count response") from None
        if n <= 0 or k != n:
            raise ValueError("Invalid or nonunique publisher cohort")
        return n

    before_update, before_schema = metadata()
    expected = counts()
    before_pairs = official_pairs(expected)
    before_triples = official_triples(expected)
    if dict(Counter({pair: sum(n for (b, a, _), n in before_triples.items()
                               if (b, a) == pair)
                     for pair in before_pairs})) != before_pairs:
        raise ValueError("Official three-way and two-way cross-aggregate disagree")
    seen = set()
    local_pairs = Counter()
    local_triples = Counter()
    month_start = dt.datetime.fromisoformat(lower)
    month_end = dt.datetime.fromisoformat(upper)
    rows = 0
    pages = 0
    last_key = None
    temp_csv = temp_receipt = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=csv_path.parent, prefix=".nyc311-source-",
                                         suffix=".csv.tmp", delete=False) as output:
            temp_csv = Path(output.name)
            os.chmod(temp_csv, 0o600)
            writer = csv.DictWriter(output, fieldnames=FIELDS, extrasaction="ignore",
                                    lineterminator="\n")
            writer.writeheader()
            while rows < expected:
                url = api_url("/resource/" + DATASET + ".json", {
                    "$select": ",".join(FIELDS), "$where": predicate,
                    "$order": "unique_key ASC",
                    "$limit": min(page_size, expected - rows),
                    "$offset": rows
                })
                page = fetch(url)
                if not isinstance(page, list) or not page:
                    raise ValueError("Truncated publisher page")
                if len(page) > min(page_size, expected - rows):
                    raise ValueError("Oversized publisher page")
                for record in page:
                    if not isinstance(record, dict):
                        raise ValueError("Malformed publisher row")
                    key = record.get("unique_key")
                    if not isinstance(key, str) or not key:
                        raise ValueError("Missing publisher unique_key")
                    if last_key is not None and key <= last_key:
                        raise ValueError("Duplicate or out-of-order publisher key")
                    if key in seen:
                        raise ValueError("Duplicate publisher unique_key")
                    seen.add(key)
                    last_key = key
                    timestamp = parse_floating_timestamp(record.get("created_date"), required=True)
                    if not month_start <= timestamp < month_end:
                        raise ValueError("Publisher row outside reporting month")
                    # Socrata may omit an unresolved request\'s closed_date or
                    # represent it as JSON null; both mean no closure timestamp.
                    closed = parse_floating_timestamp(record.get("closed_date"))
                    if any(not isinstance(record.get(f, ""), str) for f in FIELDS
                           if f != "closed_date"):
                        raise ValueError("Invalid publisher field type")
                    if record.get("closed_date") is None:
                        record = {**record, "closed_date": ""}
                    local_pairs[(record.get("borough", ""), record.get("agency", ""))] += 1
                    local_triples[(record.get("borough", ""), record.get("agency", ""),
                                   record.get("status", ""))] += 1
                    writer.writerow({f: record.get(f, "") for f in FIELDS})
                rows += len(page)
                pages += 1
            output.flush()
            os.fsync(output.fileno())
        if rows != expected or len(seen) != expected:
            raise ValueError("Publisher row/key count mismatch")
        after_update, after_schema = metadata()
        if (after_update != before_update or after_schema != before_schema
                or counts() != expected):
            raise ValueError("Publisher source changed during export")
        after_pairs = official_pairs(expected)
        if after_pairs != before_pairs:
            raise ValueError("Publisher source aggregates changed during export")
        if dict(local_pairs) != before_pairs:
            raise ValueError("Exported rows disagree with official cross-aggregate")
        after_triples = official_triples(expected)
        if after_triples != before_triples:
            raise ValueError("Official three-way aggregates changed during export")
        if dict(local_triples) != before_triples:
            raise ValueError("Exported rows disagree with official three-way cross-aggregate")
        # Stamp *completed* source checks, not the start of a long paginated
        # acquisition. A caller-supplied UTC clock is only a synthetic test hook.
        if verified_at is None:
            verified_at = dt.datetime.now(dt.timezone.utc).isoformat()
        verified_dt = validate_utc_verification_time(verified_at)
        try:
            source_updated = dt.datetime.fromtimestamp(before_update, dt.timezone.utc)
        except (ValueError, OverflowError, OSError):
            raise ValueError("Invalid publisher source-update clock") from None
        if source_updated > verified_dt + dt.timedelta(minutes=5):
            raise ValueError("Publisher update clock follows verification")
        # Digest only: fine-grained cells remain in private memory, not the receipt.
        aggregate_digest = hashlib.sha256(json.dumps(
            [[b, a, n] for (b, a), n in sorted(before_pairs.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        three_way_digest = hashlib.sha256(json.dumps(
            [[b, a, status, n] for (b, a, status), n in sorted(before_triples.items())],
            separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest()
        sha = hashlib.sha256()
        with temp_csv.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                sha.update(chunk)
        receipt = {
            "dataset": DATASET, "reporting_month": month,
            "publisher": BASE + "/d/" + DATASET,
            "metadata_url": meta_url, "count_query_url": count_url,
            "aggregate_query_url": aggregate_url,
            "aggregate_cells": len(before_pairs),
            "aggregate_sha256": aggregate_digest,
            "cross_aggregate_verified": True,
            "three_way_aggregate_query_url": three_way_url,
            "three_way_aggregate_cells": len(before_triples),
            "three_way_aggregate_sha256": three_way_digest,
            "three_way_cross_aggregate_verified": True,
            "where": predicate, "ordered_by": "unique_key ASC",
            "fields": list(FIELDS), "rows": rows, "distinct_keys": len(seen),
            "pages": pages, "page_size": page_size,
            "publisher_rows_updated_at": before_update,
            "csv_sha256": sha.hexdigest(), "verified_at_utc": verified_at,
            "provenance_limit": "Non-atomic paginated public API reads; matched source cross-aggregates, metadata and counts do not prove an immutable publisher snapshot.",
            "release_status": "HOLD"
        }
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=receipt_path.parent, prefix=".nyc311-receipt-",
                                         suffix=".json.tmp", delete=False) as output:
            temp_receipt = Path(output.name)
            os.chmod(temp_receipt, 0o600)
            json.dump(receipt, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        # Atomic no-clobber publication: os.replace would overwrite an artifact
        # created after the initial existence check. Both temporary files are
        # created in their destination directories, so hard links stay on-device.
        os.link(temp_csv, csv_path)
        try:
            os.link(temp_receipt, receipt_path)
        except Exception:
            # The CSV link belongs to this invocation; remove it if receipt
            # publication fails. Never remove a pre-existing receipt.
            csv_path.unlink()
            raise
        return receipt
    finally:
        if temp_csv is not None:
            temp_csv.unlink(missing_ok=True)
        if temp_receipt is not None:
            temp_receipt.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True)
    parser.add_argument("--csv", required=True)
    parser.add_argument("--receipt", required=True)
    parser.add_argument("--page-size", type=int, default=50000)
    args = parser.parse_args()
    result = download(args.month, args.csv, args.receipt, page_size=args.page_size)
    print(json.dumps({"rows": result["rows"], "pages": result["pages"],
                      "release_status": "HOLD", "receipt": str(args.receipt)}))


if __name__ == "__main__":
    main()
