"""Build a *private-only* NYC 311 September viewer payload from a reconciled CSV.

The API evidence and CSV reconciliation check content, NOT official file origin.
Do not embed output in public pages, join it with borough totals, or infer service quality.
No raw identifiers, addresses, or individual rows are exported.
"""
import argparse
import json
import os
from pathlib import Path
import tempfile

from pipeline import ingest
from reconcile_september_csv import reconcile

PERIOD = '2026-09'
MIN_CELL = 10


def build(csv_path, evidence_path, output_path, *, expected_sha256=None):
    csv_path = Path(csv_path)
    evidence_path = Path(evidence_path)
    output_path = Path(output_path)
    if not csv_path.is_file() or not evidence_path.is_file():
        raise ValueError('Input CSV and pinned API evidence must be existing files')
    if output_path.resolve() in (csv_path.resolve(), evidence_path.resolve()):
        raise ValueError('Refusing to overwrite source material')
    if not output_path.parent.is_dir():
        raise ValueError('Output directory must already exist')
    evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
    audit = reconcile(csv_path, evidence, expected_sha256=expected_sha256)
    # A private aggregate is generated in a scratch directory and promoted
    # only if the independent row audit and payload checks both succeed.
    with tempfile.TemporaryDirectory(prefix='nyc311-review-', dir=output_path.parent) as scratch:
        scratch_file = Path(scratch) / 'aggregate.json'
        payload = ingest(csv_path, scratch_file, as_of=evidence['verification_date'], min_cell=MIN_CELL)
        if (payload.get('publication_authorized') is not False
            or payload.get('source_sha256') != audit['csv_sha256']
            or payload.get('dataset_id') != audit['dataset_id']
            or payload.get('quality', {}).get('rows_read') != audit['rows_reconciled']
            or payload.get('quality', {}).get('valid_records') != audit['rows_reconciled']
            or payload.get('rules', {}).get('display_minimum_cell_count') != MIN_CELL):
            raise ValueError('Aggregate pipeline disagrees with source-bound CSV audit')
        # Suppressed groups can be reconstructed by subtracting published
        # groups from global quality totals. Never export the quality block.
        payload.pop('quality', None)
        payload.pop('source_bytes', None)
        payload['review_status'] = 'PRIVATE_ONLY_SOURCE_ORIGIN_NOT_AUTHENTICATED'
        payload['publication_authorized'] = False
        groups = payload.get('aggregates')
        if not isinstance(groups, list):
            raise ValueError('Missing aggregate groups')
        keys = set()
        for r in groups:
            if (r.get('month') != PERIOD or r.get('requests', 0) < MIN_CELL
                or r.get('borough') not in ('BRONX', 'BROOKLYN', 'MANHATTAN', 'QUEENS', 'STATEN ISLAND', 'UNKNOWN')
                or any(not isinstance(r.get(k), str) or not r[k].strip() or len(r[k]) > 160 for k in ('agency', 'problem'))):
                raise ValueError('Unexpected or unsafe aggregate group')
            key = (r['month'], r['borough'], r['agency'], r['problem'])
            if key in keys:
                raise ValueError('Duplicate aggregate group')
            keys.add(key)
            closed = r.get('closed_with_valid_interval')
            suppressed = r.get('closure_count_suppressed')
            if type(suppressed) is not bool or (closed is None) != suppressed:
                raise ValueError('Invalid suppression state')
            if not suppressed and (type(closed) is not int or closed < MIN_CELL or r['requests'] - closed < MIN_CELL):
                raise ValueError('Unsafe closure complement')
        # Atomic replacement of review output; never overwrite any input.
        tmp = Path(scratch) / 'verified.json'
        tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
        os.replace(tmp, output_path)
    return {'private_review_file': str(output_path), 'groups': len(groups),
            'csv_sha256': audit['csv_sha256'], 'rows_reconciled': audit['rows_reconciled'],
            'source_origin_authenticated': False, 'publication_authorized': False,
            'cross_table_disclosure_review_passed': False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('csv_path', type=Path)
    p.add_argument('api_evidence_json', type=Path)
    p.add_argument('output_json', type=Path)
    p.add_argument('--expect-sha256', default=None)
    args = p.parse_args()
    print(json.dumps(build(args.csv_path, args.api_evidence_json, args.output_json,
                           expected_sha256=args.expect_sha256), sort_keys=True))


if __name__ == '__main__':
    main()
