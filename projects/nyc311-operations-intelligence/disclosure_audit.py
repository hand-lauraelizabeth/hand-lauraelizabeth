"""Conservative, source-free disclosure preflight for NYC 311 aggregate exports.

This audit is intentionally a *blocking* preflight, not a publication approval.
It does not inspect request-level records and cannot assess differencing against
other releases, public tables, or temporal snapshots.
"""
import argparse
import json
from pathlib import Path


def assess_export(payload, *, publication_floor=10):
    """Return coded blocking findings without exposing suppressed cell values.

    A private export can contain both exact `quality.valid_records` and
    public aggregate rows. If at least one aggregate row was suppressed,
    subtracting the visible request counts from the exact total reconstructs
    the combined suppressed count; with exactly one suppressed row it
    reconstructs that cell's count exactly.
    """
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    quality = payload.get("quality")
    rows = payload.get("aggregates")
    rules = payload.get("rules")
    if not isinstance(quality, dict) or not isinstance(rows, list) or not isinstance(rules, dict):
        raise ValueError("Missing quality, aggregates, or rules")
    if type(publication_floor) is not int or publication_floor < 1:
        raise ValueError("Invalid publication review floor")
    minimum = rules.get("display_minimum_cell_count")
    suppressed = quality.get("small_cells_suppressed")
    valid = quality.get("valid_records")
    if type(minimum) is not int or minimum < 1:
        raise ValueError("Invalid export minimum")
    if type(suppressed) is not int or suppressed < 0:
        raise ValueError("Invalid suppressed-cell count")
    if type(valid) is not int or valid < 0:
        raise ValueError("Invalid valid-record count")
    visible = 0
    for row in rows:
        if not isinstance(row, dict) or type(row.get("requests")) is not int or row["requests"] < minimum:
            raise ValueError("Malformed visible aggregate row")
        visible += row["requests"]
    if visible > valid:
        raise ValueError("Visible counts exceed valid-record count")

    findings = []
    def block(code, explanation):
        findings.append({"code": code, "severity": "blocker", "explanation": explanation})

    if suppressed:
        # This is a structural inference finding, not an output of the
        # suppressed count itself. Never emit reconstructed small values.
        if suppressed == 1:
            block("exact_suppressed_cell_reconstructable",
                  "Exact valid-record totals and visible counts reveal the sole withheld request cell.")
        else:
            block("suppressed_group_total_reconstructable",
                  "Exact valid-record totals and visible counts reveal the combined withheld requests.")
        if not suppressed <= valid - visible < suppressed * minimum:
            block("suppression_metadata_inconsistent",
                  "Aggregate and suppression metadata violate the configured minimum-cell bounds.")
    elif visible != valid:
        block("aggregate_total_unreconciled",
              "Visible counts do not reconcile with the stated total and no suppressed groups are recorded.")

    if minimum < publication_floor:
        block("publication_threshold_below_review_floor",
              "The configured display threshold is below the conservative publication review floor.")
    if any(row.get("closed_with_valid_interval") is None for row in rows):
        block("closure_subcell_cross_table_review_required",
              "Withheld closure outcomes require independent complementary and cross-table disclosure checks.")
    # Even an internally consistent single export can disclose values when
    # compared with other public or future exports; source authenticity is
    # also outside the scope of this preflight.
    block("cross_release_and_source_review_pending",
          "Publisher provenance and temporal/cross-release disclosure checks have not been established.")
    return {"publication_cleared": False, "findings": findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_aggregate_json", type=Path)
    args = parser.parse_args()
    try:
        result = assess_export(json.loads(args.private_aggregate_json.read_text(encoding="utf-8")))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2  # Preflight is never sufficient to authorize public release.


if __name__ == "__main__":
    raise SystemExit(main())
