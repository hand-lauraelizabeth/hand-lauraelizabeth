"""Synthetic-only fail-closed duplicate ID tests; never embed real 311 identifiers."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ['unique_key','created_date','closed_date','agency','complaint_type','borough','status']
def row(key, date='2026-09-01T10:00:00'):
    return [key,date,'','DOT','Pothole','Queens','Open']

class DistinctIdentifierTests(unittest.TestCase):
    def run_rows(self, rows, expected=None, existing=False):
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp)/'source.csv', Path(tmp)/'out.json'
            with src.open('w', newline='', encoding='utf-8') as f:
                w=csv.writer(f); w.writerow(FIELDS); w.writerows(rows)
            if existing: out.write_text('PRESERVE', encoding='utf-8')
            if expected:
                with self.assertRaisesRegex(ValueError, expected) as caught:
                    ingest(src,out,as_of='2026-09-30',min_cell=1)
                self.assertNotIn('SECRET_ID',str(caught.exception))
                if existing:
                    self.assertEqual(out.read_text(),'PRESERVE')
                else:
                    self.assertFalse(out.exists())
            else:
                result=ingest(src,out,as_of='2026-09-30',min_cell=1)
                self.assertEqual(result['quality']['rows_read'],len(rows))
                self.assertEqual(json.loads(out.read_text())['quality']['valid_records'],len(rows))
            self.assertEqual(sorted(x.name for x in Path(tmp).iterdir()), ['out.json','source.csv'] if out.exists() else ['source.csv'])
    def test_duplicate_valid(self): self.run_rows([row('SECRET_ID'),row('SECRET_ID')],'Duplicate unique_key')
    def test_duplicate_ignored_date(self): self.run_rows([row('SECRET_ID','not-a-date'),row('SECRET_ID')],'Duplicate unique_key')
    def test_whitespace_alias(self): self.run_rows([row('SECRET_ID'),row(' SECRET_ID ')],'Duplicate unique_key')
    def test_existing_output_preserved(self): self.run_rows([row('SECRET_ID'),row('SECRET_ID')],'Duplicate unique_key',True)
    def test_distinct_10000(self): self.run_rows([row(str(i)) for i in range(10000)])

if __name__=='__main__': unittest.main()
