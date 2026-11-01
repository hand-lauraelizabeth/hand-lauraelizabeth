"""NYC 311 offline, privacy-conscious aggregate builder (standard library only).

Input: a locally downloaded CSV export of the official NYC Open Data
311 Service Requests from 2020 to Present (erm2-nwe9).
This does not publish individual request locations or addresses.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from zoneinfo import ZoneInfo

NYC_TZ = ZoneInfo("America/New_York")

REQUIRED = {"unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"}
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"}
SOURCE_URL = "https://data.cityofnewyork.us/d/erm2-nwe9"

def dateparse(s):
    s = (s or "").strip()
    if not s: return None
    try:
        parsed = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=NYC_TZ)
        return parsed.astimezone(NYC_TZ)
    except ValueError: return None

def normalize(s):
    return " ".join((s or "").strip().split())

def ingest(source, output, *, as_of, min_cell=10, expected_sha256=None,
           expected_rows=None, reporting_month=None):
    source = Path(source)
    destination = Path(output)
    # Reject identical files and aliases before opening either path.
    # resolve() detects path and symlink aliases; samefile() detects hardlinks.
    if source.resolve() == destination.resolve() or (
        destination.exists() and source.samefile(destination)
    ):
        raise ValueError("Input CSV and output JSON must refer to distinct files")
    as_of_day = dt.date.fromisoformat(as_of)
    if reporting_month is not None:
        # An explicit full-month source cohort must be complete by calendar
        # boundary and checked against an independently retained receipt.
        # This verifies membership, not official origin or completeness.
        if (not isinstance(reporting_month, str)
                or not re.fullmatch(r"\d{4}-\d{2}", reporting_month)):
            raise ValueError("Invalid required reporting month")
        try:
            month_start = dt.date.fromisoformat(reporting_month + "-01")
        except ValueError:
            raise ValueError("Invalid required reporting month") from None
        # A date-only as-of value cannot attest to the entire reporting
        # month until its first subsequent calendar day (including Dec→Jan).
        first_after = (dt.date(month_start.year + 1, 1, 1)
                       if month_start.month == 12 else
                       dt.date(month_start.year, month_start.month + 1, 1))
        if as_of_day < first_after:
            raise ValueError("Snapshot precedes completion of required reporting month")
        if expected_sha256 is None or expected_rows is None:
            raise ValueError("Full-month cohort requires independent SHA-256 and row count")
    if (expected_sha256 is None) != (expected_rows is None):
        raise ValueError("Expected SHA-256 and row count must be supplied together")
    if expected_sha256 is not None:
        if (len(expected_sha256) != 64 or
                any(c not in "0123456789abcdefABCDEF" for c in expected_sha256)):
            raise ValueError("Expected SHA-256 must be 64 hexadecimal characters")
        if type(expected_rows) is not int or expected_rows < (1 if reporting_month else 0):
            raise ValueError("Expected row count must be a valid integer")
    counts = collections.Counter()
    grouped = collections.Counter()
    closed = collections.Counter()
    # A disk-backed uniqueness index avoids holding request IDs in Python RAM.
    # Its private temporary files are removed even if parsing raises.
    # Hash exactly the immutable snapshot parsed below, not a separate read of
    # a source file that might change between hashing and parsing.
    with tempfile.TemporaryDirectory(prefix="nyc311-ids-") as scratch:
        snapshot = Path(scratch) / "source_snapshot.csv"
        digest = hashlib.sha256()
        source_bytes = 0
        with source.open("rb") as original, snapshot.open("wb") as copied:
            while chunk := original.read(1024 * 1024):
                copied.write(chunk)
                digest.update(chunk)
                source_bytes += len(chunk)
        # The expected digest must originate from an independently retained
        # source manifest. Matching caller-supplied values does not prove origin.
        if expected_sha256 is not None and digest.hexdigest().lower() != expected_sha256.lower():
            raise ValueError("CSV SHA-256 does not match supplied manifest")
        with closing(sqlite3.connect(str(Path(scratch) / "keys.sqlite3"))) as db, \
                snapshot.open(encoding="utf-8-sig", newline="") as f:
            db.execute("CREATE TABLE seen (request_id TEXT PRIMARY KEY) WITHOUT ROWID")
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)):
                raise ValueError("Duplicate CSV header")
            missing = REQUIRED - set(headers)
            if missing: raise ValueError("Missing API columns: " + ", ".join(sorted(missing)))
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Malformed CSV row: inconsistent field count")
                counts["rows_read"] += 1
                key = normalize(row["unique_key"])
                created = dateparse(row["created_date"])
                finished = dateparse(row["closed_date"])
                # In strict full-month mode, a nonempty malformed closure
                # timestamp is a source-contract failure, never an open case.
                if (reporting_month is not None and
                        normalize(row["closed_date"]) and finished is None):
                    raise ValueError("Invalid closed_date in required month cohort")
                if reporting_month is not None:
                    # Compare New York calendar dates, not UTC date strings.
                    # Never silently skip invalid, out-of-cohort or future rows.
                    if created is None:
                        raise ValueError("Invalid created_date in required month cohort")
                    if created.strftime("%Y-%m") != reporting_month:
                        raise ValueError("CSV row outside required reporting month")
                    if created.date() > as_of_day:
                        raise ValueError("CSV row after snapshot date")
                    counts["reporting_month_rows_verified"] += 1
                if not key: raise ValueError("Missing unique_key")
                try:
                    db.execute("INSERT INTO seen (request_id) VALUES (?)", (key,))
                except sqlite3.IntegrityError:
                    # Never include actual request IDs in exceptions.
                    raise ValueError("Duplicate unique_key") from None
                if not created: counts["missing_or_invalid_created_date"] += 1; continue
                if created.date() > as_of_day: counts["created_after_as_of"] += 1; continue
                valid_closure = False
                if finished:
                    # Compare UTC instants, not NYC wall-clock times across DST folds.
                    if finished.astimezone(dt.timezone.utc) < created.astimezone(dt.timezone.utc):
                        counts["closure_before_creation"] += 1
                    elif finished.date() > as_of_day:
                        counts["closure_after_as_of"] += 1
                    else:
                        valid_closure = True
                borough = normalize(row["borough"]).upper()
                agency = normalize(row["agency"])
                problem = normalize(row["complaint_type"])
                if borough not in BOROUGHS: counts["missing_or_unknown_borough"] += 1; borough = "UNKNOWN"
                if not agency: counts["missing_agency"] += 1; agency = "UNKNOWN"
                if not problem: counts["missing_problem"] += 1; problem = "UNKNOWN"
                group = (created.date().strftime("%Y-%m"), borough, agency, problem)
                grouped[group] += 1
                counts["valid_records"] += 1
                if normalize(row["status"]).casefold() == "closed" and valid_closure:
                    closed[group] += 1
        if expected_rows is not None and counts["rows_read"] != expected_rows:
            raise ValueError("CSV row count does not match supplied manifest")
        # A source mutation during processing invalidates this source binding.
        # This is an integrity check, NOT independent official-source authentication.
        current = hashlib.sha256()
        with source.open("rb") as original:
            while chunk := original.read(1024 * 1024):
                current.update(chunk)
        if current.digest() != digest.digest():
            raise ValueError("Input CSV changed during processing")
    # Display-safe threshold; totals kept separately so small cells are not misreported as zero.
    # Suppressing small request cells is insufficient: an exact closure count
    # inside a large request cell can disclose a small outcome subgroup, or
    # its small complement (requests - closed). Null, never zero, denotes
    # withheld closure counts. Zero and all-closed cells are safe within
    # this single-table threshold rule, but cross-release differencing is
    # NOT addressed; no public release until a separate disclosure audit.
    records = []
    for (m, b, a, p), n in sorted(grouped.items()):
        if n < min_cell:
            continue
        c = closed[(m, b, a, p)]
        withheld = (0 < c < min_cell) or (0 < n - c < min_cell)
        if withheld:
            counts["closure_subcells_suppressed"] += 1
        records.append(dict(
            month=m, borough=b, agency=a, problem=p, requests=n,
            closed_with_valid_interval=None if withheld else c
        ))
    counts["small_cells_suppressed"] = sum(1 for n in grouped.values() if n < min_cell)
    counts["unique_keys_verified"] = counts["rows_read"]
    counts["supplied_manifest_verified"] = expected_sha256 is not None
    payload = {
        "source": SOURCE_URL,
        "dataset_id": "erm2-nwe9", "snapshot_as_of": as_of,
        "source_sha256": digest.hexdigest(), "source_bytes": source_bytes,
        "rules": {"grain":"month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count":min_cell,
                  "closure":"closed status AND nonnegative elapsed interval by snapshot date in New York; not proof of resolution",
                  "privacy":"No record-level coordinates, addresses, ZIP codes, or details exported",
                  "limitations":"Distinct IDs checked within this input; no rate/exposure denominators or case-mix-adjusted agency comparisons.",
                  "source_provenance":"Caller-supplied checksum/count agreement is not independent authentication of official NYC source origin."},
        "quality": dict(counts), "aggregates": records
    }
    if reporting_month is not None:
        payload["rules"]["strict_reporting_month"] = reporting_month
    # Preserve any existing export if serialization, flushing, or replacement fails.
    # The temporary file must be on the destination filesystem for atomic replace.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                         prefix=".nyc311_", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return payload

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv"); p.add_argument("output_json")
    p.add_argument("--as-of", required=True, help="snapshot date YYYY-MM-DD")
    p.add_argument("--min-cell", type=int, default=10)
    p.add_argument("--expected-sha256", help="independently recorded full-source SHA-256")
    p.add_argument("--expected-rows", type=int, help="independently recorded CSV data-row count")
    p.add_argument("--reporting-month", help="strict YYYY-MM cohort; requires expected SHA-256 and row count")
    a = p.parse_args()
    if a.min_cell < 1: p.error("--min-cell must be positive")
    result = ingest(a.input_csv, a.output_json, as_of=a.as_of, min_cell=a.min_cell,
                    expected_sha256=a.expected_sha256, expected_rows=a.expected_rows,
                    reporting_month=a.reporting_month)
    print(json.dumps({"quality":result["quality"],"public_cells":len(result["aggregates"])}))
if __name__ == "__main__": main()
