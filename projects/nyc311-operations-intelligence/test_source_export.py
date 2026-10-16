"""Offline mocked-source acquisition tests; no real 311 records or network."""
import csv
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from source_export import acquire, month_bounds

def fake_row(key):
    return {'unique_key': str(key), 'created_date': '2026-09-01T12:00:00',
            'closed_date': '', 'agency': 'DOT', 'complaint_type': 'Pothole',
            'borough': 'QUEENS', 'status': 'Open'}

class ExportTests(unittest.TestCase):
    def transport(self, keys, counts=None):
        counts = iter(counts if counts is not None else [len(keys), len(keys)])
        def fetch(params):
            if params.get('$select') == 'count(*) as total':
                return [{'total': str(next(counts))}]
            after = params['$where'].split("unique_key > '")[-1].split("'")[0] if 'unique_key >' in params['$where'] else None
            return [fake_row(k) for k in keys if after is None or str(k) > after][:params['$limit']]
        return fetch

    def test_success_multi_page_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / '2026-09.csv'
            result = acquire('2026-09', output, transport=self.transport(['1','2','3','4','5']),
                             page_size=2, expected_count=5,
                             now=dt.datetime(2026,10,16,tzinfo=dt.timezone.utc))
            self.assertEqual(result['rows_exported'], 5)
            self.assertEqual(result['source_count_before'], result['source_count_after'])
            self.assertEqual(result['retrieved_utc'], '2026-10-16T00:00:00+00:00')
            with output.open(newline='') as f:
                rows=list(csv.DictReader(f))
            self.assertEqual([r['unique_key'] for r in rows], ['1','2','3','4','5'])
            manifest=json.loads(output.with_suffix('.csv.manifest.json').read_text())
            self.assertEqual(manifest['sha256'],result['sha256'])
            self.assertEqual(len(rows[0]),7)
            with self.assertRaises(FileExistsError):
                acquire('2026-09',output,transport=self.transport(['1']),page_size=2)

    def test_fail_closed_on_changed_count(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'data.csv'
            with self.assertRaisesRegex(ValueError,'changed or incomplete'):
                acquire('2026-09',output,transport=self.transport(['1','2'],[2,3]),page_size=2)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.csv.manifest.json').exists())

    def test_fail_closed_on_repeated_key(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'data.csv'
            def broken(params):
                if params.get('$select')=='count(*) as total':return [{'total':'2'}]
                return [fake_row('1'),fake_row('1')]
            with self.assertRaisesRegex(ValueError,'repeated or out of order'):
                acquire('2026-09',output,transport=broken,page_size=2)
            self.assertFalse(output.exists())

    def test_count_mismatch_prevents_download(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'data.csv'
            with self.assertRaisesRegex(ValueError,'expected_count'):
                acquire('2026-09',output,transport=self.transport(['1','2']),expected_count=3)
            self.assertFalse(output.exists())

    def test_month_bounds_and_invalid_inputs(self):
        self.assertEqual(month_bounds('2026-12'),('2026-12-01T00:00:00','2027-01-01T00:00:00'))
        for invalid in ('2026-13','2026-9','2019-01','2026-02-03'):
            with self.assertRaises(ValueError):month_bounds(invalid)
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                acquire('2026-09',Path(d)/'x.csv',page_size=0)

    def test_fail_closed_on_truncated_page(self):
        with tempfile.TemporaryDirectory() as d:
            output=Path(d)/'data.csv'
            def truncated(params):
                if params.get('$select')=='count(*) as total':return [{'total':'3'}]
                return [fake_row('1')]
            with self.assertRaisesRegex(ValueError,'changed or incomplete'):
                acquire('2026-09',output,transport=truncated,page_size=2)
            self.assertFalse(output.exists())

    def test_nullable_soda_fields_are_normalized_and_counted(self):
        # SODA JSON omits empty fields on otherwise valid open requests.
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'sparse.csv'
            first = fake_row('1')
            first.pop('closed_date')
            first.pop('agency')
            second = fake_row('2')
            second['closed_date'] = None
            second.pop('status')
            def sparse(params):
                if params.get('$select') == 'count(*) as total':
                    return [{'total': '2'}]
                return [first, second]
            manifest = acquire('2026-09', output, transport=sparse, page_size=3,
                               expected_count=2)
            with output.open(newline='') as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['closed_date'], '')
            self.assertEqual(rows[0]['agency'], '')
            self.assertEqual(rows[1]['status'], '')
            self.assertEqual(manifest['null_or_omitted_optional_fields'],
                             {'agency': 1, 'closed_date': 2, 'status': 1})
            self.assertEqual(manifest['rows_exported'], 2)

    def test_missing_required_date_rejects_entire_export(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'invalid.csv'
            row = fake_row('1')
            row.pop('created_date')
            def missing(params):
                if params.get('$select') == 'count(*) as total':
                    return [{'total': '1'}]
                return [row]
            with self.assertRaisesRegex(ValueError, 'Missing required source fields'):
                acquire('2026-09', output, transport=missing, page_size=2)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_suffix('.csv.manifest.json').exists())

    def test_nontext_optional_field_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / 'invalid.csv'
            row = fake_row('1')
            row['borough'] = {'unexpected': 'nested'}
            def nested(params):
                if params.get('$select') == 'count(*) as total':
                    return [{'total': '1'}]
                return [row]
            with self.assertRaisesRegex(ValueError, 'Non-text source field'):
                acquire('2026-09', output, transport=nested, page_size=2)
            self.assertFalse(output.exists())

if __name__ == '__main__': unittest.main()
