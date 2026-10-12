#!/usr/bin/env python3
"""Build a six-digit CIP x award-level *historical completions* layer.

This is an optional, lazy-loaded companion to the live national matcher, not
a claim that an institution currently offers a named program or license.
Inputs must be original NCES 2025 IPEDS C2025_A and NCES CIPCode2020 CSV/ZIP.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

from national_ipeds_completion_bridge import digest, national_records, normalize_cip

COMPLETIONS_URL = "https://nces.ed.gov/ipeds/datacenter/data/C2025_A.zip"
CIP_URL = "https://nces.ed.gov/ipeds/cipcode/resources.aspx?y=56"
AWARD_LEVELS = {
    "1": "Undergraduate certificate: less than 1 year",
    "2": "Undergraduate certificate: 1 to under 2 years",
    "3": "Associate's degree",
    "4": "Undergraduate certificate: 2 to under 4 years",
    "5": "Bachelor's degree",
    "6": "Postbaccalaureate certificate",
    "7": "Master's degree",
    "8": "Post-master's certificate",
    "17": "Doctor's degree: research/scholarship",
    "18": "Doctor's degree: professional practice",
    "19": "Doctor's degree: other",
}
# AWLEVEL 12-15 are totals; 20 and 21 subdivide level 1.
ROLLUP_LEVELS = {"12", "13", "14", "15", "20", "21"}
KNOWN_MISSING = {"", "NA", "N/A", "NULL", "PS", "-1", "-2"}


def source_rows(path: Path, csv_name: str):
    """CSV and ZIP ingestion, rejecting ambiguous or unsafe archive entries."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            matches = [
                i for i in z.infolist()
                if Path(i.filename).name.lower() == csv_name.lower()
                and not i.filename.startswith("__MACOSX/")
                and not Path(i.filename).name.startswith("._")
                and not i.is_dir()
            ]
            if len(matches) != 1:
                raise ValueError(f"Expected one {csv_name} in source archive")
            if matches[0].file_size > 512 * 1024 * 1024:
                raise ValueError("Unexpectedly large source CSV")
            with z.open(matches[0]) as raw:
                yield from parsed_rows(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
    else:
        if path.name.lower() != csv_name.lower():
            raise ValueError(f"Expected official filename {csv_name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from parsed_rows(stream)


def parsed_rows(stream):
    reader = csv.DictReader(stream)
    headers = reader.fieldnames or []
    if len(headers) != len(set(headers)) or not headers or any(not x for x in headers):
        raise ValueError("Missing, blank, or duplicate CSV headers")
    for row in reader:
        if None in row:
            raise ValueError("Malformed CSV row with extra columns")
        yield row


def get(row, *names):
    normalized = {k.upper().replace("_", ""): v for k, v in row.items()}
    for name in names:
        val = normalized.get(name.upper().replace("_", ""))
        if val is not None:
            return str(val).strip()
    raise ValueError("Missing expected field: " + "/".join(names))


def cip_titles(path):
    titles = {}
    for row in source_rows(path, "CIPCode2020.csv"):
        cip = normalize_cip(get(row, "CIPCODE", "CIPCODE2020"))
        # The official classification contains 2- and 4-digit headers; skip.
        if not cip:
            continue
        title = get(row, "CIPTITLE", "CIPTITLE2020")
        if not title:
            raise ValueError("Blank title for CIP " + cip)
        if cip in titles and titles[cip] != title:
            raise ValueError("Conflicting CIP2020 title for " + cip)
        titles[cip] = title
    if not titles:
        raise ValueError("Empty six-digit NCES CIP 2020 classification")
    return titles


def reported_count(raw):
    token = str(raw).strip()
    if token.upper() in KNOWN_MISSING:
        return None, "missing_or_suppressed"
    if not re.fullmatch(r"\d+(?:\.0+)?", token):
        raise ValueError("Invalid IPEDS completion count: " + token)
    return int(float(token)), "reported"


def program_rows(csv_or_zip, titles, allowed_ids):
    rows = defaultdict(list)
    seen = set()
    stats = defaultdict(int)
    for entry in source_rows(csv_or_zip, "C2025_A.csv"):
        stats["source_rows"] += 1
        unitid = get(entry, "UNITID")
        cip = normalize_cip(get(entry, "CIPCODE", "CIP6"))
        major = get(entry, "MAJORNUM")
        level = get(entry, "AWLEVEL")
        if major == "2":
            stats["second_major_excluded"] += 1
            continue
        if major != "1":
            raise ValueError("Unsupported first-major indicator: " + major)
        if not cip:
            stats["cip_summary_excluded"] += 1
            continue
        if level in ROLLUP_LEVELS:
            stats["overlapping_award_totals_excluded"] += 1
            continue
        if level not in AWARD_LEVELS:
            raise ValueError("Unexpected NCES award level: " + level)
        if not re.fullmatch(r"\d{6}", unitid):
            raise ValueError("Invalid IPEDS UNITID: " + unitid)
        if cip not in titles:
            raise ValueError("CIP 2020 title missing for reported CIP " + cip)
        key = (unitid, cip, level)
        if key in seen:
            raise ValueError("Duplicate unitid/CIP6/AWLEVEL first-major record: " + repr(key))
        seen.add(key)
        count, status = reported_count(get(entry, "CTOTALT"))
        if unitid not in allowed_ids:
            stats["source_rows_outside_national_universe"] += 1
            continue
        rows[unitid].append([cip, level, count, status])
        stats["joined_program_award_records"] += 1
        if status == "reported":
            stats["reported_completion_cells"] += 1
        else:
            stats["missing_or_suppressed_completion_cells"] += 1
    for values in rows.values():
        values.sort(key=lambda r: (r[0], int(r[1])))
    return rows, dict(stats)


def write_asset(path, payload):
    data = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(data)
    compressed = gzip.compress(data, compresslevel=9, mtime=0)
    path.with_name(path.name + ".gz").write_bytes(compressed)
    if len(compressed) > 768000:
        raise ValueError("Program shard exceeds 750 KiB compressed limit: " + path.name)
    return {"file": path.name, "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "gzip_bytes": len(compressed),
            "gzip_sha256": hashlib.sha256(compressed).hexdigest()}


def build(national_dir, completions_path, cip_path, out_dir):
    national, shards = national_records(national_dir)
    allowed_ids = {row[0] for _, records in shards for row in records}
    titles = cip_titles(cip_path)
    records, counters = program_rows(completions_path, titles, allowed_ids)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for oldname, institutions in shards:
        entries = [[row[0], records[row[0]]] for row in institutions if row[0] in records]
        output = out_dir / oldname.replace("national-", "programs-")
        asset = write_asset(output, {"schema_version": "1.0", "institutions": entries})
        asset["institutions"] = len(entries)
        asset["program_award_records"] = sum(len(item[1]) for item in entries)
        files.append(asset)
    lookup = write_asset(out_dir / "cip2020-titles.json", titles)
    counts = {
        "national_institutions": len(allowed_ids),
        "institutions_with_historical_program_completions": len(records),
        "national_institutions_without_joined_completions": len(allowed_ids)-len(records),
        "distinct_six_digit_cip2020_titles": len(titles),
        **counters,
    }
    manifest = {
        "schema_version": "1.0",
        "data_kind": "IPEDS_2024_25_HISTORICAL_FIRST_MAJOR_COMPLETIONS",
        "current_program_offering_verified": False,
        "credential_name_institution_verified": False,
        "professional_license_eligibility_verified": False,
        "admissions_and_career_matching_authorized": False,
        "national_scorecard_data_version": national["data_version"],
        "unitid_join_rule": "Exact six-digit UNITID only; eight-digit extensions remain unmatched",
        "program_identity": ["UNITID", "CIP2020_6digit", "AWLEVEL"],
        "program_row_layout": ["cip6", "awlevel", "awards_conferred", "count_status"],
        "source_reporting_period": "2024-07-01 through 2025-06-30",
        "source_release_status": "IPEDS 2025 preliminary/provisional; check source revision",
        "sources": {
            "completions": {"url": COMPLETIONS_URL, "sha256": digest(completions_path)},
            "cip2020": {"url": CIP_URL, "sha256": digest(cip_path)},
        },
        "award_levels": AWARD_LEVELS,
        "cip2020_titles": lookup,
        "counts": counts,
        "shards": files,
        "caveats": [
            "IPEDS completions are historical activity, not a current academic program catalog.",
            "CIP titles are federal categories, not exact school-advertised degree names.",
            "Award level is not evidence of RN/LPN licensing, board eligibility or a named BSN/AAS credential.",
            "Zero is an observed count; missing/suppressed counts remain null, never zero.",
            "No program-present inference from the absence of completions; no parent-campus UNITID coercion.",
            "No career or admission outcome inferred from CIP/completions alone.",
        ],
    }
    (out_dir / "programs.manifest.v1.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("national_dir", type=Path)
    p.add_argument("c2025_a_csv_or_zip", type=Path)
    p.add_argument("cipcode2020_csv_or_zip", type=Path)
    p.add_argument("output_dir", type=Path)
    args = p.parse_args()
    result = build(args.national_dir, args.c2025_a_csv_or_zip,
                   args.cipcode2020_csv_or_zip, args.output_dir)
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
