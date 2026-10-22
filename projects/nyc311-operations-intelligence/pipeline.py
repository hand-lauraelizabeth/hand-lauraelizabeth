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
from pathlib import Path

REQUIRED = {"unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"}
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"}
SOURCE_URL = "https://data.cityofnewyork.us/d/erm2-nwe9"

def dateparse(s):
    s = (s or "").strip()
    if not s: return None
    try: return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
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
    with source.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing: raise ValueError("Missing API columns: " + ", ".join(sorted(missing)))
        for row in reader:
            counts["rows_read"] += 1
            key = normalize(row["unique_key"])
            created = dateparse(row["created_date"])
            finished = dateparse(row["closed_date"])
            if not key: counts["missing_unique_key"] += 1
            if not created: counts["missing_or_invalid_created_date"] += 1; continue
            if created.date() > as_of_day: counts["created_after_as_of"] += 1; continue
            if finished and (finished < created): counts["closure_before_creation"] += 1
            borough = normalize(row["borough"]).upper()
            agency = normalize(row["agency"])
            problem = normalize(row["complaint_type"])
            if borough not in BOROUGHS: counts["missing_or_unknown_borough"] += 1; borough = "UNKNOWN"
            if not agency: counts["missing_agency"] += 1; agency = "UNKNOWN"
            if not problem: counts["missing_problem"] += 1; problem = "UNKNOWN"
            group = (created.date().strftime("%Y-%m"), borough, agency, problem)
            grouped[group] += 1
            counts["valid_records"] += 1
            if normalize(row["status"]).casefold() == "closed" and finished and finished >= created:
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
                  "closure":"closed status AND nonnegative valid close interval; not proof of resolution",
                  "privacy":"No record-level coordinates, addresses, ZIP codes, or details exported",
                  "limitations":"No distinct-identifier check, no rate/exposure denominators, no case-mix-adjusted agency comparisons."},
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
