"""Private synthetic-first exact integer audit for 20-cell overlapping marginals.

This is NOT a disclosure certification: a 20-variable algebraic model is not
bound to the real candidate's reporting cells, public auxiliary tables, or
successive releases. Source provenance and structural zeros require separate
verification. Never log counts, inferred values, or private input contents.
"""
import argparse
import json
from fractions import Fraction
from pathlib import Path

VERSION = "nyc311-private-multiway-20-v1"
FIELDS = {"schema_version", "bounds", "marginals", "targets",
          "structural_zero_claims", "minimum_cell_count"}
N = 20


def _nonnegative_int(value):
    return type(value) is int and value >= 0


def _forced_equalities(marginals, lows, highs):
    """Exact rational elimination; return forced integer values or infeasibility.

    A forced rational noninteger value rules out integer solutions. Unforced
    values are not certified feasible; remaining integer feasibility is open.
    """
    matrix = []
    for ids, total in marginals:
        members = set(ids)
        matrix.append([Fraction(int(i in members)) for i in range(N)] +
                      [Fraction(total)])
    for i in range(N):
        if highs[i] is not None and lows[i] == highs[i]:
            matrix.append([Fraction(int(j == i)) for j in range(N)] +
                          [Fraction(lows[i])])
    pivot_row = 0
    for col in range(N):
        found = next((r for r in range(pivot_row, len(matrix))
                      if matrix[r][col]), None)
        if found is None:
            continue
        matrix[pivot_row], matrix[found] = matrix[found], matrix[pivot_row]
        factor = matrix[pivot_row][col]
        matrix[pivot_row] = [v / factor for v in matrix[pivot_row]]
        for r in range(len(matrix)):
            if r != pivot_row and matrix[r][col]:
                factor = matrix[r][col]
                matrix[r] = [v - factor * p
                             for v, p in zip(matrix[r], matrix[pivot_row])]
        pivot_row += 1
    if any(not any(row[:N]) and row[N] for row in matrix):
        return None
    fixed = {}
    for row in matrix:
        nonzero = [i for i in range(N) if row[i]]
        if len(nonzero) == 1:
            idx = nonzero[0]
            value = row[N] / row[idx]
            if (value.denominator != 1 or value < lows[idx] or
                    (highs[idx] is not None and value > highs[idx])):
                return None
            fixed[idx] = int(value)
    return fixed


def audit(payload):
    """Conservative finding codes only; never output totals or inferred counts."""
    invalid = ["invalid_multiway_integer_schema"]
    if (not isinstance(payload, dict) or set(payload) != FIELDS or
            payload.get("schema_version") != VERSION):
        return invalid
    bounds = payload["bounds"]
    raw_marginals = payload["marginals"]
    targets = payload["targets"]
    zeros = payload["structural_zero_claims"]
    threshold = payload["minimum_cell_count"]
    if (not isinstance(bounds, list) or len(bounds) != N or
            not isinstance(raw_marginals, list) or not 1 <= len(raw_marginals) <= 120 or
            not isinstance(targets, list) or not targets or
            not isinstance(zeros, list) or
            not _nonnegative_int(threshold) or threshold < 10):
        return invalid
    if (any(not isinstance(b, list) or len(b) != 2 or
            not _nonnegative_int(b[0]) or
            (b[1] is not None and
             (not _nonnegative_int(b[1]) or b[1] < b[0]))
            for b in bounds)):
        return invalid
    if (any(type(i) is not int or not 0 <= i < N for i in targets + zeros)
            or len(set(targets)) != len(targets)
            or len(set(zeros)) != len(zeros)):
        return invalid
    marginals = []
    scopes = set()
    covered = set()
    for marginal in raw_marginals:
        if (not isinstance(marginal, dict) or
                set(marginal) != {"cells", "total"}):
            return invalid
        ids, total = marginal["cells"], marginal["total"]
        if (not isinstance(ids, list) or not ids or
                any(type(i) is not int or not 0 <= i < N for i in ids) or
                len(set(ids)) != len(ids) or not _nonnegative_int(total)):
            return invalid
        scope = frozenset(ids)
        if scope in scopes:
            return invalid
        scopes.add(scope)
        covered.update(ids)
        marginals.append((ids, total))
    lows = [b[0] for b in bounds]
    highs = [b[1] for b in bounds]
    incomplete = True
    for _ in range(100):
        changed = False
        for ids, total in marginals:
            minimum = sum(lows[i] for i in ids)
            maximum = (sum(highs[i] for i in ids)
                       if all(highs[i] is not None for i in ids) else None)
            if minimum > total or (maximum is not None and maximum < total):
                return ["infeasible_multiway_constraints"]
            for i in ids:
                upper = total - (minimum - lows[i])
                if highs[i] is None or upper < highs[i]:
                    highs[i] = upper
                    changed = True
                others = [j for j in ids if j != i]
                if all(highs[j] is not None for j in others):
                    lower = total - sum(highs[j] for j in others)
                    if lower > lows[i]:
                        lows[i] = lower
                        changed = True
                if highs[i] is not None and lows[i] > highs[i]:
                    return ["infeasible_multiway_constraints"]
        fixed = _forced_equalities(marginals, lows, highs)
        if fixed is None:
            return ["infeasible_multiway_integer_constraints"]
        for i, value in fixed.items():
            if lows[i] != value or highs[i] != value:
                lows[i] = highs[i] = value
                changed = True
        if not changed:
            incomplete = False
            break
    issues = {"candidate_20cell_alignment_unverified",
              "integer_multiway_feasibility_not_exhaustively_proven"}
    if incomplete:
        issues.add("multiway_propagation_incomplete")
    if zeros:
        issues.add("structural_zero_claims_not_authenticated")
    if len(covered) != N:
        issues.add("incomplete_multiway_cell_coverage")
    for i in targets:
        lo, hi = lows[i], highs[i]
        if hi is not None and lo == hi:
            issues.add("multiway_target_forced_by_constraints")
            if 0 < lo < threshold:
                issues.add("small_multiway_target_forced_by_constraints")
        elif lo < threshold and (hi is None or hi > 0):
            issues.add("multiway_target_range_includes_small_cells")
    return sorted(issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_constraints", type=Path)
    args = parser.parse_args()
    try:
        findings = audit(json.loads(args.private_constraints.read_text(encoding="utf-8")))
    except (OSError, UnicodeError, ValueError, TypeError):
        findings = ["unreadable_or_invalid_multiway_constraints"]
    print(json.dumps({"hold": True, "publication_approved": False,
                      "findings": findings,
                      "scope": "unbound 20-cell algebraic review; not release clearance"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
