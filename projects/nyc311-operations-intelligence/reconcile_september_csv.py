"""Private NYC 311 September CSV reconciliation against a dated SoQL API audit.

Checks content, not file origin. No record-level values are written to output.
A passing reconciliation never authorizes publication.
"""
import argparse
from collections import Counter
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

NYC = ZoneInfo("America/New_York")
PERIOD = "2026-09"
SOURCE = "https://data.cityofnewyork.us/d/erm2-nwe9"
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND", "Unspecified"}
REQUIRED = {"unique_key", "created_date", "borough"}


def checksum(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def local_month(value):
    try:
        parsed = dt.datetime.fromisoformat((value or "").strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(NYC)
        return parsed.strftime("%Y-%m")
    except (ValueError, TypeError):
        return None


def normalize_borough(value):
    v = " ".join((value or "").split()).upper()
    return "Unspecified" if v in ("", "UNSPECIFIED") else v


def reconcile(path, evidence, *, expected_sha256=None):
    if (not isinstance(evidence, dict) or evidence.get("dataset_id") != "erm2-nwe9"
        or evidence.get("period") != PERIOD or evidence.get("source") != SOURCE
        or evidence.get("verification_scope") != "live_API_aggregate_only"
        or evidence.get("publication_authorized") is not False
        or evidence.get("full_csv_reconciled") is not False):
        raise ValueError("Invalid or unpinned API evidence")
    expected = evidence.get("borough_counts")
    if not isinstance(expected, dict) or set(expected) != BOROUGHS:
        raise ValueError("Invalid borough evidence")
    if any(type(n) is not int or n < 0 for n in expected.values()):
        raise ValueError("Invalid borough counts")
    total = evidence.get("total_rows")
    if type(total) is not int or total <= 0 or sum(expected.values()) != total:
        raise ValueError("API evidence totals do not reconcile")
    if evidence.get("distinct_keys") != total or evidence.get("nonnull_keys") != total:
        raise ValueError("API evidence key counts do not reconcile")
    if not isinstance(evidence.get("source_query_urls"), dict) or set(evidence["source_query_urls"]) != {"summary", "borough", "month"}:
        raise ValueError("Missing API source queries")
    if any(not isinstance(u, str) or not u.startswith("https://data.cityofnewyork.us/resource/erm2-nwe9.json?") for u in evidence["source_query_urls"].values()):
        raise ValueError("Unexpected API source query")

    path = Path(path)
    before = path.stat()
    digest = checksum(path)
    if expected_sha256 is not None and (len(expected_sha256) != 64 or digest.lower() != expected_sha256.lower()):
        raise ValueError("CSV hash does not match pinned expected hash")
    seen = set()
    counts = Counter()
    by_borough = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("CSV API columns missing or duplicated")
        for row in reader:
            counts["rows_read"] += 1
            key = (row.get("unique_key") or "").strip()
            if not key:
                counts["missing_key"] += 1
            elif key in seen:
                counts["duplicate_key"] += 1
            else:
                seen.add(key)
            if local_month(row.get("created_date")) != PERIOD:
                counts["invalid_or_outside_month"] += 1
            borough = normalize_borough(row.get("borough"))
            if borough not in BOROUGHS:
                counts["invalid_borough"] += 1
            else:
                by_borough[borough] += 1
    after = path.stat()
    if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns or checksum(path) != digest:
        raise ValueError("CSV changed during audit")
    if (counts["rows_read"] != total or len(seen) != total
        or any(counts[k] for k in ("missing_key", "duplicate_key", "invalid_or_outside_month", "invalid_borough"))
        or dict(by_borough) != expected):
        raise ValueError("CSV does not reconcile with the dated API evidence")
    return {
        "dataset_id": "erm2-nwe9", "period": PERIOD,
        "api_verification_date": evidence.get("verification_date"),
        "api_evidence_source": SOURCE, "csv_sha256": digest,
        "csv_bytes": before.st_size, "rows_reconciled": total,
        "distinct_nonnull_keys": len(seen), "borough_counts": dict(sorted(by_borough.items())),
        "full_csv_reconciled": True, "source_origin_authenticated": False,
        "publication_authorized": False,
        "limitations": "Exact row-level counts and checksums do not authenticate the CSV's origin or establish disclosure-safe public release."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("api_evidence_json", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--expect-sha256", default=None)
    args = parser.parse_args()
    evidence = json.loads(args.api_evidence_json.read_text(encoding="utf-8"))
    result = reconcile(args.input_csv, evidence, expected_sha256=args.expect_sha256)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output_json.with_suffix(args.output_json.suffix + ".tmp")
    tmp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(args.output_json)
    print(json.dumps({"rows_reconciled": result["rows_reconciled"], "publication_authorized": False}))


if __name__ == "__main__":
    main()
