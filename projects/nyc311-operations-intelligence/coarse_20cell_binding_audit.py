"""Private, synthetic-first reconciliation of a 5-borough x 4-group 311 candidate.

Checks internal arithmetic and mapping of a *supplied* complete fine aggregate
snapshot; cannot authenticate its provenance, the original CSV, public marginals,
structural zeros, or repeated releases. Findings never authorize publication.
Never print supplied counts, agencies, digests, or source rows.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

VERSION = "nyc311-coarse-binding-review-v1"
BOROUGHS = ("BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND")
EXCLUDED = "UNSPECIFIED"
FIELDS = {"schema_version", "dataset_id", "month", "snapshot_as_of",
          "source_sha256", "group_labels", "agency_to_group", "fine_rows",
          "coarse_cells", "excluded_requests", "source_total_requests"}
FINE = {"borough", "agency", "requests"}
COARSE = {"borough", "group", "requests"}


def _count(n):
    return type(n) is int and n >= 0


def _labels(items, expected=None):
    return (isinstance(items, list) and (expected is None or len(items) == expected)
            and all(isinstance(x, str) and bool(x.strip()) and x == x.strip()
                    for x in items) and len(items) == len(set(items)))


def audit(payload, expected_source_sha256=None):
    """Return finding codes, never any private cell values."""
    invalid = ["invalid_coarse_binding_schema"]
    if not isinstance(payload, dict) or set(payload) != FIELDS:
        return invalid
    if payload["schema_version"] != VERSION or payload["dataset_id"] != "erm2-nwe9":
        return invalid
    month, asof, digest = (payload[k] for k in ("month", "snapshot_as_of", "source_sha256"))
    try:
        if (not isinstance(month, str) or not re.fullmatch(r"\d{4}-\d{2}", month)
                or not isinstance(asof, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", asof)):
            return invalid
        dt.date.fromisoformat(month + "-01")
        dt.date.fromisoformat(asof)
    except ValueError:
        return invalid
    if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not _labels(payload["group_labels"], 4)
            or not isinstance(payload["agency_to_group"], dict)
            or not payload["agency_to_group"]
            or not isinstance(payload["fine_rows"], list)
            or not isinstance(payload["coarse_cells"], list)
            or not _count(payload["excluded_requests"])
            or not _count(payload["source_total_requests"])):
        return invalid
    groups = set(payload["group_labels"])
    mapping = payload["agency_to_group"]
    if (any(not isinstance(a, str) or not a.strip() or a != a.strip()
            or g not in groups for a, g in mapping.items())
            or len(payload["fine_rows"]) > 100000):
        return invalid

    findings = {"source_provenance_not_authenticated",
                "public_auxiliary_marginals_not_reconciled",
                "temporal_reconstruction_not_reconciled",
                "editorial_group_definitions_not_independently_verified"}
    if expected_source_sha256 is None:
        findings.add("independent_source_digest_not_supplied")
    elif (not isinstance(expected_source_sha256, str)
          or not re.fullmatch(r"[0-9a-f]{64}", expected_source_sha256)):
        findings.add("invalid_expected_source_digest")
    elif digest != expected_source_sha256:
        findings.add("source_digest_mismatch")

    fine = {}
    total = 0
    excluded = 0
    seen = set()
    for row in payload["fine_rows"]:
        if (not isinstance(row, dict) or set(row) != FINE
                or not isinstance(row["borough"], str)
                or not isinstance(row["agency"], str)
                or not row["agency"].strip() or not _count(row["requests"])):
            return invalid
        borough, agency, count = row["borough"], row["agency"], row["requests"]
        if borough not in BOROUGHS + (EXCLUDED,):
            findings.add("unexpected_source_borough")
            continue
        key = (borough, agency)
        if key in seen:
            findings.add("duplicate_fine_group")
            continue
        seen.add(key)
        total += count
        if borough == EXCLUDED:
            excluded += count
        if agency not in mapping:
            findings.add("unmapped_source_agency")
        elif borough in BOROUGHS:
            coarse_key = (borough, mapping[agency])
            fine[coarse_key] = fine.get(coarse_key, 0) + count

    cells = {}
    for row in payload["coarse_cells"]:
        if (not isinstance(row, dict) or set(row) != COARSE
                or not isinstance(row["borough"], str)
                or not isinstance(row["group"], str)
                or not _count(row["requests"])):
            return invalid
        key = (row["borough"], row["group"])
        if key in cells:
            findings.add("duplicate_coarse_cell")
        cells[key] = row["requests"]
        if row["requests"] < 10:
            findings.add("coarse_cell_below_display_threshold")
    expected = {(b, g) for b in BOROUGHS for g in groups}
    if set(cells) != expected or len(payload["coarse_cells"]) != 20:
        findings.add("incomplete_or_extra_coarse_grid")
    if ("unmapped_source_agency" not in findings
            and "duplicate_fine_group" not in findings
            and "unexpected_source_borough" not in findings
            and (set(cells) != expected or any(cells[key] != fine.get(key, 0)
                                               for key in expected))):
        findings.add("coarse_counts_do_not_reconcile")
    if excluded != payload["excluded_requests"]:
        findings.add("excluded_borough_count_mismatch")
    if total != payload["source_total_requests"]:
        findings.add("source_total_count_mismatch")
    return sorted(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_manifest", type=Path)
    parser.add_argument("--expected-source-sha256",
                        help="Independent expected digest; matching is not origin authentication")
    args = parser.parse_args()
    try:
        findings = audit(json.loads(args.private_manifest.read_text(encoding="utf-8")),
                         args.expected_source_sha256)
    except (OSError, UnicodeError, ValueError, TypeError):
        findings = ["unreadable_or_invalid_coarse_binding_manifest"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings,
                      "scope": "internal 20-cell arithmetic only; source origin, auxiliary data and temporal safety unverified"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
