"""Private linear-marginal reconstruction screen for proposed NYC 311 aggregate releases.

All inputs must be synthetic or cleared public marginal constraints. No identifiers,
cell names, or values are emitted. This is a necessary-only linear screen, NOT a
release approval: nonnegative/integer, temporal and external-source inference
require independent review. The public-release decision always remains HOLD.
"""
from fractions import Fraction

MAX_VARIABLES = 128
MAX_CONSTRAINTS = 256


def _validate(coefficients, totals, suppressed):
    if (not isinstance(coefficients, list) or not coefficients or
            len(coefficients) > MAX_CONSTRAINTS or not isinstance(totals, list) or
            len(totals) != len(coefficients) or not isinstance(suppressed, list)):
        raise ValueError('invalid matrix dimensions')
    first = coefficients[0]
    if (not isinstance(first, list) or not 1 <= len(first) <= MAX_VARIABLES):
        raise ValueError('invalid variable count')
    width = len(first)
    if (any(not isinstance(row, list) or len(row) != width or
            any(type(x) is not int or x < 0 for x in row)
            for row in coefficients) or
            any(type(x) is not int or x < 0 for x in totals) or
            any(type(x) is not int or not 0 <= x < width for x in suppressed) or
            len(set(suppressed)) != len(suppressed)):
        raise ValueError('invalid constraints')
    return width


def audit_marginals(coefficients, totals, suppressed):
    """Screen uniqueness under linear equalities only; never reveal values."""
    try:
        width = _validate(coefficients, totals, suppressed)
    except (TypeError, ValueError):
        return {'status': 'HOLD', 'structural_valid': False,
                'codes': ['INVALID_MARGINAL_CONTRACT'], 'manual_review_required': True}
    matrix = [[Fraction(v) for v in row] + [Fraction(total)]
              for row, total in zip(coefficients, totals)]
    pivot_rows = {}
    rank = 0
    for col in range(width):
        pivot = next((i for i in range(rank, len(matrix)) if matrix[i][col]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        scale = matrix[rank][col]
        matrix[rank] = [x / scale for x in matrix[rank]]
        for i in range(len(matrix)):
            if i != rank and matrix[i][col]:
                factor = matrix[i][col]
                matrix[i] = [x - factor * y for x, y in zip(matrix[i], matrix[rank])]
        pivot_rows[col] = rank
        rank += 1
        if rank == len(matrix):
            break
    if any(all(x == 0 for x in row[:width]) and row[-1] != 0
           for row in matrix):
        return {'status': 'HOLD', 'structural_valid': False,
                'codes': ['INCONSISTENT_PUBLIC_MARGINALS'], 'manual_review_required': True}
    free_columns = set(range(width)) - pivot_rows.keys()
    uniquely_identified = any(
        col in pivot_rows and all(matrix[pivot_rows[col]][free] == 0 for free in free_columns)
        for col in suppressed
    )
    codes = ['INTEGER_BOUND_EXTERNAL_AND_TEMPORAL_REVIEW_REQUIRED']
    if uniquely_identified:
        codes.append('SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS')
    if free_columns:
        codes.append('UNDERDETERMINED_LINEAR_SYSTEM')
    return {'status': 'HOLD', 'structural_valid': True, 'codes': sorted(codes),
            'manual_review_required': True}
