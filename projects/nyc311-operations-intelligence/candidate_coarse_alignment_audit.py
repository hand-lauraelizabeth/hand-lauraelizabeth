"""Private candidate-to-source reconciliation for NYC 311 review aggregates.

Compare the fine candidate's visible problem cells against a separately supplied
20-cell source-binding manifest. This checks aggregate arithmetic, NOT whether
the manifest is official, complete, or derived from the claimed CSV. Suppressed
candidate categories can make coverage incomplete; do not interpret residuals
as a count of identifiable people. No source data or counts are printed.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from coarse_20cell_binding_audit import BOROUGHS, audit as audit_binding
from release_privacy_gate import CANDIDATE_VERSION, inspect


BLOCKING_BINDING = {
    "invalid_coarse_binding_schema", "unexpected_source_borough",
    "duplicate_fine_group", "unmapped_source_agency", "duplicate_coarse_cell",
    "incomplete_or_extra_coarse_grid", "coarse_counts_do_not_reconcile",
    "excluded_borough_count_mismatch", "source_total_count_mismatch",
    "coarse_cell_below_display_threshold",
}


def audit(candidate, manifest):
    """Return only finding codes. Never return source counts or agency labels."""
    if (not isinstance(candidate, dict)
            or candidate.get("schema_version") != CANDIDATE_VERSION
            or inspect(candidate)):
        return ["invalid_or_unsafe_review_candidate"]
    binding_findings = set(audit_binding(manifest))
    if binding_findings & BLOCKING_BINDING:
        return ["invalid_or_inconsistent_source_binding"]
    # The binding audit validates the shape of every row before this point.
    findings = {"candidate_source_provenance_not_authenticated",
                "external_marginals_and_temporal_disclosure_pending"}
    if candidate["dataset_id"] != manifest["dataset_id"]:
        findings.add("candidate_source_dataset_mismatch")
        return sorted(findings)
    if candidate["snapshot_as_of"] != manifest["snapshot_as_of"]:
        findings.add("candidate_source_snapshot_mismatch")

    source = {(r["borough"], r["agency"]): r["requests"]
              for r in manifest["fine_rows"] if r["borough"] in BOROUGHS}
    source_groups = {(r["borough"], r["group"]): r["requests"]
                     for r in manifest["coarse_cells"]}
    candidate_fine = defaultdict(int)
    candidate_groups = defaultdict(int)
    observed = set()
    mapping = manifest["agency_to_group"]
    for row in candidate["aggregates"]:
        if row["month"] != manifest["month"]:
            findings.add("candidate_source_month_mismatch")
            continue
        borough, agency = row["borough"], row["agency"]
        if borough not in BOROUGHS:
            findings.add("candidate_excluded_or_unexpected_borough")
            continue
        if agency not in mapping or (borough, agency) not in source:
            findings.add("candidate_agency_not_in_source_binding")
            continue
        key = (borough, agency)
        observed.add(key)
        candidate_fine[key] += row["requests"]
        candidate_groups[(borough, mapping[agency])] += row["requests"]

    for key, source_count in source.items():
        visible = candidate_fine[key]
        if visible > source_count:
            findings.add("candidate_agency_total_exceeds_source")
        elif visible < source_count:
            findings.add("candidate_source_coverage_incomplete")
            if 0 < source_count - visible < candidate["rules"]["display_minimum_cell_count"]:
                findings.add("small_unpublished_source_residual")
        if source_count and key not in observed:
            findings.add("source_agency_missing_from_candidate")

    for key, source_count in source_groups.items():
        visible = candidate_groups[key]
        if visible > source_count:
            findings.add("candidate_coarse_cell_exceeds_source")
        elif visible < source_count:
            findings.add("candidate_coarse_cell_undercovered")

    # Even equality for every agency and group cannot prove category-level
    # completeness, source identity, or the absence of balanced tampering.
    return sorted(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_candidate", type=Path)
    parser.add_argument("private_source_binding", type=Path)
    args = parser.parse_args()
    try:
        candidate = json.loads(args.private_candidate.read_text(encoding="utf-8"))
        manifest = json.loads(args.private_source_binding.read_text(encoding="utf-8"))
        findings = audit(candidate, manifest)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        findings = ["unreadable_or_invalid_candidate_source_pair"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings,
                      "scope": "private arithmetic reconciliation only; source provenance, unique keys, suppressed categories, external marginals and temporal risk unverified"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
