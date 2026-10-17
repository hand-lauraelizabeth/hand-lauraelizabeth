"""Private NYC 311 seven-field monthly exporter; never commit raw CSV."""
import argparse
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import urlencode
from urllib.request import urlopen
from reconcile_csv import COLUMNS
from validate_snapshot import DATASET, ENDPOINT

def _month_scope(month):
    if not isinstance(month, str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise ValueError('month must be YYYY-MM')
    year, number = map(int, month.split('-'))
    start = date(year, number, 1)
    stop = date(year + (number == 12), number % 12 + 1, 1)
    return (f"created_date >= '{start.isoformat()}T00:00:00' "
            f"AND created_date < '{stop.isoformat()}T00:00:00'"), start, stop

def fetch_json(params):
    with urlopen(ENDPOINT + '?' + urlencode(params), timeout=40) as response:
        if response.status != 200:
            raise RuntimeError('official API returned non-200')
        return json.load(response)

def _count(fetch, scope):
    payload = fetch({'$select': 'count(*) as n', '$where': scope})
    if (not isinstance(payload, list) or len(payload) != 1 or
        not isinstance(payload[0], dict) or
        not re.fullmatch(r'\d+', str(payload[0].get('n', '')))):
        raise ValueError('invalid official count response')
    return int(payload[0]['n'])

def export(month, csv_path, manifest_path, *, fetch=fetch_json, page_size=5000, retrieved_at=None):
    scope, start, stop = _month_scope(month)
    if type(page_size) is not int or not 1 <= page_size <= 5000:
        raise ValueError('page_size outside 1..5000')
    csv_path, manifest_path = Path(csv_path), Path(manifest_path)
    if csv_path.resolve() == manifest_path.resolve() or csv_path.exists() or manifest_path.exists():
        raise FileExistsError('output paths must be distinct and not already exist')
    if not csv_path.parent.is_dir() or not manifest_path.parent.is_dir():
        raise FileNotFoundError('output directories must exist')
    before = _count(fetch, scope)
    last = None
    exported = 0
    optional_nulls = {k: 0 for k in COLUMNS[2:]}
    with tempfile.TemporaryDirectory(prefix='nyc311-export-', dir=str(csv_path.parent)) as temp:
        tmp_csv = Path(temp) / 'source.csv'
        with tmp_csv.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator='\n')
            writer.writeheader()
            while True:
                where = scope if last is None else scope + f" AND unique_key > '{last}'"
                page = fetch({'$select': ','.join(COLUMNS), '$where': where,
                              '$order': 'unique_key ASC', '$limit': str(page_size)})
                if not isinstance(page, list) or len(page) > page_size:
                    raise ValueError('invalid API page')
                if not page:
                    break
                for item in page:
                    if not isinstance(item, dict) or set(item) - set(COLUMNS):
                        raise ValueError('unexpected field in API response')
                    key = item.get('unique_key')
                    if not isinstance(key, str) or not re.fullmatch(r'[0-9]+', key):
                        raise ValueError('invalid request identifier')
                    if last is not None and key <= last:
                        raise ValueError('non-monotonic or duplicate identifier')
                    stamp = item.get('created_date')
                    try:
                        created = datetime.fromisoformat(stamp)
                    except (TypeError, ValueError) as exc:
                        raise ValueError('invalid created_date') from exc
                    if created.tzinfo is not None or not start <= created.date() < stop:
                        raise ValueError('created_date outside reporting month')
                    row = {}
                    for field in COLUMNS:
                        value = item.get(field)
                        if value is not None and not isinstance(value, str):
                            raise ValueError('unexpected field value type')
                        row[field] = value or ''
                        if field in optional_nulls and not value:
                            optional_nulls[field] += 1
                    writer.writerow(row)
                    last = key
                    exported += 1
                    if exported > before:
                        raise ValueError('more records exported than initial count')
                if len(page) < page_size:
                    break
        after = _count(fetch, scope)
        if before != after or exported != before:
            raise ValueError('mutable-source count mismatch; discard export')
        digest = hashlib.sha256()
        with tmp_csv.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
        timestamp = retrieved_at or datetime.now(timezone.utc)
        if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError('retrieved_at must be UTC')
        manifest = {
            'dataset_id': DATASET, 'source_endpoint': ENDPOINT,
            'month': month, 'where': scope, 'selected_fields': list(COLUMNS),
            'paging': 'unique_key ASC (strict numeric-text key ordering)',
            'page_size': page_size, 'source_count_before': before,
            'source_count_after': after, 'rows_exported': exported,
            'source_bytes': tmp_csv.stat().st_size, 'sha256': digest.hexdigest(),
            'retrieved_utc': timestamp.isoformat(),
            'null_or_omitted_optional_fields': optional_nulls,
            'limitations': ('Mutable API; count-before/after and monotonic keyset paging '
                            'do not prove a transactional snapshot. Independently capture '
                            'dated aggregate queries and reconcile before any staging.'),
        }
        tmp_manifest = Path(temp) / 'manifest.json'
        tmp_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        tmp_csv.replace(csv_path)
        try:
            tmp_manifest.replace(manifest_path)
        except Exception:
            csv_path.unlink(missing_ok=True)
            raise
    return manifest

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--month', required=True)
    parser.add_argument('--private-csv', required=True)
    parser.add_argument('--private-manifest', required=True)
    args = parser.parse_args()
    result = export(args.month, args.private_csv, args.private_manifest)
    print(json.dumps({'rows_exported': result['rows_exported'],
                      'sha256': result['sha256'], 'public_release_approved': False}))

if __name__ == '__main__':
    main()
