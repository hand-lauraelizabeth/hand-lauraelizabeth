"""Source-free, fail-closed temporal comparison of NYC 311 review candidates.

This is a conservative risk detector, never a release authorization. It does
not verify publisher provenance, unseen suppressed cells, public marginals,
integer reconstruction, or request-level transitions. No cell values or keys
are emitted in findings.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

GRAIN = ("month", "borough", "agency", "problem")
FIELDS = set(GRAIN) | {"requests", "closed_with_valid_interval"}
SCHEMA = "nyc311-review-candidate-v1"
RULE = "month × borough × agency × original API complaint_type"


def _validate(candidate):
    if not isinstance(candidate, dict) or set(candidate) != {
        "schema_version", "dataset_id", "snapshot_as_of", "rules", "aggregates"
    }:
        raise ValueError("Unexpected candidate envelope")
    if candidate["schema_version"] != SCHEMA or candidate["dataset_id"] != "erm2-nwe9":
        raise ValueError("Unexpected candidate schema or dataset")
    label = candidate["snapshot_as_of"]
    if not isinstance(label, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
        raise ValueError("Noncanonical snapshot date")
    try:
        day = dt.date.fromisoformat(label)
    except ValueError as exc:
        raise ValueError("Invalid snapshot date") from exc
    rules = candidate["rules"]
    if not isinstance(rules, dict) or set(rules) != {"grain", "display_minimum_cell_count"}:
        raise ValueError("Unexpected candidate rules")
    floor = rules["display_minimum_cell_count"]
    if rules["grain"] != RULE or type(floor) is not int or floor < 10:
        raise ValueError("Invalid candidate grain or threshold")
    rows = candidate["aggregates"]
    if not isinstance(rows, list):
        raise ValueError("Invalid candidate aggregates")
    mapping = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Unexpected aggregate fields")
        key = tuple(row[field] for field in GRAIN)
        if any(not isinstance(value, str) or not value.strip() for value in key):
            raise ValueError("Invalid aggregate key")
        if not re.fullmatch(r"\d{4}-\d{2}", key[0]):
            raise ValueError("Noncanonical aggregate month")
        try:
            month = dt.date.fromisoformat(key[0] + "-01")
        except ValueError as exc:
            raise ValueError("Invalid aggregate month") from exc
        if month > day:
            raise ValueError("Aggregate month after snapshot")
        if key in mapping:
            raise ValueError("Duplicate aggregate key")
        n, closed = row["requests"], row["closed_with_valid_interval"]
        if type(n) is not int or n < floor:
            raise ValueError("Unsafe request count")
        if closed is not None:
            if type(closed) is not int or not 0 <= closed <= n:
                raise ValueError("Invalid closure count")
            if 0 < closed < floor or 0 < n - closed < floor:
                raise ValueError("Unsafe closure subgroup")
        mapping[key] = (n, closed)
    return day, floor, mapping


def assess_pair(earlier, later, *, delta_floor=10):
    """Return structural risk codes only; never output counts or cell keys."""
    if type(delta_floor) is not int or delta_floor < 10:
        raise ValueError("Delta review floor must be at least 10")
    day_a, min_a, cells_a = _validate(earlier)
    day_b, min_b, cells_b = _validate(later)
    if day_a >= day_b:
        raise ValueError("Snapshots must be strictly chronologically ordered")
    if min_a != min_b:
        raise ValueError("Threshold changes require a separate disclosure audit")
    # A caller must not weaken the delta gate below the source suppression floor.
    # The stronger of the two floors applies to request and closure deltas.
    effective_delta_floor = max(delta_floor, min_a)
    codes = set()
    if cells_a.keys() != cells_b.keys():
        # Missing is not zero: it could be a suppressed or reclassified cell.
        codes.add("visible_cell_presence_changed")
    for key in cells_a.keys() & cells_b.keys():
        old_n, old_closed = cells_a[key]
        new_n, new_closed = cells_b[key]
        if 0 < abs(new_n - old_n) < effective_delta_floor:
            codes.add("small_visible_request_delta")
        if (old_closed is None) != (new_closed is None):
            codes.add("closure_suppression_state_changed")
        elif old_closed is not None and new_closed is not None:
            if 0 < abs(new_closed - old_closed) < effective_delta_floor:
                codes.add("small_visible_closure_delta")
            # Both published values expose the complementary open count (n - closed).
            # A small open-count delta can be reconstructed even when the two
            # individually tested request/closure deltas are each large.
            old_open, new_open = old_n - old_closed, new_n - new_closed
            if 0 < abs(new_open - old_open) < effective_delta_floor:
                codes.add("small_visible_open_complement_delta")
    # Even zero observed deltas cannot certify safety against external data,
    # reclassification, prior public exports, or source snapshot drift.
    codes.add("external_marginal_and_provenance_review_pending")
    return {"publication_cleared": False,
            "findings": [{"code": code, "severity": "blocker"} for code in sorted(codes)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("earlier_review_candidate", type=Path)
    parser.add_argument("later_review_candidate", type=Path)
    args = parser.parse_args()
    try:
        older = json.loads(args.earlier_review_candidate.read_text(encoding="utf-8"))
        newer = json.loads(args.later_review_candidate.read_text(encoding="utf-8"))
        outcome = assess_pair(older, newer)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
