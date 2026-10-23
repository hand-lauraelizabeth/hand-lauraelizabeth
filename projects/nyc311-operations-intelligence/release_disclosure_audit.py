"""Private, source-free release-disclosure audit for NYC 311 candidate aggregates.

A HOLD result is mandatory: this checks necessary conditions, never grants
publication approval. No request-level data, small values or group labels are
included in the report. It accepts the current 2026-10-23 07ET pipeline schema.
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

SOURCE = 'https://data.cityofnewyork.us/d/erm2-nwe9'
GRAIN = ('month', 'borough', 'agency', 'problem')


def _check(payload):
    if not isinstance(payload, dict):
        raise ValueError('not a mapping')
    if payload.get('source') != SOURCE or payload.get('dataset_id') != 'erm2-nwe9':
        raise ValueError('unrecognized source')
    if not re.fullmatch(r'[0-9a-f]{64}', str(payload.get('source_sha256', ''))):
        raise ValueError('unverified digest syntax')
    if type(payload.get('source_bytes')) is not int or payload['source_bytes'] < 1:
        raise ValueError('invalid source size')
    cutoff = payload.get('snapshot_as_of')
    if not isinstance(cutoff, str):
        raise ValueError('invalid cutoff')
    try:
        dt.date.fromisoformat(cutoff)
    except ValueError:
        raise ValueError('invalid cutoff') from None
    quality, rules, cells = payload.get('quality'), payload.get('rules'), payload.get('aggregates')
    if not isinstance(quality, dict) or not isinstance(rules, dict) or not isinstance(cells, list):
        raise ValueError('invalid schema')
    threshold = rules.get('display_minimum_cell_count')
    if type(threshold) is not int or threshold < 1:
        raise ValueError('invalid threshold')
    for key in ('rows_read', 'valid_records', 'unique_keys_verified', 'small_cells_suppressed'):
        if type(quality.get(key)) is not int or quality[key] < 0:
            raise ValueError('invalid quality counter')
    if quality['rows_read'] != quality['unique_keys_verified'] or quality['valid_records'] > quality['rows_read']:
        raise ValueError('inconsistent record count')
    # The pipeline exports an explicit boolean provenance flag; do not mistake
    # it for a numeric quality counter (bool subclasses int in Python).
    if type(quality.get('supplied_manifest_verified')) is not bool:
        raise ValueError('invalid manifest-verification flag')
    for name, v in quality.items():
        if name == 'supplied_manifest_verified':
            continue
        if type(v) is not int or v < 0:
            raise ValueError('unexpected quality field type')
    seen = set()
    total = 0
    for cell in cells:
        if not isinstance(cell, dict) or set(cell) != set(GRAIN) | {'requests', 'closed_with_valid_interval'}:
            raise ValueError('unreviewed cell fields')
        grain = tuple(cell[k] for k in GRAIN)
        if any(not isinstance(v, str) or not v for v in grain) or grain in seen:
            raise ValueError('invalid or duplicate grain')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', grain[0]) or grain[0] > cutoff[:7]:
            raise ValueError('invalid month')
        seen.add(grain)
        n, c = cell['requests'], cell['closed_with_valid_interval']
        if type(n) is not int or n < threshold or type(c) is not int or c < 0 or c > n:
            raise ValueError('unsafe count')
        total += n
    suppressed = quality['small_cells_suppressed']
    residual = quality['valid_records'] - total
    if residual < 0 or (suppressed == 0 and residual != 0) or (
        suppressed > 0 and not suppressed <= residual <= suppressed * (threshold - 1)
    ):
        raise ValueError('unreconciled suppressed residual')
    return threshold, suppressed, residual


def audit_single(payload):
    """Never emit raw cell values or labels. Always returns HOLD."""
    try:
        threshold, groups, residual = _check(payload)
    except (TypeError, ValueError, KeyError):
        return {'status': 'HOLD', 'structural_valid': False,
                'codes': ['INVALID_AGGREGATE_CONTRACT']}
    codes = []
    if threshold < 10:
        codes.append('THRESHOLD_BELOW_10')
    if groups:
        codes.append('SUPPRESSED_RESIDUAL_EXPOSED_BY_TOTAL')
        lo = max(1, residual - (groups - 1) * (threshold - 1))
        hi = min(threshold - 1, residual - (groups - 1))
        if lo == hi:
            codes.append('SUPPRESSED_CELL_EXACTLY_RECONSTRUCTIBLE')
        elif hi - lo <= 2:
            codes.append('SUPPRESSED_CELL_TIGHTLY_BOUNDED')
    if any(0 < n < threshold for k, n in payload['quality'].items()
           if k not in ('rows_read', 'valid_records', 'unique_keys_verified', 'small_cells_suppressed')):
        codes.append('SMALL_QUALITY_COUNTER_EXPOSED')
    if any(0 < c['closed_with_valid_interval'] < threshold or
           0 < c['requests'] - c['closed_with_valid_interval'] < threshold
           for c in payload['aggregates']):
        codes.append('SMALL_CLOSURE_OR_COMPLEMENT_EXPOSED')
    codes.append('CROSS_TABLE_EXTERNAL_SOURCE_REVIEW_REQUIRED')
    return {'status': 'HOLD', 'structural_valid': True, 'codes': sorted(set(codes)),
            'manual_review_required': True}


def audit_pair(previous, current):
    """Flags disclosure from two candidate snapshots, not observed transitions."""
    a, b = audit_single(previous), audit_single(current)
    codes = set(a['codes']) | set(b['codes'])
    if not a['structural_valid'] or not b['structural_valid']:
        codes.add('UNSAFE_PAIR_INPUT')
    elif previous['rules'] != current['rules']:
        codes.add('INCOMPATIBLE_RULES')
    else:
        if previous['source_sha256'] != current['source_sha256']:
            codes.add('SOURCE_VERSION_CHANGED')
        if previous['snapshot_as_of'] != current['snapshot_as_of']:
            codes.add('CUTOFF_CHANGED')
        before = {tuple(c[k] for k in GRAIN): c for c in previous['aggregates']}
        after = {tuple(c[k] for k in GRAIN): c for c in current['aggregates']}
        if before.keys() != after.keys():
            codes.add('DISPLAY_CELL_SET_CHANGED')
        threshold = previous['rules']['display_minimum_cell_count']
        for k in before.keys() & after.keys():
            if 0 < abs(before[k]['requests'] - after[k]['requests']) < threshold:
                codes.add('SMALL_REQUEST_DELTA_EXPOSED')
            if 0 < abs(before[k]['closed_with_valid_interval'] - after[k]['closed_with_valid_interval']) < threshold:
                codes.add('SMALL_CLOSURE_DELTA_EXPOSED')
        if 0 < abs(previous['quality']['valid_records'] - current['quality']['valid_records']) < threshold:
            codes.add('SMALL_COHORT_TOTAL_DELTA_EXPOSED')
        # Quality fields and invalid-row totals can reveal small changes even
        # when all displayed cells and valid cohort totals remain unchanged.
        # Check every numeric counter; never include counter values in reports.
        old_quality, new_quality = previous['quality'], current['quality']
        if old_quality.keys() != new_quality.keys():
            codes.add('QUALITY_COUNTER_SET_CHANGED')
        if old_quality['supplied_manifest_verified'] != new_quality['supplied_manifest_verified']:
            codes.add('SOURCE_MANIFEST_VERIFICATION_CHANGED')
        for name in (old_quality.keys() & new_quality.keys()) - {'supplied_manifest_verified'}:
            delta = abs(old_quality[name] - new_quality[name])
            if 0 < delta < threshold:
                if name in ('rows_read', 'unique_keys_verified'):
                    codes.add('SMALL_SOURCE_ROW_DELTA_EXPOSED')
                elif name != 'valid_records':
                    codes.add('SMALL_QUALITY_DELTA_EXPOSED')
    return {'status': 'HOLD', 'codes': sorted(codes), 'manual_review_required': True,
            'note': 'Necessary checks only; no request-level transitions inferred.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate_json')
    parser.add_argument('--previous-json')
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    candidate = json.loads(Path(args.candidate_json).read_text(encoding='utf-8'))
    result = (audit_pair(json.loads(Path(args.previous_json).read_text(encoding='utf-8')), candidate)
              if args.previous_json else audit_single(candidate))
    Path(args.report).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('HOLD: independent cross-table and temporal disclosure review required')
    raise SystemExit(2)


if __name__ == '__main__':
    main()
