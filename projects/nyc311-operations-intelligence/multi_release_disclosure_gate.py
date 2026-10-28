"""Private NYC 311 multi-release disclosure screen; NEVER authorizes publication.

Every pair, every three-release second difference and every disjoint 2+2\ncontrast of up to eight releases is checked,
including coarse cells and public marginals. Counts and labels are never emitted.
This is a necessary-only screen; external auxiliary tables and arbitrary integer
linear combinations remain outside its scope.
"""
from itertools import combinations

from paired_release_differencing_gate import (
    BOROUGHS, _read_snapshot,
)

SCHEMA = 'nyc311-multi-release-disclosure-v1'
BASE = {'SOURCE_COHORT_NOT_AUTHENTICATED',
        'MAPPING_PROVENANCE_NOT_AUTHENTICATED',
        'AUXILIARY_AND_SOURCE_LEVEL_PRIVACY_REVIEW_REQUIRED',
        'ARBITRARY_MULTI_RELEASE_LINEAR_INFERENCE_NOT_CLEARED'}


def _result(codes):
    return {'status': 'HOLD', 'publication_approved': False,
            'codes': sorted(codes)}


def _invalid():
    return _result(BASE | {'INVALID_MULTI_RELEASE_CONTRACT'})


def _projection(values, groups):
    # Fixed ordering ensures the output never depends on input row ordering.
    cells = tuple(values[(b, g)] for b in BOROUGHS for g in groups)
    borough = tuple(sum(values[(b, g)] for g in groups) for b in BOROUGHS)
    editorial = tuple(sum(values[(b, g)] for b in BOROUGHS) for g in groups)
    return cells, borough, editorial


def _small(deltas, threshold):
    return any(0 < abs(value) < threshold for value in deltas)


def audit(payload):
    if not isinstance(payload, dict) or set(payload) != {
            'schema_version', 'dataset_id', 'reporting_month',
            'group_labels', 'minimum_disclosure_delta', 'snapshots'}:
        return _invalid()
    groups = payload['group_labels']
    threshold = payload['minimum_disclosure_delta']
    snaps = payload['snapshots']
    if (payload['schema_version'] != SCHEMA
            or payload['dataset_id'] != 'erm2-nwe9'
            or payload['reporting_month'] != '2026-09'
            or not isinstance(groups, list) or len(groups) != 4
            or any(not isinstance(g, str) or not g or g != g.strip()
                   or len(g) > 120 for g in groups)
            or len(set(groups)) != 4
            or type(threshold) is not int or threshold < 10
            or not isinstance(snaps, list) or not 3 <= len(snaps) <= 8):
        return _invalid()
    try:
        rows = [_read_snapshot(s, groups) for s in snaps]
    except (ValueError, TypeError, OverflowError):
        return _invalid()
    codes = set(BASE)
    times = [r[0] for r in rows]
    if any(a >= b for a, b in zip(times, times[1:])):
        codes.add('INVALID_SNAPSHOT_ORDER')
    hashes = {r[2] for r in rows}
    if len(hashes) != 1:
        codes.add('MAPPING_FINGERPRINT_MISMATCH')
        return _result(codes)  # Cross-mapping arithmetic has no common meaning.
    projections = [_projection(r[3], groups) for r in rows]
    for i, j in combinations(range(len(rows)), 2):
        if rows[i][1] == rows[j][1] and rows[i][3] != rows[j][3]:
            codes.add('UNCHANGED_REVISION_WITH_CHANGED_COUNTS')
        for dim, code in enumerate(('SMALL_PAIR_CELL_DIFFERENCE',
                                    'SMALL_PAIR_BOROUGH_DIFFERENCE',
                                    'SMALL_PAIR_GROUP_DIFFERENCE')):
            delta = [b - a for a, b in zip(projections[i][dim], projections[j][dim])]
            if _small(delta, threshold):
                codes.add(code)
            if dim == 0 and any(d < 0 for d in delta):
                codes.add('NEGATIVE_CORRECTION_REVIEW_REQUIRED')
    # Three releases can disclose a small second difference that no pair
    # reveals: 100 - 2*120 + 141 = 1. Test each possible middle
    # coefficient, not only the chronological middle snapshot.
    for chosen in combinations(range(len(rows)), 3):
        for middle in chosen:
            others = [idx for idx in chosen if idx != middle]
            for dim, code in enumerate(('SMALL_THREE_RELEASE_CELL_SECOND_DIFFERENCE',
                                        'SMALL_THREE_RELEASE_BOROUGH_SECOND_DIFFERENCE',
                                        'SMALL_THREE_RELEASE_GROUP_SECOND_DIFFERENCE')):
                first = projections[others[0]][dim]
                second = projections[middle][dim]
                third = projections[others[1]][dim]
                if _small((a + c - 2*b for a, b, c in zip(first, second, third)),
                          threshold):
                    codes.add(code)
    # Four distinct public releases can disclose a small contrast even if no
    # pairwise difference is small: e.g. 100 + 162 - 120 - 141 = 1.
    for chosen in combinations(range(len(rows)), 4):
        # Three distinct partitions of a 4-set into two unordered pairs.
        a, b, c, d = chosen
        for plus, minus in (((a, b), (c, d)),
                            ((a, c), (b, d)),
                            ((a, d), (b, c))):
            for dim, code in enumerate(('SMALL_FOUR_RELEASE_CELL_CONTRAST',
                                        'SMALL_FOUR_RELEASE_BOROUGH_CONTRAST',
                                        'SMALL_FOUR_RELEASE_GROUP_CONTRAST')):
                lhs = [x + y for x, y in zip(projections[plus[0]][dim], projections[plus[1]][dim])]
                rhs = [x + y for x, y in zip(projections[minus[0]][dim], projections[minus[1]][dim])]
                if _small((x - y for x, y in zip(lhs, rhs)), threshold):
                    codes.add(code)
    return _result(codes)
