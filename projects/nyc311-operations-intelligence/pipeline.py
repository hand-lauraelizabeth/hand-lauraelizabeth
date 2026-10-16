"""NYC 311 CSV aggregate builder with disclosure-safe public JSON."""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
from disclosure import publish_cells

REQUIRED = {"unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"}
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"}
SOURCE_URL = "https://data.cityofnewyork.us/d/erm2-nwe9"

def dateparse(s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None

def normalize(s):
    return " ".join((s or "").strip().split())

def ingest(source, output, *, as_of, min_cell=10):
    source = Path(source)
    as_of_day = dt.date.fromisoformat(as_of)
    if min_cell < 2:
        raise ValueError("min_cell must be at least 2")
    digest = hashlib.sha256()
    with source.open("rb") as binary:
        while chunk := binary.read(1024 * 1024):
            digest.update(chunk)
    counts = collections.Counter()
    grouped = collections.Counter()
    closed = collections.Counter()
    with source.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing API columns: " + ", ".join(sorted(missing)))
        for row in reader:
            counts["rows_read"] += 1
            key = normalize(row["unique_key"])
            created = dateparse(row["created_date"])
            finished = dateparse(row["closed_date"])
            if not key:
                counts["missing_unique_key"] += 1
            if not created:
                counts["missing_or_invalid_created_date"] += 1
                continue
            if created.date() > as_of_day:
                counts["created_after_as_of"] += 1
                continue
            if finished and finished < created:
                counts["closure_before_creation"] += 1
            borough = normalize(row["borough"]).upper()
            agency = normalize(row["agency"])
            problem = normalize(row["complaint_type"])
            if borough not in BOROUGHS:
                counts["missing_or_unknown_borough"] += 1
                borough = "UNKNOWN"
            if not agency:
                counts["missing_agency"] += 1
                agency = "UNKNOWN"
            if not problem:
                counts["missing_problem"] += 1
                problem = "UNKNOWN"
            group = (created.date().strftime("%Y-%m"), borough, agency, problem)
            grouped[group] += 1
            counts["valid_records"] += 1
            if normalize(row["status"]).casefold() == "closed" and finished and finished >= created:
                closed[group] += 1
    source_cells = [
        dict(month=m, borough=b, agency=a, problem=p, requests=n,
             closed_with_valid_interval=closed[(m,b,a,p)])
        for (m,b,a,p), n in sorted(grouped.items())
    ]
    disclosure = publish_cells(source_cells, minimum=min_cell)
    quality_private = dict(counts)
    quality_private["small_cells_suppressed"] = sum(n < min_cell for n in grouped.values())
    payload = {
        "source": SOURCE_URL,
        "dataset_id": "erm2-nwe9",
        "snapshot_as_of": as_of,
        "source_sha256": digest.hexdigest(),
        "source_bytes": source.stat().st_size,
        "rules": {
            "grain": "month × borough × agency × original API complaint_type",
            "display_minimum_cell_count": min_cell,
            "closure": "Closed status and nonnegative interval; not proof of issue resolution",
            "privacy": "No record-level locations, exact marginal totals, or suppressed cell counts exported",
            "limitations": "No distinct-identifier audit, rate denominators, or case-mix adjustment"
        },
        "disclosure": {"marginals_available": False, "note": disclosure["note"]},
        "aggregates": disclosure["cells"]
    }
    Path(output).write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {**payload, "quality": quality_private}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input_csv")
    p.add_argument("output_json")
    p.add_argument("--as-of", required=True)
    p.add_argument("--min-cell", type=int, default=10)
    a = p.parse_args()
    if a.min_cell < 2:
        p.error("--min-cell must be >= 2")
    result = ingest(a.input_csv, a.output_json, as_of=a.as_of, min_cell=a.min_cell)
    print(json.dumps({"private_quality": result["quality"], "public_cells": len(result["aggregates"])}))

if __name__ == "__main__":
    main()
