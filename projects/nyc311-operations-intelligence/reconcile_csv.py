"""Private, fail-closed NYC 311 raw CSV reconciliation against a captured API snapshot.

The snapshot must be independently obtained at the same observation period as the CSV.
Only synthetic test data and this code may be committed. Never publish raw identifiers.
"""
import argparse
from collections import Counter
import csv
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import tempfile

from validate_snapshot import validate as validate_aggregate

COLUMNS = ('unique_key', 'created_date', 'closed_date', 'agency',
           'complaint_type', 'borough', 'status')


def reconcile(csv_path, snapshot, *, pinned_sha256=None):
    contract = validate_aggregate(snapshot)
    if pinned_sha256 is not None and not re.fullmatch('[0-9a-f]{64}', pinned_sha256):
        raise ValueError('Invalid pinned SHA-256')
    path = Path(csv_path)
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    checksum = digest.hexdigest()
    if pinned_sha256 is not None and checksum != pinned_sha256:
        raise ValueError('Raw CSV checksum mismatch')

    start = date.fromisoformat(contract['month'] + '-01')
    year, month = start.year, start.month
    end = date(year + (month == 12), month % 12 + 1, 1)
    boroughs, days, complaints = Counter(), Counter(), Counter()
    count = 0
    with tempfile.TemporaryDirectory(prefix='nyc311-keys-') as folder:
        with sqlite3.connect(str(Path(folder) / 'unique.db')) as db:
            db.execute('CREATE TABLE keys (key TEXT PRIMARY KEY) WITHOUT ROWID')
            with path.open('r', encoding='utf-8-sig', newline='') as source:
                rows = csv.DictReader(source)
                if rows.fieldnames != list(COLUMNS):
                    raise ValueError('Unexpected CSV schema or column order')
                for row in rows:
                    if None in row or any(value is None for value in row.values()):
                        raise ValueError('Malformed CSV record')
                    key = row['unique_key']
                    if not re.fullmatch('[0-9]+', key):
                        raise ValueError('Invalid request identifier')
                    try:
                        db.execute('INSERT INTO keys VALUES (?)', (key,))
                    except sqlite3.IntegrityError as exc:
                        raise ValueError('Duplicate request identifier') from exc
                    try:
                        stamp = datetime.fromisoformat(row['created_date'])
                    except ValueError as exc:
                        raise ValueError('Invalid creation timestamp') from exc
                    if stamp.tzinfo is not None or not start <= stamp.date() < end:
                        raise ValueError('Timestamp outside requested month')
                    boroughs[row['borough']] += 1
                    days[stamp.date().isoformat()] += 1
                    complaints[row['complaint_type']] += 1
                    count += 1
                    if count > contract['requests']:
                        raise ValueError('More rows than official count')
    evidence = snapshot['results']
    if count != contract['requests'] or dict(boroughs) != evidence['borough_counts']:
        raise ValueError('Total or borough aggregate mismatch')
    if days != Counter({r['day']: r['requests'] for r in evidence['daily_counts'] if r['requests']}):
        raise ValueError('Daily series mismatch')
    top = evidence['top_complaint_types']
    for item in top:
        if complaints[item['complaint_type']] != item['requests']:
            raise ValueError('Complaint category mismatch')
    if count - sum(complaints[item['complaint_type']] for item in top) != evidence['other_complaint_types_requests']:
        raise ValueError('Other complaint category mismatch')
    return {'dataset_id': contract['dataset_id'], 'month': contract['month'],
            'observation': contract['observation'], 'rows': count,
            'unique_identifiers': count, 'raw_csv_sha256': checksum,
            'raw_csv_bytes': path.stat().st_size, 'raw_record_reconciled': True,
            'limitations': 'Counts match a dated mutable API observation; not an immutable official historical release.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--private-report', required=True)
    parser.add_argument('--pinned-sha256')
    args = parser.parse_args()
    target = Path(args.private_report)
    if target.exists():
        raise FileExistsError('Use a new versioned report filename')
    report = reconcile(args.csv, json.loads(Path(args.snapshot).read_text()), pinned_sha256=args.pinned_sha256)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps({'reconciled': True, 'rows': report['rows'], 'sha256': report['raw_csv_sha256']}))


if __name__ == '__main__':
    main()
