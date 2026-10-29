"""Review-only bounded integer-linear inference screen for NYC 311 releases.

This is a necessary, never-sufficient disclosure check. It examines every
primitive zero-sum integer contrast with coefficients in [-2, 2] and total
absolute weight <= 8, across 3-8 snapshots. It cannot authenticate the
underlying source, mapping, or external auxiliary evidence. It never approves
publication or returns data values, names, timestamps, or cell coordinates.
"""
from itertools import product
from math import gcd

from multi_release_disclosure_gate import audit as baseline_audit, _projection
from paired_release_differencing_gate import _read_snapshot

MAX_ABS_COEFFICIENT = 2
MAX_TOTAL_WEIGHT = 8
NEW_CODES = ('SMALL_BOUNDED_LINEAR_CELL_CONTRAST',
             'SMALL_BOUNDED_LINEAR_BOROUGH_CONTRAST',
             'SMALL_BOUNDED_LINEAR_GROUP_CONTRAST')


def _contrasts(n):
    """Generate primitive, sign-canonical, translation-invariant contrasts."""
    for coeffs in product(range(-MAX_ABS_COEFFICIENT,
                                MAX_ABS_COEFFICIENT + 1), repeat=n):
        if sum(coeffs) != 0 or sum(abs(x) for x in coeffs) > MAX_TOTAL_WEIGHT:
            continue
        first = next((x for x in coeffs if x), None)
        if first is None or first < 0:
            continue
        divisor = 0
        for x in coeffs:
            divisor = gcd(divisor, abs(x))
        if divisor != 1:
            continue
        yield coeffs


def audit(payload):
    """Return HOLD codes only; a clean bounded screen is NOT clearance."""
    base = baseline_audit(payload)
    codes = set(base['codes'])
    if ('INVALID_MULTI_RELEASE_CONTRACT' in codes
            or 'MAPPING_FINGERPRINT_MISMATCH' in codes
            or 'INVALID_SNAPSHOT_ORDER' in codes):
        return base
    groups = payload['group_labels']
    snapshots = [_read_snapshot(s, groups) for s in payload['snapshots']]
    projected = [_projection(s[3], groups) for s in snapshots]
    threshold = payload['minimum_disclosure_delta']
    for coefficients in _contrasts(len(projected)):
        for dimension, code in enumerate(NEW_CODES):
            if code in codes:
                continue
            rows = [p[dimension] for p in projected]
            if any(0 < abs(sum(c * row[col] for c, row in zip(coefficients, rows)))
                   < threshold for col in range(len(rows[0]))):
                codes.add(code)
        if all(code in codes for code in NEW_CODES):
            break
    return {'status': 'HOLD', 'publication_approved': False,
            'codes': sorted(codes)}
