"""Synthetic NYC calendar and DST regression tests; no actual service requests."""
import csv
import tempfile
import unittest
from pathlib import Path
from pipeline import ingest

FIELDS = ['unique_key','created_date','closed_date','agency','complaint_type','borough','status']

class NYCReportingCalendarTests(unittest.TestCase):
    def process(self, rows, as_of='2026-09-30'):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'input.csv'
            output = Path(temp) / 'output.json'
            with source.open('w', newline='', encoding='utf-8') as handle:
                writer = csv.writer(handle)
                writer.writerow(FIELDS)
                for i, (created, closed, status) in enumerate(rows, start=1):
                    writer.writerow([str(i),created,closed,'DOT','Pothole','Queens',status])
            return ingest(source, output, as_of=as_of, min_cell=1)

    def test_utc_october_first_is_september_in_nyc(self):
        p = self.process([('2026-10-01T01:30:00Z','','Open')])
        self.assertEqual(p['quality']['valid_records'],1)
        self.assertEqual(p['aggregates'][0]['month'],'2026-09')

    def test_utc_october_first_after_nyc_midnight_excluded(self):
        p = self.process([('2026-10-01T05:30:00Z','','Open')])
        self.assertEqual(p['quality']['created_after_as_of'],1)
        self.assertEqual(p['aggregates'],[])

    def test_mixed_naive_and_aware_dates_can_be_compared(self):
        p = self.process([('2026-09-30T10:00:00','2026-09-30T15:00:00Z','Closed')])
        self.assertEqual(p['aggregates'][0]['closed_with_valid_interval'],1)

    def test_dst_fall_back_valid_elapsed_interval(self):
        p = self.process([('2026-11-01T01:30:00-04:00','2026-11-01T01:15:00-05:00','Closed')],as_of='2026-11-01')
        self.assertEqual(p['aggregates'][0]['closed_with_valid_interval'],1)
        self.assertEqual(p['quality'].get('closure_before_creation',0),0)

    def test_dst_fall_back_reverse_invalid(self):
        p = self.process([('2026-11-01T01:30:00-05:00','2026-11-01T01:15:00-04:00','Closed')],as_of='2026-11-01')
        self.assertEqual(p['aggregates'][0]['closed_with_valid_interval'],0)
        self.assertEqual(p['quality']['closure_before_creation'],1)

    def test_future_closure_not_counted_as_of(self):
        p = self.process([('2026-09-30T09:00:00','2026-10-01T09:00:00','Closed')])
        self.assertEqual(p['aggregates'][0]['requests'],1)
        self.assertEqual(p['aggregates'][0]['closed_with_valid_interval'],0)
        self.assertEqual(p['quality']['closure_after_as_of'],1)

if __name__=='__main__': unittest.main()
