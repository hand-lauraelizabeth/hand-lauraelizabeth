"""Bounded integer/nonnegative reconstruction preflight (synthetic-only).
No source IDs, suppressed values or sensitive labels may be emitted.
This small-matrix screen never approves release. External, temporal, and
large-system inference require independent review.
"""
MAX_VARIABLES = 8
MAX_CONSTRAINTS = 24
MAX_STATES = 100_000
MAX_TOTAL = 10_000

def audit_integer_feasibility(coefficients, totals, suppressed, sensitive_groups=None):
    """Detect fixed hidden values over exhaustively enumerated integer solutions."""
    hold = {'status': 'HOLD', 'manual_review_required': True}
    if sensitive_groups is None:
        sensitive_groups = []
    if (type(coefficients) is not list or not coefficients or
            len(coefficients) > MAX_CONSTRAINTS or type(totals) is not list or
            len(totals) != len(coefficients) or type(suppressed) is not list or
            type(sensitive_groups) is not list):
        return {**hold, 'codes': ['INVALID_INTEGER_CONTRACT']}
    n = len(coefficients[0]) if type(coefficients[0]) is list else 0
    if not 1 <= n <= MAX_VARIABLES:
        return {**hold, 'codes': ['INTEGER_AUDIT_SCOPE_EXCEEDED']}
    if (any(type(row) is not list or len(row) != n or
            any(type(c) is not int or c < 0 for c in row)
            for row in coefficients) or
            any(type(t) is not int or not 0 <= t <= MAX_TOTAL for t in totals) or
            any(type(i) is not int or not 0 <= i < n for i in suppressed) or
            len(set(suppressed)) != len(suppressed) or
            len(sensitive_groups) > MAX_VARIABLES or
            any(type(group) is not list or not group or len(group) > n or
                len(set(group)) != len(group) or
                any(type(i) is not int or i not in suppressed for i in group)
                for group in sensitive_groups)):
        return {**hold, 'codes': ['INVALID_INTEGER_CONTRACT']}
    bounds = []
    for j in range(n):
        bounded = [total // row[j] for row, total in zip(coefficients, totals)
                   if row[j] > 0]
        if not bounded:
            return {**hold, 'codes': ['UNBOUNDED_INTEGER_VARIABLE']}
        bounds.append(min(bounded))
    product = 1
    for b in bounds:
        product *= b + 1
        if product > MAX_STATES:
            return {**hold, 'codes': ['INTEGER_AUDIT_BUDGET_EXCEEDED']}
    first = None
    variable_fixed = [True] * len(suppressed)
    group_fixed = [True] * len(sensitive_groups)
    solutions = 0
    partial = [0] * len(coefficients)
    values = [0] * n
    def search(j):
        nonlocal first, solutions
        if j == n:
            if any(s != t for s, t in zip(partial, totals)):
                return
            solutions += 1
            signature = (tuple(values[i] for i in suppressed),
                         tuple(sum(values[i] for i in group)
                               for group in sensitive_groups))
            if first is None:
                first = signature
            else:
                for k, val in enumerate(signature[0]):
                    if val != first[0][k]:
                        variable_fixed[k] = False
                for k, val in enumerate(signature[1]):
                    if val != first[1][k]:
                        group_fixed[k] = False
            return
        for v in range(bounds[j] + 1):
            values[j] = v
            updated = [partial[r] + coefficients[r][j] * v
                       for r in range(len(coefficients))]
            if any(updated[r] > totals[r] for r in range(len(totals))):
                break
            old = partial[:]
            partial[:] = updated
            search(j + 1)
            partial[:] = old
    search(0)
    if not solutions:
        return {**hold, 'codes': ['NO_FEASIBLE_INTEGER_ASSIGNMENT']}
    codes = ['INTEGER_AUDIT_LIMITED_SCOPE', 'EXTERNAL_AND_TEMPORAL_REVIEW_REQUIRED']
    if any(variable_fixed):
        codes.append('SUPPRESSED_VARIABLE_INTEGER_RECONSTRUCTIBLE')
    if any(group_fixed):
        codes.append('SENSITIVE_GROUP_SUM_INTEGER_RECONSTRUCTIBLE')
    return {**hold, 'codes': sorted(codes)}
