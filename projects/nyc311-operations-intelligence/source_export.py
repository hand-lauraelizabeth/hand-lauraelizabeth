"""Bounded NYC 311 monthly CSV acquisition for private, offline analysis.

The public repository contains no request-level records. A count-reconciled
export is still not an immutable source snapshot.
"""
import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
FIELDS = ("unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status")

def fetch_json(params):
    headers = {"Accept": "application/json", "User-Agent": "NYC311-Research-Export/1.0"}
    token = os.getenv("SOCRATA_APP_TOKEN")
    if token:
        headers["X-App-Token"] = token
    with urlopen(Request(ENDPOINT + "?" + urlencode(params), headers=headers), timeout=45) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("Expected a source JSON array")
    return data

def month_bounds(month):
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month must be YYYY-MM")
    year, number = map(int, month.split("-"))
    if year < 2020 or year > 9998:
        raise ValueError("month outside supported dataset range")
    start = dt.date(year, number, 1)
    end = dt.date(year + (number == 12), number % 12 + 1, 1)
    return start.isoformat() + "T00:00:00", end.isoformat() + "T00:00:00"

def acquire(month, output_csv, *, transport=fetch_json, page_size=5000,
            max_rows=500000, expected_count=None, now=None):
    if type(page_size) is not int or not 1 <= page_size <= 5000:
        raise ValueError("page_size must be 1..5000")
    if type(max_rows) is not int or max_rows < 1:
        raise ValueError("max_rows must be positive")
    if expected_count is not None and (type(expected_count) is not int or expected_count < 0):
        raise ValueError("expected_count must be nonnegative")
    start, end = month_bounds(month)
    where = f"created_date >= '{start}' AND created_date < '{end}'"
    def count():
        rows = transport({"$select": "count(*) as total", "$where": where})
        if len(rows) != 1 or not isinstance(rows[0], dict):
            raise ValueError("Unexpected source count response")
        try:
            n = int(rows[0]["total"])
        except (ValueError, KeyError, TypeError) as exc:
            raise ValueError("Invalid source count") from exc
        if n < 0 or str(rows[0]["total"]) != str(n):
            raise ValueError("Invalid source count")
        return n
    before = count()
    if before > max_rows:
        raise ValueError("Source count exceeds max_rows")
    if expected_count is not None and before != expected_count:
        raise ValueError("Source count differs from expected_count")
    output = Path(output_csv)
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    if output.exists() or manifest_path.exists():
        raise FileExistsError("Output already exists; use a versioned filename")
    output.parent.mkdir(parents=True, exist_ok=True)
    total, previous_key = 0, None
    missing_optional = Counter()
    with tempfile.TemporaryDirectory(prefix="nyc311-source-", dir=output.parent) as directory:
        partial = Path(directory) / "export.csv"
        with partial.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            while True:
                query = where + (f" AND unique_key > '{previous_key}'" if previous_key else "")
                rows = transport({"$select": ",".join(FIELDS), "$where": query,
                                  "$order": "unique_key ASC", "$limit": page_size})
                if not isinstance(rows, list) or len(rows) > page_size:
                    raise ValueError("Unexpected source page")
                for row in rows:
                    # SODA JSON omits nullable columns rather than returning null.
                    # Keep identity and created_date mandatory; normalize optional
                    # missing/null values to empty CSV cells for downstream QA.
                    if not isinstance(row, dict) or not {"unique_key", "created_date"}.issubset(row):
                        raise ValueError("Missing required source fields")
                    key = row["unique_key"]
                    if not isinstance(key, str) or not re.fullmatch(r"[0-9]+", key):
                        raise ValueError("Invalid numeric-text unique_key")
                    if not isinstance(row["created_date"], str) or not row["created_date"].strip():
                        raise ValueError("Missing or invalid required created_date")
                    if previous_key is not None and key <= previous_key:
                        raise ValueError("Source keys repeated or out of order")
                    normalized = {}
                    for field in FIELDS:
                        value = row.get(field)
                        if value is None:
                            if field in ("unique_key", "created_date"):
                                raise ValueError("Null required source field")
                            missing_optional[field] += 1
                            value = ""
                        if not isinstance(value, str):
                            raise ValueError("Non-text source field: " + field)
                        normalized[field] = value
                    previous_key = key
                    writer.writerow(normalized)
                    total += 1
                    if total > max_rows or total > before:
                        raise ValueError("Page exceeds source count")
                if len(rows) < page_size:
                    break
        after = count()
        if before != after or total != before:
            raise ValueError("Source count changed or incomplete paging")
        with partial.open("rb") as binary:
            digest = hashlib.file_digest(binary, "sha256").hexdigest()
        when = now or dt.datetime.now(dt.timezone.utc)
        manifest = {
            "dataset_id": "erm2-nwe9", "source_endpoint": ENDPOINT,
            "month": month, "where": where, "selected_fields": list(FIELDS),
            "paging": "unique_key ASC (strict numeric-text key ordering)",
            "source_count_before": before, "source_count_after": after,
            "rows_exported": total, "page_size": page_size, "sha256": digest,
            "source_bytes": partial.stat().st_size,
            "null_or_omitted_optional_fields": dict(sorted(missing_optional.items())),
            "retrieved_utc": when.astimezone(dt.timezone.utc).isoformat(),
            "limitations": "Mutable source; matching counts do not prove immutable content or independent completeness. Raw CSV and manifest are private."
        }
        temporary_manifest = Path(directory) / "manifest.json"
        temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.link(partial, output)
        try:
            os.link(temporary_manifest, manifest_path)
        except BaseException:
            output.unlink()
            raise
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--page-size", type=int, default=5000)
    parser.add_argument("--max-rows", type=int, default=500000)
    parser.add_argument("--expected-count", type=int)
    args = parser.parse_args()
    result = acquire(args.month, args.output, page_size=args.page_size,
                     max_rows=args.max_rows, expected_count=args.expected_count)
    print(json.dumps({"rows_exported": result["rows_exported"], "sha256": result["sha256"],
                      "manifest": str(Path(args.output).with_suffix(Path(args.output).suffix + ".manifest.json"))}))

if __name__ == "__main__":
    main()
