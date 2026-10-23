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

def ingest(source, output, *, as_of, min_cell=10):
    source = Path(source)
    destination = Path(output)
    # Reject identical files and aliases before opening either path.
    # resolve() detects path and symlink aliases; samefile() detects hardlinks.
    if source.resolve() == destination.resolve() or (
        destination.exists() and source.samefile(destination)
    ):
        raise ValueError("Input CSV and output JSON must refer to distinct files")
    as_of_day = dt.date.fromisoformat(as_of)
    digest = hashlib.sha256()
    with source.open("rb") as binary:
        while chunk := binary.read(1024 * 1024): digest.update(chunk)
    counts = collections.Counter()
    grouped = collections.Counter()
    closed = collections.Counter()
    # A disk-backed uniqueness index avoids holding request IDs in Python RAM.
    # Its private temporary files are removed even if parsing raises.
    with tempfile.TemporaryDirectory(prefix="nyc311-ids-") as scratch, \
            closing(sqlite3.connect(str(Path(scratch) / "keys.sqlite3"))) as db, \
            source.open(encoding="utf-8-sig", newline="") as f:
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
    # Display-safe threshold; totals kept separately so small cells are not misreported as zero.
    records = [dict(month=m, borough=b, agency=a, problem=p, requests=n,
                    closed_with_valid_interval=closed[(m,b,a,p)])
               for (m,b,a,p),n in sorted(grouped.items()) if n >= min_cell]
    counts["small_cells_suppressed"] = sum(1 for n in grouped.values() if n < min_cell)
    payload = {
        "source": SOURCE_URL,
        "dataset_id": "erm2-nwe9", "snapshot_as_of": as_of,
        "source_sha256": digest.hexdigest(), "source_bytes": source.stat().st_size,
        "rules": {"grain":"month × borough × agency × original API complaint_type",
                  "display_minimum_cell_count":min_cell,
                  "closure":"closed status AND nonnegative elapsed interval by snapshot date in New York; not proof of resolution",
                  "privacy":"No record-level coordinates, addresses, ZIP codes, or details exported",
                  "limitations":"Distinct IDs checked within this input; no rate/exposure denominators or case-mix-adjusted agency comparisons."},
        "quality": dict(counts), "aggregates": records
    }
    Path(output).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return payload

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv"); p.add_argument("output_json")
    p.add_argument("--as-of", required=True, help="snapshot date YYYY-MM-DD")
    p.add_argument("--min-cell", type=int, default=10)
    a = p.parse_args()
    if a.min_cell < 1: p.error("--min-cell must be positive")
    result = ingest(a.input_csv, a.output_json, as_of=a.as_of, min_cell=a.min_cell)
    print(json.dumps({"quality":result["quality"],"public_cells":len(result["aggregates"])}))
if __name__ == "__main__": main()
