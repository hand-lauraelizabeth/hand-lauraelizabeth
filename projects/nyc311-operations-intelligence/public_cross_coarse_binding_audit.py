"""Private source-to-coarse audit: public borough×agency receipt vs 20-cell binding.

The public queries are non-atomic, the private fine rows are not proven to
originate from an official CSV, and the editorial grouping is not validated.
Even an exact match is diagnostic only. Never echo labels, counts or digests.
"""
import argparse
import calendar
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path

from coarse_20cell_binding_audit import BOROUGHS, EXCLUDED, audit as audit_binding
from cross_dimension_marginal_receipt import HOLDS as CROSS_HOLDS, audit as audit_cross

BINDING_HOLDS = {
    "source_provenance_not_authenticated",
    "public_auxiliary_marginals_not_reconciled",
    "temporal_reconstruction_not_reconciled",
    "editorial_group_definitions_not_independently_verified",
    "independent_source_digest_not_supplied",
}
HOLDS = {
    "source_csv_origin_unverified",
    "public_source_queries_not_atomic",
    "editorial_group_classification_unverified",
    "integer_and_temporal_disclosure_pending",
}


def audit(binding, receipt, cross):
    """Return codes only, never input data; all outcomes retain release HOLD."""
    issues = set(HOLDS)
    public_findings = set(audit_cross(receipt, cross))
    binding_findings = set(audit_binding(binding))
    if public_findings - CROSS_HOLDS:
        issues.add("invalid_or_inconsistent_public_cross_receipt")
    if binding_findings - BINDING_HOLDS:
        issues.add("invalid_or_inconsistent_private_binding")
    if issues - HOLDS:
        return sorted(issues)
    if binding["month"] != receipt["reporting_month"]:
        return sorted(issues | {"reporting_month_mismatch"})
    try:
        year, month = map(int, binding["month"].split("-"))
        last = dt.date(year, month, calendar.monthrange(year, month)[1])
        if dt.date.fromisoformat(binding["snapshot_as_of"]) < last:
            issues.add("private_snapshot_before_month_end")
    except (ValueError, TypeError, OverflowError):
        issues.add("invalid_snapshot_date")
    if issues - HOLDS:
        return sorted(issues)

    public = {}
    for row in cross["rows"]:
        borough = row["borough"].strip().upper()
        if borough not in BOROUGHS + (EXCLUDED,):
            issues.add("unrecognized_public_borough")
            continue
        key = (borough, row["agency"])
        if key in public:
            issues.add("borough_normalization_collision")
        else:
            public[key] = int(row["records"])
    if issues - HOLDS:
        return sorted(issues)

    private = {(r["borough"], r["agency"]): r["requests"]
               for r in binding["fine_rows"] if r["requests"] > 0}
    if set(public) != set(private):
        issues.add("public_private_source_pair_support_mismatch")
    if any(public.get(k) != n for k, n in private.items()):
        issues.add("public_private_source_pair_count_mismatch")

    public_agencies = {agency for _, agency in public}
    if public_agencies != set(binding["agency_to_group"]):
        issues.add("editorial_mapping_does_not_cover_public_agencies")
    public_coarse = defaultdict(int)
    for (borough, agency), n in public.items():
        if borough in BOROUGHS and agency in binding["agency_to_group"]:
            public_coarse[(borough, binding["agency_to_group"][agency])] += n
    private_coarse = {(r["borough"], r["group"]): r["requests"]
                      for r in binding["coarse_cells"]}
    if any(public_coarse.get(k, 0) != n for k, n in private_coarse.items()):
        issues.add("public_private_coarse_cell_mismatch")
    if sum(public.values()) != binding["source_total_requests"]:
        issues.add("public_private_source_total_mismatch")
    return sorted(issues)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_coarse_binding", type=Path)
    p.add_argument("public_four_query_receipt", type=Path)
    p.add_argument("public_cross_query_receipt", type=Path)
    args = p.parse_args()
    try:
        inputs = [json.loads(path.read_text(encoding="utf-8")) for path in
                  (args.private_coarse_binding, args.public_four_query_receipt,
                   args.public_cross_query_receipt)]
        findings = audit(*inputs)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, ImportError):
        findings = sorted(HOLDS | {"unreadable_or_invalid_source_input"})
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
