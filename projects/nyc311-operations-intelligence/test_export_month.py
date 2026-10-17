"""Offline regression tests for the private September exporter."""
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from export_month import export, _month_scope
from reconcile_csv import COLUMNS

def item(n):
    return {'unique_key':str(n),'created_date':'2026-09-12T12:30:00',
            **{k:'BROOKLYN' if k=='borough' else 'sample' for k in COLUMNS[2:]}}

def fake_fetch(*, duplicate=False, bad_date=False, drift=False):
    def fetch(params):
        if params.get('$select') == 'count(*) as n':
            return [{'n': '3' if not drift else '4'}]
        rows = [item(101),item(102),item(103)]
        if duplicate: rows[2]['unique_key']='102'
        if bad_date: rows[2]['created_date']='2026-10-01T00:00:00'
        where=params['$where']
        import re
        m=re.search(r"unique_key > '([0-9]+)'",where)
        if m: rows=[r for r in rows if r['unique_key'] > m.group(1)]
        return rows[:int(params['$limit'])]
    return fetch

class ExportTests(unittest.TestCase):
    def test_scope(self):
        self.assertIn('2026-10-01',_month_scope('2026-09')[0])
        with self.assertRaises(ValueError): _month_scope('2026-13')
    def run_export(self,fetch):
        with TemporaryDirectory() as d:
            p=Path(d)/'private.csv'; m=Path(d)/'private.json'
            result=export('2026-09',p,m,fetch=fetch,page_size=2)
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),result['sha256'])
            self.assertEqual(result['rows_exported'],3)
            self.assertFalse(result.get('public_release_approved',False))
    def test_valid(self): self.run_export(fake_fetch())
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): self.run_export(fake_fetch(duplicate=True))
    def test_wrong_month_rejected(self):
        with self.assertRaises(ValueError): self.run_export(fake_fetch(bad_date=True))
    def test_source_count_drift_rejected(self):
        with self.assertRaises(ValueError): self.run_export(fake_fetch(drift=True))

if __name__ == '__main__': unittest.main()
