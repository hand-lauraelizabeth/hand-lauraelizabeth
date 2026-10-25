"""Private exact 2x2 integer-bound audit for overlapping NYC 311 marginals.

Diagnostic only: never publication approval. It covers a single aligned 2x2
partition, not the 20-cell candidate, all public cross-tabs, or time series.
Only synthetic fixtures belong in version control. Never print private totals.
"""
import argparse
import json
from pathlib import Path

VERSION = "nyc311-private-overlap-2x2-v1"
FIELDS = {"schema_version", "row_totals", "column_totals", "bounds", "targets", "minimum_cell_count"}


def _integer(value):
    return type(value) is int and value >= 0


def audit(payload):
    """Return risk codes without revealing counts or inferred cell values."""
    invalid = ["invalid_overlap_integer_schema"]
    if not isinstance(payload, dict) or set(payload) != FIELDS or payload.get("schema_version") != VERSION:
        return invalid
    rows, cols, bounds, targets = (payload.get(k) for k in
                                   ("row_totals", "column_totals", "bounds", "targets"))
    threshold = payload.get("minimum_cell_count")
    if (not isinstance(rows, list) or len(rows) != 2 or
        not isinstance(cols, list) or len(cols) != 2 or
        not all(_integer(x) for x in rows + cols) or
        not _integer(threshold) or threshold < 10 or
        not isinstance(bounds, list) or len(bounds) != 2 or
        not isinstance(targets, list) or not targets):
        return invalid
    for row in bounds:
        if not isinstance(row, list) or len(row) != 2:
            return invalid
        for item in row:
            if (not isinstance(item, list) or len(item) != 2 or
                not _integer(item[0]) or
                (item[1] is not None and
                 (not _integer(item[1]) or item[1] < item[0]))):
                return invalid
    if any(not isinstance(t, list) or len(t) != 2 or
           any(type(i) is not int or i not in (0, 1) for i in t)
           for t in targets):
        return invalid
    if len({tuple(t) for t in targets}) != len(targets):
        return invalid
    if sum(rows) != sum(cols):
        return ["inconsistent_overlap_totals"]

    # Set x = cell[0,0]. Every other cell is an affine function of x:
    # [x, r0-x], [c0-x, r1-c0+x]. All bounds are exact integers.
    affine = ((1, 0), (-1, rows[0]), (-1, cols[0]),
              (1, rows[1] - cols[0]))
    lower, upper = 0, min(rows[0], cols[0])
    for (slope, intercept), (lo, hi) in zip(affine, (bounds[0] + bounds[1])):
        if slope == 1:
            lower = max(lower, lo - intercept)
            if hi is not None:
                upper = min(upper, hi - intercept)
        else:
            upper = min(upper, intercept - lo)
            if hi is not None:
                lower = max(lower, intercept - hi)
    if lower > upper:
        return ["infeasible_overlap_constraints"]
    issues = {"overlap_integer_review_partial"}
    for r, c in targets:
        slope, intercept = affine[2*r + c]
        target_lo, target_hi = ((lower + intercept, upper + intercept)
                                if slope == 1 else
                                (intercept - upper, intercept - lower))
        if target_lo == target_hi:
            issues.add("integer_target_uniquely_reconstructible")
            if 0 < target_lo < threshold:
                issues.add("small_integer_target_uniquely_reconstructible")
        elif target_lo < threshold and target_hi > 0:
            issues.add("integer_target_range_includes_small_cells")
    return sorted(issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_constraints", type=Path)
    args = parser.parse_args()
    try:
        findings = audit(json.loads(args.private_constraints.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError, TypeError):
        findings = ["unreadable_or_invalid_overlap_constraints"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings,
                      "scope": "single private 2x2 integer overlap only"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
