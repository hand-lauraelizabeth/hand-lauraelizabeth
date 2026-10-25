"""Private synthetic-first audit of review candidates against public cross-table totals.

This is a diagnostic, not publication approval. It detects residual inference at
month/borough/agency grain; it cannot establish category support, all public
marginals, independent auxiliary information, or protection over time. Never
include confidential/source row-level records in a repository fixture.
"""
import argparse
import json
from pathlib import Path

from release_privacy_gate import CANDIDATE_VERSION, inspect

MARGINAL_FIELDS = {"month", "borough", "agency", "requests"}
KEY = ("month", "borough", "agency")


def audit(candidate, marginals):
    """Return sorted risk codes, never counts, categories, or source values."""
    issues = set()
    try:
        valid_candidate = (isinstance(candidate, dict) and
                           candidate.get("schema_version") == CANDIDATE_VERSION and
                           not inspect(candidate))
    except (TypeError, ValueError, KeyError):
        valid_candidate = False
    if not valid_candidate:
        return ["cross_table_and_auxiliary_inference_review_pending",
                "invalid_or_unsafe_candidate"]
    if not isinstance(marginals, dict) or set(marginals) != {"dataset_id", "grain", "totals"}:
        return sorted(issues | {"invalid_external_marginal_schema"})
    if (marginals["dataset_id"] != "erm2-nwe9" or
            marginals["grain"] != "month × borough × agency" or
            not isinstance(marginals["totals"], list)):
        return sorted(issues | {"invalid_external_marginal_schema"})
    visible = {}
    for row in candidate.get("aggregates", []) if isinstance(candidate, dict) else []:
        if not isinstance(row, dict):
            continue
        key = tuple(row.get(k) for k in KEY)
        n = row.get("requests")
        if any(not isinstance(k, str) or not k for k in key) or type(n) is not int or n < 0:
            issues.add("invalid_or_unsafe_candidate")
            continue
        visible[key] = visible.get(key, 0) + n
    seen = set()
    for row in marginals["totals"]:
        if not isinstance(row, dict) or set(row) != MARGINAL_FIELDS:
            issues.add("invalid_external_marginal_schema")
            continue
        key = tuple(row.get(k) for k in KEY)
        n = row["requests"]
        if any(not isinstance(k, str) or not k for k in key) or type(n) is not int or n < 0:
            issues.add("invalid_external_marginal_schema")
            continue
        if key in seen:
            issues.add("duplicate_external_marginal")
            continue
        seen.add(key)
        if key not in visible:
            issues.add("external_marginal_without_visible_group")
            continue
        residual = n - visible[key]
        if residual < 0:
            issues.add("external_total_below_visible_sum")
        elif residual > 0:
            issues.add("external_residual_may_reveal_suppressed_categories")
            k = candidate.get("rules", {}).get("display_minimum_cell_count")
            if type(k) is int and 0 < residual < k:
                issues.add("small_external_residual_reconstructible")
    if set(visible) - seen:
        issues.add("unverified_external_marginal_coverage")
    # Even an apparently zero residual is not a comprehensive disclosure review.
    issues.add("cross_table_and_auxiliary_inference_review_pending")
    return sorted(issues)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("candidate", type=Path)
    p.add_argument("external_marginals", type=Path)
    args = p.parse_args()
    try:
        candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
        marginals = json.loads(args.external_marginals.read_text(encoding="utf-8"))
        findings = audit(candidate, marginals)
    except (OSError, UnicodeError, ValueError, TypeError):
        findings = ["unreadable_or_invalid_json"]
    print(json.dumps({"hold": True, "publication_approved": False, "findings": findings}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
