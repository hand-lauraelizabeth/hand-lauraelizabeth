"""Private QA: fail-closed marginal and paired-snapshot disclosure checks.

This diagnostic never authorizes publication. External marginal, exact 2x2,
and unbound 20-cell multiway checks are partial; they do not establish safety
for candidate data, agency reclassification, arbitrary overlaps, or releases.
Only synthetic fixtures belong in repository tests. Do not commit source CSVs.
"""
import argparse
import calendar
import datetime as dt
import json
from pathlib import Path

GRAIN = ("month", "borough", "agency", "problem")
FORBIDDEN = {"unique_key", "incident_address", "latitude", "longitude",
             "location", "address", "incident_zip", "descriptor"}
CANDIDATE_FIELDS = {"schema_version", "dataset_id", "snapshot_as_of",
                    "rules", "aggregates"}
CANDIDATE_RULES = {"grain", "display_minimum_cell_count"}
AGGREGATE_FIELDS = set(GRAIN) | {"requests", "closed_with_valid_interval"}
CANDIDATE_VERSION = "nyc311-review-candidate-v1"
EXPECTED_GRAIN = "month × borough × agency × original API complaint_type"


def inspect(payload, previous=None):
    """Return issue codes only; never echo source cells or suppressed values."""
    issues = set()
    if not isinstance(payload, dict):
        return ["invalid_payload"]
    rules = payload.get("rules")
    quality = payload.get("quality")
    rows = payload.get("aggregates")
    candidate = payload.get("schema_version") == CANDIDATE_VERSION
    if "schema_version" in payload:
        if not candidate or set(payload) != CANDIDATE_FIELDS:
            return ["invalid_candidate_schema"]
        if (payload.get("dataset_id") != "erm2-nwe9" or
                not isinstance(rules, dict) or set(rules) != CANDIDATE_RULES or
                rules.get("grain") != EXPECTED_GRAIN or not isinstance(rows, list)):
            return ["invalid_candidate_schema"]
        snapshot = payload.get("snapshot_as_of")
        try:
            if not isinstance(snapshot, str) or len(snapshot) != 10:
                raise ValueError("Invalid snapshot date")
            dt.date.fromisoformat(snapshot)
        except ValueError:
            return ["invalid_candidate_schema"]
    elif not isinstance(rules, dict) or not isinstance(quality, dict) or not isinstance(rows, list):
        return ["invalid_payload"]
    k = rules.get("display_minimum_cell_count")
    if type(k) is not int or k < (10 if candidate else 2):
        issues.add("unsafe_or_invalid_threshold")
        k = max(k, 10 if candidate else 2) if type(k) is int else (10 if candidate else 2)
    if not candidate:
        suppressed = quality.get("small_cells_suppressed")
        if type(suppressed) is not int or suppressed < 0:
            issues.add("unverified_suppression_metadata")
        elif suppressed:
            # Exact private QA totals may reconstruct a withheld partition.
            if any(field in quality for field in ("valid_records", "rows_read",
                                                   "unique_keys_verified")):
                issues.add("exact_quality_marginal_with_suppressed_cells")
            if suppressed == 1 and "valid_records" in quality:
                issues.add("single_suppressed_cell_reconstructible")
    keys = set()
    public = {}
    for row in rows:
        if not isinstance(row, dict):
            issues.add("invalid_aggregate")
            continue
        if FORBIDDEN.intersection(row):
            issues.add("record_level_field")
        if candidate and set(row) != AGGREGATE_FIELDS:
            issues.add("invalid_candidate_aggregate_schema")
        key = tuple(row.get(f) for f in GRAIN)
        if any(not isinstance(x, str) or not x for x in key):
            issues.add("invalid_group_key")
            continue
        if key in keys:
            issues.add("duplicate_group_key")
        keys.add(key)
        n = row.get("requests")
        c = row.get("closed_with_valid_interval")
        if type(n) is not int or n < k:
            issues.add("unsafe_request_cell")
            continue
        if c is not None:
            if type(c) is not int or c < 0 or c > n:
                issues.add("invalid_closure_cell")
            elif 0 < c < k or 0 < n - c < k:
                issues.add("unsafe_closure_subcell")
        public[key] = n
    if previous is not None:
        if (not isinstance(previous, dict) or not isinstance(previous.get("aggregates"), list) or
                not isinstance(previous.get("rules"), dict)):
            issues.add("invalid_previous_snapshot")
        elif (previous.get("dataset_id") != payload.get("dataset_id") or
              previous.get("rules", {}).get("grain") != rules.get("grain") or
              previous.get("schema_version") != payload.get("schema_version") or
              (candidate and previous.get("rules", {}).get("display_minimum_cell_count") != k)):
            issues.add("incompatible_snapshots")
        else:
            if candidate:
                if inspect(previous):
                    issues.add("invalid_previous_snapshot")
                try:
                    if dt.date.fromisoformat(previous["snapshot_as_of"]) > dt.date.fromisoformat(payload["snapshot_as_of"]):
                        issues.add("reverse_snapshot_order")
                except (KeyError, TypeError, ValueError):
                    issues.add("invalid_previous_snapshot")
            earlier = {}
            earlier_closure = {}
            for row in previous["aggregates"]:
                if not isinstance(row, dict):
                    issues.add("invalid_previous_snapshot")
                    continue
                key = tuple(row.get(f) for f in GRAIN)
                n = row.get("requests")
                if (all(isinstance(x, str) and x for x in key) and
                    type(n) is int and n >= 0):
                    if key in earlier:
                        issues.add("duplicate_previous_group_key")
                    earlier[key] = n
                    earlier_closure[key] = row.get("closed_with_valid_interval")
                else:
                    issues.add("invalid_previous_snapshot")
            # A small change in a matched published group can expose a
            # change cohort; the gate reports risk, not an individual identity.
            for key in set(public) & set(earlier):
                delta = abs(public[key] - earlier[key])
                if 0 < delta < k:
                    issues.add("small_temporal_difference")
                if candidate:
                    current = next((r.get("closed_with_valid_interval") for r in rows
                                    if tuple(r.get(f) for f in GRAIN) == key), None)
                    prior = earlier_closure[key]
                    if (current is None) != (prior is None):
                        issues.add("changed_closure_disclosure_support")
                    elif type(current) is int and type(prior) is int:
                        if 0 < abs(current - prior) < k:
                            issues.add("small_temporal_closure_difference")
            if set(public) != set(earlier):
                issues.add("changed_published_group_support")
    return sorted(issues)



def inspect_official_marginal_receipt(payload, receipt):
    """Bind a public four-query receipt to candidate month; never authorize release.

    The receipt's live SoQL calls are not an atomic snapshot. A passing upper
    bound is necessary arithmetic consistency, NOT a full source reconciliation.
    """
    from official_marginal_receipt import audit as audit_receipt
    source_findings = set(audit_receipt(receipt))
    issues = set(source_findings)
    issues.add("official_marginal_receipt_candidate_source_not_authenticated")
    if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
        issues.add("official_marginal_receipt_requires_review_candidate")
        return sorted(issues)
    month = receipt.get("reporting_month") if isinstance(receipt, dict) else None
    if not isinstance(month, str):
        issues.add("official_marginal_receipt_invalid_month")
        return sorted(issues)
    rows = payload.get("aggregates")
    same_month = (isinstance(rows, list) and bool(rows) and
                  all(isinstance(row, dict) and row.get("month") == month for row in rows))
    if not same_month:
        issues.add("official_marginal_receipt_candidate_month_mismatch")
    try:
        if len(month) != 7 or month[4] != "-":
            raise ValueError("Invalid month")
        year, number = map(int, month.split("-"))
        if not (1 <= number <= 12):
            raise ValueError("Invalid month")
        month_end = dt.date(year, number, calendar.monthrange(year, number)[1])
        as_of = dt.date.fromisoformat(payload["snapshot_as_of"])
        if as_of < month_end:
            issues.add("official_marginal_receipt_candidate_before_month_end")
    except (ValueError, TypeError, KeyError, OverflowError):
        issues.add("official_marginal_receipt_invalid_month_or_snapshot")
    # Only compare a necessary upper bound when all four source queries passed
    # schema, scope, category and internal arithmetic checks.
    baseline = {"source_queries_not_atomic", "official_csv_origin_not_authenticated",
                "privacy_and_temporal_release_review_pending"}
    if same_month and source_findings == baseline and all(
            type(row.get("requests")) is int and row["requests"] >= 0 for row in rows):
        cohort = int(receipt["queries"]["cohort"]["rows"][0]["records"])
        if sum(row["requests"] for row in rows) > cohort:
            issues.add("official_marginal_receipt_visible_candidate_exceeds_source")
    return sorted(issues)



def inspect_cross_dimension_receipt(payload, receipt, cross):
    """Check necessary candidate pair bounds against saved public 2D marginals.

    This is arithmetic QA only: the independent public queries are non-atomic,
    a candidate may omit suppressed groups, and source CSV origin is unknown.
    No findings contain categories, private counts, paths or row identifiers.
    """
    from cross_dimension_marginal_receipt import HOLDS, audit as audit_cross
    findings = set(audit_cross(receipt, cross))
    findings.add("cross_dimension_candidate_source_not_authenticated")
    findings.update(inspect_official_marginal_receipt(payload, receipt))
    if (not isinstance(payload, dict) or
            payload.get("schema_version") != CANDIDATE_VERSION or inspect(payload)):
        findings.add("cross_dimension_requires_valid_review_candidate")
        return sorted(findings)
    if findings - (HOLDS | {
            "cross_dimension_candidate_source_not_authenticated",
            "official_marginal_receipt_candidate_source_not_authenticated"}):
        # Never compare against a malformed, differently scoped or
        # inconsistent public source, or a mismatched candidate month.
        return sorted(findings)
    by_pair = {}
    for row in cross["rows"]:
        key = (row["borough"], row["agency"])
        by_pair[key] = int(row["records"])
    candidate_pairs = {}
    for row in payload["aggregates"]:
        key = (row["borough"], row["agency"])
        candidate_pairs[key] = candidate_pairs.get(key, 0) + row["requests"]
    for pair, visible in candidate_pairs.items():
        if pair not in by_pair:
            findings.add("cross_dimension_candidate_pair_absent_from_source")
        elif visible > by_pair[pair]:
            findings.add("cross_dimension_candidate_pair_exceeds_source")
    return sorted(findings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--borough-agency-cross-receipt", type=Path,
                        help="Saved bounded public borough x agency query; requires --official-marginal-receipt; never release clearance")
    parser.add_argument("--official-marginal-receipt", type=Path,
                        help="Saved official public SoQL aggregates; source/date QA only, never release clearance")
    parser.add_argument("--external-marginals", type=Path,
                        help="Private auxiliary-total audit; diagnostic only, never release approval")
    parser.add_argument("--overlap-constraints", type=Path,
                        help="Private exact 2x2 constraints; never proof of candidate-wide disclosure safety")
    parser.add_argument("--multiway-constraints", type=Path,
                        help="Private unbound 20-cell multiway audit; not publication clearance")
    parser.add_argument("--coarse-binding", type=Path,
                        help="Private 5-borough x 4-group source reconciliation manifest; no publication clearance")
    parser.add_argument("--candidate-source-alignment", action="store_true",
                        help="Reconcile visible candidate aggregates with --coarse-binding; arithmetic only, never provenance or release clearance")
    parser.add_argument("--expected-source-sha256",
                        help="Independent expected digest for --coarse-binding; equality is not origin authentication")
    parser.add_argument("--paired-coarse-previous", type=Path,
                        help="Previous private 20-cell manifest; requires --paired-coarse-current")
    parser.add_argument("--paired-coarse-current", type=Path,
                        help="Current private 20-cell manifest; requires --paired-coarse-previous")
    args = parser.parse_args()
    try:
        payload = json.loads(args.candidate.read_text(encoding="utf-8"))
        previous = (json.loads(args.previous.read_text(encoding="utf-8"))
                    if args.previous else None)
        findings = set(inspect(payload, previous))
        if args.official_marginal_receipt:
            try:
                receipt = json.loads(args.official_marginal_receipt.read_text(encoding="utf-8"))
                findings.update(inspect_official_marginal_receipt(payload, receipt))
            except (OSError, UnicodeError, ValueError, TypeError, KeyError, ImportError):
                findings.add("unreadable_or_invalid_official_marginal_receipt")
        if args.borough_agency_cross_receipt:
            if not args.official_marginal_receipt:
                findings.add("cross_dimension_requires_official_marginal_receipt")
            else:
                try:
                    receipt = json.loads(args.official_marginal_receipt.read_text(encoding="utf-8"))
                    cross = json.loads(args.borough_agency_cross_receipt.read_text(encoding="utf-8"))
                    findings.update(inspect_cross_dimension_receipt(payload, receipt, cross))
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, ImportError):
                    findings.add("unreadable_or_invalid_cross_dimension_receipt")
        if args.external_marginals:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("external_marginals_require_review_candidate")
            else:
                try:
                    # Lazy import avoids a circular dependency with the existing
                    # stand-alone external_marginal_audit diagnostic.
                    from external_marginal_audit import audit as audit_external_marginals
                    external = json.loads(args.external_marginals.read_text(encoding="utf-8"))
                    findings.update(audit_external_marginals(payload, external))
                except (OSError, UnicodeError, ValueError, TypeError, ImportError):
                    findings.add("unreadable_or_invalid_external_marginals")
        if args.overlap_constraints:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("overlap_constraints_require_review_candidate")
            else:
                # The 2x2 constraint file is not cryptographically or
                # structurally bound to the candidate's 20-cell aggregation.
                # Do not infer release clearance from an absence of findings.
                findings.add("overlap_constraints_alignment_unverified")
                try:
                    from overlap_integer_audit import audit as audit_overlap
                    constraints = json.loads(args.overlap_constraints.read_text(encoding="utf-8"))
                    findings.update(audit_overlap(constraints))
                except (OSError, UnicodeError, ValueError, TypeError, ImportError):
                    findings.add("unreadable_or_invalid_overlap_constraints")
        if args.multiway_constraints:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("multiway_constraints_require_review_candidate")
            else:
                # The 20-variable algebraic model is not bound to the actual
                # candidate groups or authenticated external source marginals.
                # Findings never constitute disclosure clearance.
                findings.add("multiway_constraints_alignment_unverified")
                try:
                    from multiway_integer_audit import audit as audit_multiway
                    constraints = json.loads(args.multiway_constraints.read_text(encoding="utf-8"))
                    findings.update(audit_multiway(constraints))
                except (OSError, UnicodeError, ValueError, TypeError, ImportError):
                    findings.add("unreadable_or_invalid_multiway_constraints")
        if args.expected_source_sha256 is not None and args.coarse_binding is None:
            findings.add("orphan_expected_source_digest")
        if args.coarse_binding:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("coarse_binding_requires_review_candidate")
            else:
                # This source aggregate is NOT yet bound to the fine-grain
                # candidate, authenticated official CSV, or public marginals.
                findings.add("coarse_binding_candidate_alignment_unverified")
                try:
                    from coarse_20cell_binding_audit import audit as audit_coarse_binding
                    manifest = json.loads(args.coarse_binding.read_text(encoding="utf-8"))
                    findings.update(audit_coarse_binding(
                        manifest, args.expected_source_sha256))
                except (OSError, UnicodeError, ValueError, TypeError, ImportError):
                    findings.add("unreadable_or_invalid_coarse_binding")
        if args.candidate_source_alignment and not args.coarse_binding:
            findings.add("candidate_source_alignment_requires_coarse_binding")
        elif args.candidate_source_alignment and args.coarse_binding:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("candidate_source_alignment_requires_review_candidate")
            else:
                # The 20-cell binding is only a supplied aggregate. Even exact
                # candidate equality does not authenticate the official CSV,
                # the unique-key cohort, hidden problem categories, or marginals.
                findings.add("candidate_source_alignment_authentication_pending")
                try:
                    from candidate_coarse_alignment_audit import audit as audit_candidate_source
                    source_binding = json.loads(
                        args.coarse_binding.read_text(encoding="utf-8"))
                    findings.update(audit_candidate_source(payload, source_binding))
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, ImportError):
                    findings.add("unreadable_or_invalid_candidate_source_pair")
        if bool(args.paired_coarse_previous) != bool(args.paired_coarse_current):
            findings.add("paired_coarse_manifest_pair_incomplete")
        elif args.paired_coarse_previous and args.paired_coarse_current:
            if not isinstance(payload, dict) or payload.get("schema_version") != CANDIDATE_VERSION:
                findings.add("paired_coarse_requires_review_candidate")
            else:
                # Paired manifests have NOT been bound to candidate cells,
                # independently authenticated official snapshots or public
                # external marginals. A clean synthetic audit is never approval.
                findings.add("paired_coarse_candidate_alignment_unverified")
                try:
                    from paired_coarse_temporal_audit import audit as audit_paired_coarse
                    old_manifest = json.loads(
                        args.paired_coarse_previous.read_text(encoding="utf-8"))
                    new_manifest = json.loads(
                        args.paired_coarse_current.read_text(encoding="utf-8"))
                    findings.update(audit_paired_coarse(old_manifest, new_manifest))
                except (OSError, UnicodeError, ValueError, TypeError, KeyError, ImportError):
                    findings.add("unreadable_or_invalid_paired_coarse_manifest")
        if isinstance(payload, dict) and payload.get("schema_version") == CANDIDATE_VERSION:
            # Passing modeled checks is NOT a release authorization.
            findings.add("external_marginal_integer_review_pending")
        findings = sorted(findings)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        # Avoid printing file content or paths from parser exceptions.
        findings = ["unreadable_or_invalid_json"]
    print(json.dumps({"hold": bool(findings), "findings": findings,
                      "publication_approved": False,
                      "scope": "partial QA only; candidate mapping, source marginals, integer feasibility and temporal series unverified"}))
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
