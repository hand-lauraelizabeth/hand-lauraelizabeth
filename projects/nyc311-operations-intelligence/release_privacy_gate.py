"""Private QA: fail-closed marginal and paired-snapshot disclosure checks.

This diagnostic never authorizes publication. It does not model external
cross-tabs, integer inference, agency reclassification, or repeated releases.
Only synthetic fixtures belong in repository tests. Do not commit source CSVs.
"""
import argparse
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--external-marginals", type=Path,
                        help="Private auxiliary-total audit; diagnostic only, never release approval")
    args = parser.parse_args()
    try:
        payload = json.loads(args.candidate.read_text(encoding="utf-8"))
        previous = (json.loads(args.previous.read_text(encoding="utf-8"))
                    if args.previous else None)
        findings = set(inspect(payload, previous))
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
        if isinstance(payload, dict) and payload.get("schema_version") == CANDIDATE_VERSION:
            # Passing modeled checks is NOT a release authorization.
            findings.add("external_marginal_integer_review_pending")
        findings = sorted(findings)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        # Avoid printing file content or paths from parser exceptions.
        findings = ["unreadable_or_invalid_json"]
    print(json.dumps({"hold": bool(findings), "findings": findings,
                      "publication_approved": False,
                      "scope": "partial QA only; external marginals may be incomplete and temporal series untested"}))
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
