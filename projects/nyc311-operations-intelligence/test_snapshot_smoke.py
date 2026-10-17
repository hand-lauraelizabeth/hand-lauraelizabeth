"""Synthetic, offline smoke test for monthly evidence contract."""
from datetime import date
from urllib.parse import urlencode
from validate_snapshot import ENDPOINT, validate

where = "created_date >= '2026-09-01T00:00:00' and created_date < '2026-10-01T00:00:00'"
queries = [
    {'$select':'count(*) as total,count(distinct unique_key) as distinct_ids','$where':where},
    {'$select':'borough,count(*) as n','$where':where,'$group':'borough','$order':'n desc'},
    {'$select':'date_trunc_ymd(created_date) as day,count(*) as n','$where':where,'$group':'date_trunc_ymd(created_date)','$order':'day asc','$limit':'40'},
    {'$select':'complaint_type,count(*) as n','$where':where,'$group':'complaint_type','$order':'n desc','$limit':'12'},
]
sample = {'dataset_id':'erm2-nwe9','month':'2026-09','rechecked_date':'2026-10-17',
          'queries':[{'url':ENDPOINT+'?'+urlencode(p),'params':p} for p in queries],
          'results':{'total':30,'distinct_ids':30,'borough_counts':{'BROOKLYN':30},
                     'daily_counts':[{'day':date(2026,9,n).isoformat(),'requests':1} for n in range(1,31)],
                     'top_complaint_types':[{'complaint_type':f'Synthetic {n}','requests':2} for n in range(12)],
                     'other_complaint_types_requests':6}}
assert validate(sample)['requests'] == 30
sample['results']['distinct_ids'] = 29
try:
    validate(sample)
except ValueError:
    pass
else:
    raise AssertionError('Corrupt source evidence accepted')
print('PASS: synthetic source-contract smoke test')
