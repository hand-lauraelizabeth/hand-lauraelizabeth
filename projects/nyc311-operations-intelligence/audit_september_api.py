"""Independent, fail-closed NYC 311 September API aggregate audit.

This checks current SoQL counts and key uniqueness. It DOES NOT reconcile a
complete CSV, authenticate a CSV checksum, or authorize publication.
"""
import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATASET = "erm2-nwe9"
BASE = f"https://data.cityofnewyork.us/resource/{DATASET}.json"
WHERE = "created_date >= '2026-09-01T00:00:00' AND created_date < '2026-10-01T00:00:00'"
BOROUGHS = {"BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND", "Unspecified"}
QUERIES = {
    "summary": {"$select": "count(*) as n,count(distinct unique_key) as distinct_keys,count(unique_key) as nonnull_keys", "$where": WHERE},
    "borough": {"$select": "borough,count(*) as n,count(distinct unique_key) as distinct_keys", "$where": WHERE, "$group": "borough", "$order": "borough", "$limit": "100"},
    "month": {"$select": "date_trunc_ym(created_date) as month,count(*) as n", "$where": WHERE, "$group": "month", "$order": "month"},
}

def urls():
    return {name: BASE + "?" + urlencode(params) for name, params in QUERIES.items()}

def fetch(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "NYC311-Independent-Research-Audit/1.0"})
    with urlopen(request, timeout=40) as response:
        if response.status != 200:
            raise ValueError(f"HTTP status {response.status}")
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("API aggregate response exceeds 2 MB")
    return json.loads(body)

def positive_integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)) or not str(value).isdigit():
        raise ValueError("Invalid count field")
    number = int(value)
    if number <= 0:
        raise ValueError("Zero or negative count")
    return number

def audit(summary, borough, month, *, expected_count=None):
    if not isinstance(summary, list) or len(summary) != 1:
        raise ValueError("Expected exactly one summary")
    item = summary[0]
    total = positive_integer(item["n"])
    distinct = positive_integer(item["distinct_keys"])
    nonnull = positive_integer(item["nonnull_keys"])
    if not (total == distinct == nonnull):
        raise ValueError("Missing or duplicated unique_key")
    if expected_count is not None and total != expected_count:
        raise ValueError("Source drift from expected snapshot count")
    if not isinstance(borough, list) or len(borough) != len(BOROUGHS):
        raise ValueError("Borough coverage incomplete")
    by_borough = {}
    for row in borough:
        label = row["borough"]
        if label not in BOROUGHS or label in by_borough:
            raise ValueError("Unexpected or repeated borough")
        n = positive_integer(row["n"])
        if n != positive_integer(row["distinct_keys"]):
            raise ValueError("Duplicate identifier within borough")
        by_borough[label] = n
    if set(by_borough) != BOROUGHS or sum(by_borough.values()) != total:
        raise ValueError("Borough counts do not reconcile to total")
    if not isinstance(month, list) or len(month) != 1 or month[0].get("month") != "2026-09-01T00:00:00.000":
        raise ValueError("Unexpected month grouping")
    if positive_integer(month[0]["n"]) != total:
        raise ValueError("Month count does not reconcile")
    return {"dataset_id": DATASET, "period": "2026-09", "total_rows": total,
            "distinct_keys": distinct, "nonnull_keys": nonnull,
            "borough_counts": dict(sorted(by_borough.items())),
            "source_query_urls": urls(), "verification_scope": "live_API_aggregate_only",
            "full_csv_reconciled": False, "csv_source_sha256": None,
            "publication_authorized": False}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("--expect-count", type=int)
    args = parser.parse_args()
    responses = {name: fetch(url) for name, url in urls().items()}
    report = audit(responses["summary"], responses["borough"], responses["month"], expected_count=args.expect_count)
    report["verified_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output_json.parent, delete=False) as tmp:
        json.dump(report, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp_path = tmp.name
    os.replace(tmp_path, args.output_json)
    print(json.dumps({"rows": report["total_rows"], "boroughs": len(report["borough_counts"]), "csv_reconciled": False}))

if __name__ == "__main__":
    main()
