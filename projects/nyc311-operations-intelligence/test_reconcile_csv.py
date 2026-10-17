"""Synthetic-only NYC 311 CSV reconciliation tests; no real request-level records."""
from copy import deepcopy
from datetime import date
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.parse import urlencode

from validate_snapshot import ENDPOINT
from reconcile_csv import reconcile

WHERE = "created_date >= '2026-09-01T00:00:00' and created_date < '2026-10-01T00:00:00'"
PARAMS = [
    {'$select':'count(*) as total,count(distinct unique_key) as distinct_ids','$where':WHERE},
    {'$select':'borough,count(*) as n','$where':WHERE,'$group':'borough','$order':'n desc'},
    {'$select':'date_trunc_ymd(created_date) as day,count(*) as n','$where':WHERE,'$group':'date_trunc_ymd(created_date)','$order':'day asc','$limit':'40'},
    {'$select':'complaint_type,count(*) as n','$where':WHERE,'$group':'complaint_type','$order':'n desc','$limit':'12'},
]


def fixture():
    return {'dataset_id':'erm2-nwe9','month':'2026-09','rechecked_date':'2026-10-17',
            'queries':[{'url':ENDPOINT+'?'+urlencode(p),'params':p} for p in deepcopy(PARAMS)],
            'results':{'total':30,'distinct_ids':30,'borough_counts':{'BROOKLYN':30},
                       'daily_counts':[{'day':date(2026,9,d).isoformat(),'requests':1} for d in range(1,31)],
                       'top_complaint_types':[{'complaint_type':f'Test {d}','requests':2} for d in range(1,13)],
                       'other_complaint_types_requests':6}}


def rows():
    header='unique_key,created_date,closed_date,agency,complaint_type,borough,status\n'
    records=[]
    for day in range(1,31):
        category=f'Test {(day-1)//2+1}' if day<=24 else 'Other'
        records.append(f'{day},2026-09-{day:02d}T12:00:00,,TEST,{category},BROOKLYN,Open\n')
    return header+''.join(records)


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'synthetic.csv'
        self.path.write_text(rows())
        self.snapshot=fixture()

    def test_reconciles_and_hashes(self):
        expected=hashlib.sha256(self.path.read_bytes()).hexdigest()
        report=reconcile(self.path,self.snapshot,pinned_sha256=expected)
        self.assertEqual((report['rows'],report['raw_csv_sha256']), (30,expected))

    def test_wrong_checksum_rejected(self):
        with self.assertRaisesRegex(ValueError,'checksum'):
            reconcile(self.path,self.snapshot,pinned_sha256='0'*64)

    def test_duplicate_key_rejected(self):
        self.path.write_text(rows().replace('2,2026-09-02','1,2026-09-02'))
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            reconcile(self.path,self.snapshot)

    def test_borough_mismatch_rejected(self):
        self.path.write_text(rows().replace('BROOKLYN,Open','QUEENS,Open',1))
        with self.assertRaisesRegex(ValueError,'borough'):
            reconcile(self.path,self.snapshot)

    def test_day_mismatch_rejected(self):
        self.path.write_text(rows().replace('2026-09-02T12','2026-09-01T13'))
        with self.assertRaisesRegex(ValueError,'Daily'):
            reconcile(self.path,self.snapshot)

    def test_complaint_mismatch_rejected(self):
        self.path.write_text(rows().replace('Test 1,BROOKLYN','Test 2,BROOKLYN',1))
        with self.assertRaisesRegex(ValueError,'Complaint'):
            reconcile(self.path,self.snapshot)

    def test_extra_row_rejected(self):
        self.path.write_text(rows()+'31,2026-09-01T13:00:00,,TEST,Other,BROOKLYN,Open\n')
        with self.assertRaisesRegex(ValueError,'More rows'):
            reconcile(self.path,self.snapshot)

    def test_bad_month_rejected(self):
        self.path.write_text(rows().replace('2026-09-02T12','2026-10-02T12'))
        with self.assertRaisesRegex(ValueError,'outside'):
            reconcile(self.path,self.snapshot)

    def test_tampered_query_rejected(self):
        self.snapshot['queries'][0]['params']['$where']='created_date is not null'
        with self.assertRaisesRegex(ValueError,'query'):
            reconcile(self.path,self.snapshot)

    def test_unexpected_schema_rejected(self):
        self.path.write_text(rows().replace('unique_key,created_date,','unique_key,created_on,',1))
        with self.assertRaisesRegex(ValueError,'schema'):
            reconcile(self.path,self.snapshot)


if __name__ == '__main__':
    unittest.main()
