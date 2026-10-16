"""Build disclosure-safe NYC 311 aggregates from an integrity-checked CSV."""
import argparse
import collections
import csv
import datetime as dt
import json
from pathlib import Path
from disclosure import publish_cells
from snapshot_audit import audit_snapshot

REQUIRED = {"unique_key", "created_date", "closed_date", "agency", "complaint_type", "borough", "status"}
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND"}
SOURCE_URL = "https://data.cityofnewyork.us/d/erm2-nwe9"

def dateparse(s):
    """Parse source floating timestamps; do not guess offsets or timezones."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        value = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return value if value.tzinfo is None else None
    except ValueError:
        return None

def normalize(s):
    return " ".join((s or "").strip().split())

def ingest(source, output, *, as_of, min_cell=10, expected_rows=None):
    source = Path(source)
    as_of_day = dt.date.fromisoformat(as_of)
    if not isinstance(min_cell, int) or isinstance(min_cell, bool) or min_cell < 2:
        raise ValueError("min_cell must be an integer >= 2")
    # Fail closed before aggregation rather than counting duplicate requests.
    audit = audit_snapshot(source, expected_rows=expected_rows)
    if (audit["missing_unique_key"] or audit["duplicate_unique_key"]
            or audit["expected_rows_match"] is False):
        raise ValueError("Source integrity failed: missing/duplicate keys or expected-row mismatch; no aggregate exported")
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
            created = dateparse(row["created_date"])
            finished_raw = normalize(row["closed_date"])
            finished = dateparse(finished_raw)
            if not created:
                counts["missing_or_invalid_created_date"] += 1
                continue
            if created.date() > as_of_day:
                counts["created_after_as_of"] += 1
                continue
            if finished_raw and finished is None:
                counts["invalid_or_timezone_qualified_closed_date"] += 1
            if finished and finished < created:
                counts["closure_before_creation"] += 1
            if finished and finished.date() > as_of_day:
                counts["closed_date_after_as_of"] += 1
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
            status_closed = normalize(row["status"]).casefold() == "closed"
            usable_close = (finished is not None and finished >= created
                            and finished.date() <= as_of_day)
            if status_closed and usable_close:
                closed[group] += 1
                duration = finished - created
                counts["closed_with_valid_interval"] += 1
                if duration == dt.timedelta(0):
                    counts["zero_length_closure_interval"] += 1
                if duration > dt.timedelta(days=365):
                    counts["closure_interval_over_365_days"] += 1
            elif status_closed:
                counts["closed_status_without_usable_close_date"] += 1
            elif finished is not None:
                counts["nonclosed_status_with_closed_date"] += 1
    source_cells = [
        dict(month=m, borough=b, agency=a, problem=p, requests=n,
             closed_with_valid_interval=closed[(m, b, a, p)])
        for (m, b, a, p), n in sorted(grouped.items())
    ]
    disclosure = publish_cells(source_cells, minimum=min_cell)
    quality_private = dict(counts)
    quality_private["small_cells_suppressed"] = sum(n < min_cell for n in grouped.values())
    quality_private["source_rows"] = audit["rows"]
    quality_private["unique_key_integrity_verified"] = True
    payload = {
        "source": SOURCE_URL,
        "dataset_id": "erm2-nwe9",
        "snapshot_as_of": as_of,
        "source_sha256": audit["source_sha256"],
        "source_bytes": audit["source_bytes"],
        "rules": {
            "grain": "month × borough × agency × original API complaint_type",
            "display_minimum_cell_count": min_cell,
            "closure": "Closed status, source floating timestamps, and nonnegative interval ending by cutoff; not proof of issue resolution",
            "privacy": "No record-level locations, exact marginal totals, or suppressed cell counts exported",
            "limitations": "Source IDs checked for uniqueness within the CSV; no proof of source completeness, rate denominators, or case-mix adjustment. snapshot_as_of is an analyst cutoff, not an independently verified export timestamp."
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
    p.add_argument("--expected-rows", type=int)
    a = p.parse_args()
    if a.min_cell < 2:
        p.error("--min-cell must be >= 2")
    result = ingest(a.input_csv, a.output_json, as_of=a.as_of,
                    min_cell=a.min_cell, expected_rows=a.expected_rows)
    print(json.dumps({"private_quality": result["quality"], "public_cells": len(result["aggregates"])}))

if __name__ == "__main__":
    main()
