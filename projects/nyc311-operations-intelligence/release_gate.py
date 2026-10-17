"""Private NYC 311 monthly release gate: exporter manifest + official evidence + raw CSV.

No network access, no publication, and no request-level output. Requiring a dated
manifest and independently checked aggregates is not a claim of immutable source.
"""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import re

from reconcile_csv import COLUMNS, reconcile
from validate_snapshot import DATASET, ENDPOINT, validate


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_release(csv_path, manifest, snapshot):
    """Verify the source export and independent snapshot before approving private QA.

    Only the derived QA status is returned. The raw CSV must remain private.
    """
    contract = validate(snapshot)
    _require(isinstance(manifest, dict), 'manifest must be an object')
    _require(manifest.get('dataset_id') == DATASET, 'manifest dataset mismatch')
    _require(manifest.get('source_endpoint') == ENDPOINT, 'manifest endpoint mismatch')
    _require(manifest.get('month') == contract['month'], 'manifest month mismatch')
    _require(manifest.get('selected_fields') == list(COLUMNS), 'manifest field selection mismatch')
    year, month = map(int, contract['month'].split('-'))
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    expected_where = (f"created_date >= '{start.isoformat()}T00:00:00' "
                      f"AND created_date < '{end.isoformat()}T00:00:00'")
    _require(manifest.get('where') == expected_where, 'manifest scope mismatch')
    _require(manifest.get('paging') == 'unique_key ASC (strict numeric-text key ordering)',
             'manifest paging mismatch')
    size = manifest.get('page_size')
    _require(type(size) is int and 1 <= size <= 5000, 'invalid manifest page size')
    n = contract['requests']
    for field in ('source_count_before', 'source_count_after', 'rows_exported'):
        _require(type(manifest.get(field)) is int and manifest[field] == n,
                 'manifest count mismatch: ' + field)
    _require(type(manifest.get('source_bytes')) is int and manifest['source_bytes'] > 0,
             'invalid manifest byte size')
    checksum = manifest.get('sha256')
    _require(isinstance(checksum, str) and re.fullmatch('[0-9a-f]{64}', checksum) is not None,
             'invalid manifest SHA-256')
    _require(Path(csv_path).stat().st_size == manifest['source_bytes'],
             'manifest file-size mismatch')
    optional = manifest.get('null_or_omitted_optional_fields', {})
    _require(isinstance(optional, dict), 'invalid optional-field counts')
    _require(all(k in COLUMNS[2:] and type(v) is int and 0 <= v <= n
                 for k, v in optional.items()), 'invalid optional-field count')
    stamp = manifest.get('retrieved_utc')
    _require(isinstance(stamp, str), 'missing export timestamp')
    try:
        retrieved = datetime.fromisoformat(stamp)
    except ValueError as exc:
        raise ValueError('invalid export timestamp') from exc
    _require(retrieved.tzinfo is not None and retrieved.utcoffset() is not None,
             'export timestamp must be timezone-aware')
    _require(retrieved.utcoffset().total_seconds() == 0, 'export timestamp must be UTC')
    retrieved_day = retrieved.astimezone(timezone.utc).date()
    checked_day = date.fromisoformat(contract['observation'])
    _require(abs((retrieved_day - checked_day).days) <= 1,
             'aggregate observation too distant from export; recapture aggregates')

    report = reconcile(csv_path, snapshot, pinned_sha256=checksum)
    return {
        'dataset_id': DATASET,
        'month': contract['month'],
        'qa_result': 'PASS: private record-level and manifest reconciliation',
        'records': report['rows'],
        'distinct_ids': report['unique_identifiers'],
        'sha256': report['raw_csv_sha256'],
        'bytes': report['raw_csv_bytes'],
        'aggregate_checked_date': contract['observation'],
        'export_retrieved_utc': retrieved.isoformat(),
        'public_release_approved': False,
        'limitations': ('The source is mutable. Matching counts, fields, checksums and aggregates '
                        'do not establish a transactional snapshot or historical immutability. '
                        'Additional disclosure review and staging approval are required.'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--private-report', required=True)
    args = parser.parse_args()
    target = Path(args.private_report)
    if target.exists():
        raise FileExistsError('Use a new versioned private report filename')
    report = verify_release(args.csv, json.loads(Path(args.manifest).read_text()),
                            json.loads(Path(args.snapshot).read_text()))
    with target.open('x', encoding='utf-8') as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write('\n')
    print(json.dumps({'qa_result': 'PASS', 'rows': report['records'],
                      'public_release_approved': False}))


if __name__ == '__main__':
    main()
