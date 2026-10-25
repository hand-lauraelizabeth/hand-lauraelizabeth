"""Private QA: fail-closed marginal and paired-snapshot disclosure checks.

This diagnostic never authorizes publication. It does not model external
cross-tabs, integer inference, agency reclassification, or repeated releases.
Only synthetic fixtures belong in repository tests. Do not commit source CSVs.
"""
import argparse
import json
from pathlib import Path

GRAIN = ("month", "borough", "agency", "problem")
FORBIDDEN = {"unique_key", "incident_address", "latitude", "longitude",
             "location", "address", "incident_zip", "descriptor"}


def inspect(payload, previous=None):
    """Return issue codes only; never echo source cells or suppressed values."""
    issues = set()
    if not isinstance(payload, dict):
        return ["invalid_payload"]
    rules = payload.get("rules")
    quality = payload.get("quality")
    rows = payload.get("aggregates")
    if not isinstance(rules, dict) or not isinstance(quality, dict) or not isinstance(rows, list):
        return ["invalid_payload"]
    k = rules.get("display_minimum_cell_count")
    if type(k) is not int or k < 2:
        issues.add("unsafe_or_invalid_threshold")
        k = max(k, 2) if type(k) is int else 2
    suppressed = quality.get("small_cells_suppressed")
    if type(suppressed) is not int or suppressed < 0:
        issues.add("unverified_suppression_metadata")
    elif suppressed:
        # A complete partition plus an exact valid_records marginal reveals
        # the total of the omitted request cells. If just one is omitted,
        # its exact count is recovered. Other quality totals may combine to
        # reveal valid_records even when that field is absent.
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
        if not isinstance(previous, dict) or not isinstance(previous.get("aggregates"), list):
            issues.add("invalid_previous_snapshot")
        elif (previous.get("dataset_id") != payload.get("dataset_id") or
              previous.get("rules", {}).get("grain") != rules.get("grain")):
            issues.add("incompatible_snapshots")
        else:
            earlier = {}
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
                else:
                    issues.add("invalid_previous_snapshot")
            # A small change in a matched published group can expose a
            # change cohort; the gate reports risk, not an individual identity.
            for key in set(public) & set(earlier):
                delta = abs(public[key] - earlier[key])
                if 0 < delta < k:
                    issues.add("small_temporal_difference")
            if set(public) != set(earlier):
                issues.add("changed_published_group_support")
    return sorted(issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--previous", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.candidate.read_text(encoding="utf-8"))
        previous = (json.loads(args.previous.read_text(encoding="utf-8"))
                    if args.previous else None)
        findings = inspect(payload, previous)
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        # Avoid printing file content or paths from parser exceptions.
        findings = ["unreadable_or_invalid_json"]
    print(json.dumps({"hold": bool(findings), "findings": findings,
                      "publication_approved": False,
                      "scope": "partial QA only; external marginals and temporal series untested"}))
    return 2 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
