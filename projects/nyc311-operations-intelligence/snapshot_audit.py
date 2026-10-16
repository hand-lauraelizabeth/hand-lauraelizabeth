"""Offline integrity audit of a pinned NYC 311 CSV snapshot.

Reports only counts, provenance and a file digest; never emits request identifiers.
This checks file-internal uniqueness, not whether an API export was complete.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path

def audit_snapshot(path, *, expected_rows=None):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    counts = collections.Counter()
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not {"unique_key", "created_date", "closed_date"}.issubset(reader.fieldnames or []):
            raise ValueError("CSV requires unique_key, created_date, closed_date")
        for row in reader:
            counts["rows"] += 1
            key = (row["unique_key"] or "").strip()
            if not key:
                counts["missing_unique_key"] += 1
            elif key in seen:
                counts["duplicate_unique_key"] += 1
            else:
                seen.add(key)
            if not (row["created_date"] or "").strip():
                counts["missing_created_date"] += 1
            if (row["closed_date"] or "").strip():
                counts["closed_date_present"] += 1
    result = {
        "source_sha256": digest.hexdigest(),
        "source_bytes": path.stat().st_size,
        "rows": counts["rows"],
        "distinct_nonblank_unique_keys": len(seen),
        "missing_unique_key": counts["missing_unique_key"],
        "duplicate_unique_key": counts["duplicate_unique_key"],
        "missing_created_date": counts["missing_created_date"],
        "closed_date_present": counts["closed_date_present"],
        "expected_rows": expected_rows,
        "expected_rows_match": None if expected_rows is None else counts["rows"] == expected_rows,
        "limitations": "File-internal checks only. No proof of source completeness, duration validity or administrative resolution."
    }
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv")
    p.add_argument("--expected-rows", type=int)
    p.add_argument("--output-json")
    args = p.parse_args()
    if args.expected_rows is not None and args.expected_rows < 0:
        p.error("--expected-rows must be nonnegative")
    result = audit_snapshot(args.input_csv, expected_rows=args.expected_rows)
    output = json.dumps(result, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if result["duplicate_unique_key"] or result["missing_unique_key"] or result["expected_rows_match"] is False:
        raise SystemExit(2)

if __name__ == "__main__":
    main()
