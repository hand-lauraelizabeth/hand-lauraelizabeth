#!/usr/bin/env python3
"""Build a source-preserving IPEDS enrichment for the EXISTING national college matcher.

Inputs: committed Scorecard national manifest/shards and official HD2025 / C2025_A
CSV (or their ZIPs), or normalized copies from scripts/college_career_ingest.py.
Output: parallel UNITID-keyed enrichment shards; does not overwrite base data or
authorize current-program, accreditation, admissions, or affordability claims.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path

BASE_FIELDS = ("unitid", "name", "city", "state")
REQUIRED_HD = {"UNITID", "LOCALE"}
REQUIRED_C = {"UNITID", "MAJORNUM", "AWLEVEL", "CTOTALT"}
# 12-15 are rollups; 20-21 subdivide level 1. Do not double count.
NONOVERLAPPING_AWLEVELS = {"1", "2", "3", "4", "5", "6", "7", "8", "17", "18", "19"}
SOURCE_LINKS = {
    "directory": "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip",
    "completions": "https://nces.ed.gov/ipeds/complete-data-files/C2025_A.zip",
}
VALID_LOCALES = {str(group * 10 + digit) for group in range(1, 5) for digit in range(1, 4)}


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv(path, expected_name, required):
    """Read one named CSV from a ZIP, excluding macOS sidecars, or a plain CSV."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            candidates = [x for x in archive.namelist()
                          if Path(x).name.lower() == expected_name.lower()
                          and not x.startswith("__MACOSX/") and not Path(x).name.startswith("._")]
            if len(candidates) != 1:
                raise ValueError(f"Expected exactly one {expected_name} inside {path.name}")
            with archive.open(candidates[0]) as raw:
                with io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as stream:
                    yield from checked_rows(stream, required)
    else:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from checked_rows(stream, required)


def checked_rows(stream, required):
    reader = csv.DictReader(stream)
    columns = reader.fieldnames or []
    if len(columns) != len(set(columns)) or any(not col for col in columns):
        raise ValueError("Blank or duplicated CSV headers")
    missing = required - set(columns)
    if missing:
        raise ValueError("Missing required IPEDS fields: " + ", ".join(sorted(missing)))
    if "CIP6" in required and "CIP6" not in columns and "CIPCODE" not in columns:
        raise ValueError("Missing CIP6/CIPCODE")
    for row in reader:
        if None in row:
            raise ValueError("IPEDS row has extra unnamed columns")
        yield row


def national_records(folder):
    folder = Path(folder)
    manifest = load_json(folder / "manifest.v1.json")
    if manifest.get("expected_records", 0) < 1 or not manifest.get("shards"):
        raise ValueError("National Scorecard manifest is incomplete")
    seen = set()
    shards = []
    for descriptor in manifest["shards"]:
        name = descriptor["file"]
        if not re.fullmatch(r"national-\d\d\.json", name):
            raise ValueError("Invalid national shard path")
        path = folder / name
        if digest(path) != descriptor["sha256"]:
            raise ValueError(f"National shard integrity mismatch: {name}")
        source = load_json(path)
        records = source.get("records")
        if source.get("part") != int(name[9:11]) or len(records) != descriptor["count"]:
            raise ValueError(f"National shard row count or part mismatch: {name}")
        for record in records:
            unitid = record[0]
            if not isinstance(unitid, str) or not re.fullmatch(r"\d{6}|\d{8}", unitid):
                raise ValueError("Malformed Scorecard UNITID")
            if unitid in seen:
                raise ValueError(f"Duplicate Scorecard UNITID: {unitid}")
            seen.add(unitid)
        shards.append((name, records))
    if len(seen) != manifest["expected_records"]:
        raise ValueError("National row count does not match manifest")
    return manifest, shards


def normalize_cip(value):
    token = str(value or "").strip()
    if re.fullmatch(r"\d{2}\.\d{4}", token):
        token = token.replace(".", "")
    if not re.fullmatch(r"\d{6}", token):
        return None
    if token.startswith("99") or token == "000099":
        return None
    return token


def count_value(value):
    raw = str(value or "").strip()
    if raw.upper() in {"", "PS", "NA", "N/A", "NULL", "-1", "-2"}:
        return None
    if not re.fullmatch(r"\d+(?:\.0+)?", raw):
        raise ValueError(f"Invalid completion count {raw!r}")
    return int(float(raw))


def build_enrichment(base_shards, hd_rows, completion_rows):
    base_ids = {record[0] for _, records in base_shards for record in records}
    directory = {}
    warnings = []
    for item in hd_rows:
        key = (item.get("UNITID") or "").strip()
        if not re.fullmatch(r"\d{6}", key):
            continue
        if key in directory:
            raise ValueError(f"Duplicate HD2025 UNITID: {key}")
        directory[key] = item
    # Keyed by precise UNITID. Eight-digit extensions are never coerced to parent IDs.
    activity = defaultdict(dict)
    summary_skipped = second_skipped = rollup_skipped = 0
    program_rows = 0
    for row in completion_rows:
        key = (row.get("UNITID") or "").strip()
        major = str(row.get("MAJORNUM") or "").strip()
        code = normalize_cip(row.get("CIP6") or row.get("CIPCODE"))
        level = str(row.get("AWLEVEL") or "").strip()
        if not code:
            summary_skipped += 1
            continue
        if major == "2":
            second_skipped += 1
            continue
        if major not in {"1", ""}:
            raise ValueError(f"Unsupported MAJORNUM {major!r}")
        if level not in NONOVERLAPPING_AWLEVELS:
            rollup_skipped += 1
            continue
        if not re.fullmatch(r"\d{6}", key):
            continue
        unique = (code, level)
        if unique in activity[key]:
            raise ValueError(f"Duplicate first-major program record: {key} {unique}")
        activity[key][unique] = count_value(row.get("CTOTALT"))
        program_rows += 1

    shards_out = []
    matched_directory = matched_activity = locale_covered = locale_disagreements = 0
    cip2_institutions = set()
    for shard_name, records in base_shards:
        enriched = []
        for base in records:
            unitid = base[0]
            hd = directory.get(unitid)
            if hd:
                matched_directory += 1
            locale = str(hd.get("LOCALE") or "").strip() if hd else ""
            locale = locale if locale in VALID_LOCALES else None
            if locale:
                locale_covered += 1
                if base[18] is not None and str(base[18]) != locale:
                    locale_disagreements += 1
                    warnings.append({"unitid": unitid, "field": "LOCALE",
                                     "scorecard": base[18], "ipeds": locale})
            programs = activity.get(unitid, {})
            if programs:
                matched_activity += 1
            families = defaultdict(lambda: {"cip6": set(), "award_levels": set(),
                                             "reported_awards": 0, "suppressed_or_missing_counts": 0})
            for (cip, award), count in programs.items():
                family = families[cip[:2]]
                family["cip6"].add(cip)
                family["award_levels"].add(award)
                if count is None:
                    family["suppressed_or_missing_counts"] += 1
                else:
                    family["reported_awards"] += count
            if families:
                cip2_institutions.add(unitid)
            compact_families = [
                [cip2, len(entry["cip6"]), sorted(entry["award_levels"], key=int),
                 entry["reported_awards"], entry["suppressed_or_missing_counts"]]
                for cip2, entry in sorted(families.items())
            ]
            enriched.append([unitid, locale, compact_families])
        shards_out.append((shard_name.replace("national-", "enrichment-"), enriched))
    return shards_out, {
        "institution_records": len(base_ids),
        "exact_six_digit_hd2025_matches": matched_directory,
        "independent_ipeds_locale_cells": locale_covered,
        "scorecard_ipeds_locale_disagreements": locale_disagreements,
        "institutions_with_2024_25_first_major_completions": matched_activity,
        "institutions_with_recent_cip2_completion_activity": len(cip2_institutions),
        "first_major_nonoverlapping_award_records_examined": program_rows,
        "summary_or_invalid_cip_rows_excluded": summary_skipped,
        "second_major_rows_excluded": second_skipped,
        "rollup_or_overlapping_award_rows_excluded": rollup_skipped,
        "unmatched_or_extension_records": len(base_ids) - matched_directory,
        "locale_disagreement_review_sample": warnings[:100],
        "new_admission_or_program_eligibility_claims_authorized": False,
    }


def build(base_folder, hd_path, c_path, output_folder):
    base_manifest, base_shards = national_records(base_folder)
    enriched, coverage = build_enrichment(
        base_shards,
        read_csv(hd_path, "hd2025.csv", REQUIRED_HD),
        read_csv(c_path, "c2025_a.csv", REQUIRED_C),
    )
    output = Path(output_folder)
    output.mkdir(parents=True, exist_ok=True)
    shards = []
    for name, records in enriched:
        payload = {"schema_version": "1.0", "records": records}
        data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + "\n"
        path = output / name
        path.write_text(data, encoding="utf-8")
        shards.append({"file": name, "count": len(records), "sha256": digest(path)})
    report = {
        "schema_version": "1.0",
        "release": "2025 provisional IPEDS; completions July 2024–June 2025",
        "scorecard_data_version": base_manifest["data_version"],
        "hd2025_input_sha256": digest(hd_path),
        "c2025_a_input_sha256": digest(c_path),
        "official_urls": SOURCE_LINKS,
        "counts": coverage,
        "caveats": [
            "Exact UNITID joins only; no eight-digit extension-to-parent inference.",
            "Program families reflect 2024–25 first-major completions, NOT a currently available program catalog.",
            "IPEDS geography is an independent survey value, not a campus-accessibility or housing assessment.",
            "No admissions probability, program rank, net-price cohort-year or accreditation standing verification.",
        ],
        "publication_authorized": False,
        "source_authenticity_independently_reviewed": False,
        "row_layout": ["unitid", "ipeds_2025_locale", "first_major_2024_25_cip2_families"],
        "family_row_layout": ["cip2", "distinct_cip6", "award_levels", "reported_awards", "suppressed_or_missing_count_cells"],
        "shards": shards,
    }
    (output / "enrichment.manifest.v1.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "enrichment.coverage.v1.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("national_dir", type=Path)
    parser.add_argument("hd2025_csv_or_zip", type=Path)
    parser.add_argument("c2025_a_csv_or_zip", type=Path)
    parser.add_argument("output_dir", type=Path)
    a = parser.parse_args()
    result = build(a.national_dir, a.hd2025_csv_or_zip, a.c2025_a_csv_or_zip, a.output_dir)
    print(json.dumps(result["counts"], indent=2))


if __name__ == "__main__":
    main()
