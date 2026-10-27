"""Acquire a private, reproducible NYC 311 month cohort; never publish row data.

This utility uses the publisher's SODA 2 API and records source metadata
before and after an ordered paginated export. A matching receipt is necessary
for downstream QA, but does NOT establish a transactional/immutable snapshot.
The resulting CSV and receipt must remain in private storage.
"""
import argparse
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


def fetch_json(url, *, opener=urlopen):
    with opener(url, timeout=90) as response:
        data = response.read()
    return json.loads(data.decode("utf-8"))


def month_bounds(month):
    if not isinstance(month, str) or not re.fullmatch(r"\\d{4}-\\d{2}", month):
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

    def metadata():
        obj = fetch(meta_url)
        stamp = obj.get("rowsUpdatedAt") if isinstance(obj, dict) else None
        if type(stamp) is not int or stamp <= 0:
            raise ValueError("Publisher source-update timestamp unavailable")
        return stamp

    def counts():
        obj = fetch(count_url)
        if not isinstance(obj, list) or len(obj) != 1:
            raise ValueError("Unexpected publisher count response")
        try:
            n = int(obj[0]["records"])
            k = int(obj[0]["distinct_keys"])
        except (KeyError, TypeError, ValueError):
            raise ValueError("Invalid publisher count response") from None
        if n <= 0 or k != n:
            raise ValueError("Invalid or nonunique publisher cohort")
        return n

    before_update = metadata()
    expected = counts()
    if verified_at is None:
        verified_at = dt.datetime.now(dt.timezone.utc).isoformat()
    seen = set()
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
                                    lineterminator="\\n")
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
                    if not isinstance(record.get("created_date"), str):
                        raise ValueError("Missing publisher created_date")
                    if any(not isinstance(record.get(f, ""), str) for f in FIELDS):
                        raise ValueError("Invalid publisher field type")
                    writer.writerow({f: record.get(f, "") for f in FIELDS})
                rows += len(page)
                pages += 1
            output.flush()
            os.fsync(output.fileno())
        if rows != expected or len(seen) != expected:
            raise ValueError("Publisher row/key count mismatch")
        if metadata() != before_update or counts() != expected:
            raise ValueError("Publisher source changed during export")
        sha = hashlib.sha256()
        with temp_csv.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                sha.update(chunk)
        receipt = {
            "dataset": DATASET, "reporting_month": month,
            "publisher": BASE + "/d/" + DATASET,
            "metadata_url": meta_url, "count_query_url": count_url,
            "where": predicate, "ordered_by": "unique_key ASC",
            "fields": list(FIELDS), "rows": rows, "distinct_keys": len(seen),
            "pages": pages, "page_size": page_size,
            "publisher_rows_updated_at": before_update,
            "csv_sha256": sha.hexdigest(), "verified_at_utc": verified_at,
            "provenance_limit": "Non-atomic paginated public API reads; matching metadata and counts do not prove an immutable publisher snapshot.",
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
        os.replace(temp_csv, csv_path)
        temp_csv = None
        try:
            os.replace(temp_receipt, receipt_path)
            temp_receipt = None
        except Exception:
            csv_path.unlink(missing_ok=True)
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
