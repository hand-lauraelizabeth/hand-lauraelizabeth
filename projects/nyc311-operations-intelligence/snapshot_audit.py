"""File-internal integrity checks for a pinned NYC 311 CSV export.

The source CSV and temporary key index stay on the analyst's machine. Only
aggregate QA counters and a SHA-256 digest are returned; no request IDs.
"""
import argparse
import collections
import csv
import hashlib
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

REQUIRED = {"unique_key", "created_date", "closed_date"}

def audit_snapshot(path, *, expected_rows=None):
    if expected_rows is not None and (
        not isinstance(expected_rows, int) or isinstance(expected_rows, bool)
        or expected_rows < 0
    ):
        raise ValueError("expected_rows must be a nonnegative integer")
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    counts = collections.Counter()
    distinct = 0
    # Disk-backed unique index bounds RAM; the temporary file is deleted.
    with tempfile.TemporaryDirectory(prefix="nyc311-qa-") as tmp:
        with closing(sqlite3.connect(str(Path(tmp) / "keys.sqlite3"))) as db, db:
            db.execute("CREATE TABLE seen (key TEXT PRIMARY KEY) WITHOUT ROWID")
            with path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not REQUIRED.issubset(reader.fieldnames or []):
                    raise ValueError("CSV requires unique_key, created_date, closed_date")
                for row in reader:
                    counts["rows"] += 1
                    key = (row["unique_key"] or "").strip()
                    if not key:
                        counts["missing_unique_key"] += 1
                    else:
                        try:
                            db.execute("INSERT INTO seen (key) VALUES (?)", (key,))
                            distinct += 1
                        except sqlite3.IntegrityError:
                            counts["duplicate_unique_key"] += 1
                    if not (row["created_date"] or "").strip():
                        counts["missing_created_date"] += 1
                    if (row["closed_date"] or "").strip():
                        counts["closed_date_present"] += 1
                    if counts["rows"] % 10000 == 0:
                        db.commit()
    return {
        "source_sha256": digest.hexdigest(),
        "source_bytes": path.stat().st_size,
        "rows": counts["rows"],
        "distinct_nonblank_unique_keys": distinct,
        "missing_unique_key": counts["missing_unique_key"],
        "duplicate_unique_key": counts["duplicate_unique_key"],
        "missing_created_date": counts["missing_created_date"],
        "closed_date_present": counts["closed_date_present"],
        "expected_rows": expected_rows,
        "expected_rows_match": None if expected_rows is None else counts["rows"] == expected_rows,
        "limitations": "File-internal checks only; no proof of official export completeness, closure duration validity, or administrative resolution."
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv")
    p.add_argument("--expected-rows", type=int)
    p.add_argument("--output-json")
    args = p.parse_args()
    result = audit_snapshot(args.input_csv, expected_rows=args.expected_rows)
    output = json.dumps(result, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if (result["duplicate_unique_key"] or result["missing_unique_key"]
            or result["expected_rows_match"] is False):
        raise SystemExit(2)

if __name__ == "__main__":
    main()
