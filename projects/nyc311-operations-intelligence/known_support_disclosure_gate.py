"""Private NYC 311 known-support marginal-reconstruction challenge.

Checks the same proposed 5-borough x 4-editorial-group release under both
84-possible-pair and observed-support threat models. This is a necessary-only
linear screen, not a publication decision, provenance check, or integer,
auxiliary-table, and temporal inference audit. Never emit fine labels/counts.
"""
from marginal_reconstruction_audit import audit_marginals

BOROUGHS = ('BRONX', 'BROOKLYN', 'MANHATTAN', 'QUEENS', 'STATEN ISLAND')
ALL_BOROUGHS = BOROUGHS + ('UNSPECIFIED',)
SCHEMA = 'nyc311-known-support-linear-v1'
BASE_CODES = {'SOURCE_COHORT_NOT_AUTHENTICATED',
              'EDITORIAL_MAPPING_NOT_INDEPENDENTLY_VERIFIED',
              'INTEGER_AUXILIARY_AND_TEMPORAL_REVIEW_REQUIRED'}


def audit(payload):
    """Return redacted HOLD codes, never fine counts or cell identities."""
    issues = set(BASE_CODES)
    if not isinstance(payload, dict) or set(payload) != {
            'schema_version', 'dataset_id', 'group_labels', 'agency_to_group',
            'fine_rows', 'minimum_cell_count'}:
        return {'status': 'HOLD', 'publication_approved': False,
                'codes': sorted(issues | {'INVALID_KNOWN_SUPPORT_CONTRACT'})}
    groups, mapping, fine, threshold = (payload[k] for k in (
        'group_labels', 'agency_to_group', 'fine_rows', 'minimum_cell_count'))
    if (payload['schema_version'] != SCHEMA or payload['dataset_id'] != 'erm2-nwe9'
            or not isinstance(groups, list) or len(groups) != 4
            or any(not isinstance(g, str) or not g or g != g.strip() for g in groups)
            or len(set(groups)) != 4 or not isinstance(mapping, dict)
            or len(mapping) != 14 or any(not isinstance(a, str) or not a
                or a != a.strip() or g not in groups for a, g in mapping.items())
            or type(threshold) is not int or threshold < 10
            or not isinstance(fine, list) or not 20 <= len(fine) <= 84):
        return {'status': 'HOLD', 'publication_approved': False,
                'codes': sorted(issues | {'INVALID_KNOWN_SUPPORT_CONTRACT'})}
    counts = {}
    for row in fine:
        if (not isinstance(row, dict) or set(row) != {'borough', 'agency', 'requests'}
                or row['borough'] not in ALL_BOROUGHS
                or row['agency'] not in mapping
                or type(row['requests']) is not int or row['requests'] <= 0):
            return {'status': 'HOLD', 'publication_approved': False,
                    'codes': sorted(issues | {'INVALID_KNOWN_SUPPORT_CONTRACT'})}
        key = (row['borough'], row['agency'])
        if key in counts:
            return {'status': 'HOLD', 'publication_approved': False,
                    'codes': sorted(issues | {'DUPLICATE_SOURCE_GROUP'})}
        counts[key] = row['requests']
    if (set(a for _, a in counts) != set(mapping)
            or any(not any((b, a) in counts and mapping[a] == g
                           for a in mapping) for b in BOROUGHS for g in groups)):
        return {'status': 'HOLD', 'publication_approved': False,
                'codes': sorted(issues | {'INCOMPLETE_SOURCE_GROUP_COVERAGE'})}

    agencies = sorted(mapping)
    targets = {key for key, value in counts.items() if value < threshold}

    def check(support):
        index = {key: i for i, key in enumerate(support)}
        constraints = []
        for borough in BOROUGHS:
            for group in groups:
                constraints.append({key for key in support
                                    if key[0] == borough and mapping[key[1]] == group})
        for borough in ALL_BOROUGHS:
            constraints.append({key for key in support if key[0] == borough})
        for agency in agencies:
            constraints.append({key for key in support if key[1] == agency})
        coefficients = [[int(key in members) for key in support]
                        for members in constraints]
        totals = [sum(counts.get(key, 0) for key in members)
                  for members in constraints]
        suppressed = [index[key] for key in targets]
        return audit_marginals(coefficients, totals, suppressed)

    all_support = [(b, a) for b in ALL_BOROUGHS for a in agencies]
    known_support = sorted(counts)
    all_result = check(all_support)
    known_result = check(known_support)
    if not all_result['structural_valid'] or not known_result['structural_valid']:
        issues.add('INCONSISTENT_MARGINAL_CONSTRAINTS')
    else:
        code = 'SUPPRESSED_VARIABLE_RECONSTRUCTIBLE_FROM_MARGINALS'
        if code in all_result['codes']:
            issues.add('ALL_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE')
        if code in known_result['codes']:
            issues.add('KNOWN_SUPPORT_SMALL_CELL_RECONSTRUCTIBLE')
        if not targets:
            issues.add('NO_SMALL_SOURCE_TARGETS_IN_SUPPLIED_SNAPSHOT')
    return {'status': 'HOLD', 'publication_approved': False,
            'codes': sorted(issues)}
