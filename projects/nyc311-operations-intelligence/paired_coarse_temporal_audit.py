"""Private paired-release QA for NYC 311 20-cell coarsened aggregate manifests.

This is a synthetic-first *risk detector*, not a proof of privacy or
official source authenticity. Same-month snapshots may be revised, and
aggregate differences are not individual service-request transitions.
No source rows, cell values, agency names, or hashes are printed.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from coarse_20cell_binding_audit import audit as audit_binding

BOROUGHS = ("BRONX", "BROOKLYN", "MANHATTAN", "QUEENS", "STATEN ISLAND")
MINIMUM = 10


def _cells(manifest, kind):
    if kind == "fine":
        return {(r["borough"], r["agency"]): r["requests"]
                for r in manifest["fine_rows"]}
    return {(r["borough"], r["group"]): r["requests"]
            for r in manifest["coarse_cells"]}


def audit(previous, current):
    """Return risk *codes only*. Never emit private counts or identifiers."""
    if (not isinstance(previous, dict) or not isinstance(current, dict)
            or "invalid_coarse_binding_schema" in audit_binding(previous)
            or "invalid_coarse_binding_schema" in audit_binding(current)):
        return ["invalid_paired_coarse_manifest"]
    # Any inconsistent supplied manifest is unsafe to use for differencing.
    bad = {"unexpected_source_borough", "duplicate_fine_group",
           "unmapped_source_agency", "duplicate_coarse_cell",
           "incomplete_or_extra_coarse_grid", "coarse_counts_do_not_reconcile",
           "excluded_borough_count_mismatch", "source_total_count_mismatch",
           "coarse_cell_below_display_threshold"}
    if bad.intersection(audit_binding(previous)) or bad.intersection(audit_binding(current)):
        return ["inconsistent_paired_coarse_manifest"]

    findings = {"source_identity_cohort_not_reconciled",
                "paired_external_marginals_not_authenticated",
                "temporal_privacy_clearance_pending"}
    if previous["dataset_id"] != current["dataset_id"] or previous["month"] != current["month"]:
        findings.add("incompatible_paired_cohort")
        return sorted(findings)
    if dt.date.fromisoformat(previous["snapshot_as_of"]) >= dt.date.fromisoformat(current["snapshot_as_of"]):
        findings.add("nonincreasing_snapshot_order")
        return sorted(findings)
    if (previous["group_labels"] != current["group_labels"]
            or previous["agency_to_group"] != current["agency_to_group"]):
        findings.add("editorial_group_definition_changed")
        # Counts from different definitions cannot be safely differenced.
        return sorted(findings)

    before = _cells(previous, "coarse")
    after = _cells(current, "coarse")
    if set(before) != set(after):
        findings.add("changed_coarse_cell_support")
        return sorted(findings)
    differences = [after[k] - before[k] for k in before]
    if any(0 < abs(d) < MINIMUM for d in differences):
        findings.add("small_published_coarse_difference")
    if any(d < 0 for d in differences):
        findings.add("decreasing_coarse_cell_revision")
    if 0 < abs(current["excluded_requests"] - previous["excluded_requests"]) < MINIMUM:
        findings.add("small_excluded_borough_difference")
    if 0 < abs(current["source_total_requests"] - previous["source_total_requests"]) < MINIMUM:
        findings.add("small_source_total_difference")

    prior_fine = _cells(previous, "fine")
    next_fine = _cells(current, "fine")
    if set(prior_fine) != set(next_fine):
        findings.add("changed_fine_source_support")
    if any(0 < abs(next_fine[k] - prior_fine[k]) < MINIMUM
           for k in set(prior_fine) & set(next_fine)):
        findings.add("small_fine_source_difference")
    if all(d == 0 for d in differences) and prior_fine != next_fine:
        findings.add("fine_redistribution_masked_by_stable_coarse_totals")
    if (previous["source_sha256"] == current["source_sha256"]
            and (prior_fine != next_fine or any(d != 0 for d in differences)
                 or previous["excluded_requests"] != current["excluded_requests"])):
        findings.add("identical_digest_conflicts_with_changed_aggregates")
    return sorted(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous_private_manifest", type=Path)
    parser.add_argument("current_private_manifest", type=Path)
    args = parser.parse_args()
    try:
        old = json.loads(args.previous_private_manifest.read_text(encoding="utf-8"))
        new = json.loads(args.current_private_manifest.read_text(encoding="utf-8"))
        findings = audit(old, new)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        findings = ["unreadable_or_invalid_paired_coarse_manifest"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings,
                      "scope": "paired coarse aggregate risks only; no record-level cohort authentication"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
