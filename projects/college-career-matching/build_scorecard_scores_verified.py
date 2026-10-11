"""Generate per-institution admissions score overlay from pinned official College Scorecard ZIP.

SAT total 25th/50th/75th are the SUM of the reported Reading/Writing and
Math section percentiles, not published percentile distributions of SAT totals.
Do not interpret scores as admissions chances.
"""
import argparse
import csv
from collections import Counter
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile

ARCHIVE_SHA = 'f56a181b000ca4914e924c16b6b81dcc656e25aeb2ac68ab7d271ac0f29ffd58'
EXPECTED_COUNT = 6243
SRC_ID = 'scorecard_2026'
FIELDS = ('SAT_AVG','ACTCMMID','SATVR25','SATVR50','SATVR75','SATMT25','SATMT50','SATMT75','ACTCM25','ACTCM50','ACTCM75')

def integer(value):
    if value in ('NA','PS','NULL','',None,'PrivacySuppressed','-3'):return None
    try:
        v=float(value)
        return int(v) if v.is_integer() else None
    except (TypeError,ValueError):
        return None

def ordered(v,minimum,maximum):
    return all(x is not None and minimum<=x<=maximum for x in v) and v[0]<=v[1]<=v[2]

def build(archive):
    sha=hashlib.file_digest(open(archive,'rb'),'sha256').hexdigest()
    if sha!=ARCHIVE_SHA:raise ValueError('Archive SHA mismatch: '+sha)
    seen=set(); records={}; counts=Counter()
    with zipfile.ZipFile(archive) as z:
        files=[n for n in z.namelist() if n.endswith('.csv') and not n.startswith('__MACOSX/')]
        if len(files)!=1:raise ValueError('Expected one institutional CSV')
        with z.open(files[0]) as fh:
            reader=csv.DictReader(io.TextIOWrapper(fh,encoding='utf-8-sig',newline=''))
            if not set(FIELDS+('CURROPER','UNITID')).issubset(reader.fieldnames):raise ValueError('Missing expected columns')
            for row in reader:
                if row['CURROPER']!='1':continue
                uid=row['UNITID'].strip()
                if not (uid.isdigit() and len(uid)>=6) or uid in seen: raise ValueError('Invalid/duplicate UNITID '+uid)
                seen.add(uid)
                sat_avg=integer(row['SAT_AVG']); act_mid=integer(row['ACTCMMID'])
                sv=[integer(row['SATVR'+p]) for p in ('25','50','75')]
                sm=[integer(row['SATMT'+p]) for p in ('25','50','75')]
                sat=[a+b for a,b in zip(sv,sm)] if ordered(sv,200,800) and ordered(sm,200,800) else [None]*3
                act=[integer(row['ACTCM'+p]) for p in ('25','50','75')]
                if not ordered(act,1,36):act=[None]*3
                if sat_avg is not None and not 400<=sat_avg<=1600: raise ValueError('Bad SAT average '+uid)
                if act_mid is not None and not 1<=act_mid<=36:raise ValueError('Bad ACT midpoint '+uid)
                for key,val in [('sat_avg',sat_avg),('act_mid',act_mid),('sat_band',sat[0]),('act_band',act[0])]:
                    if val is not None:counts[key]+=1
                if any(x is not None for x in (sat_avg,act_mid,*sat,*act)):
                    # First 8 fields backwards-compatible with score overlay v1;
                    # fields 9/10 link SAT/ACT respectively to a source registry.
                    records[uid]=[sat_avg,act_mid,*sat,*act,SRC_ID if (sat_avg is not None or sat[0] is not None) else None,SRC_ID if (act_mid is not None or act[0] is not None) else None]
    if len(seen)!=EXPECTED_COUNT:raise ValueError('Unexpected operating-institution universe: '+str(len(seen)))
    if counts['sat_avg']!=1037 or counts['act_mid']!=970 or counts['sat_band']!=949 or counts['act_band']!=920:
        raise ValueError('Unexpected column coverage: '+str(counts))
    doc={'schema_version':2,'source':'College Scorecard','source_release':'2026-06-10',
         'source_archive_sha256':ARCHIVE_SHA,'school_count':EXPECTED_COUNT,
         'school_scores':{'sat_avg':counts['sat_avg'],'act_mid':counts['act_mid']},
         'verified_band_counts':{'sat_complete_bands':counts['sat_band'],'act_complete_bands':counts['act_band']},
         'percentile_source_status':'verified_2026_scorecard',
         'percentile_interpretation':{'sat':'Computed sum of section-level percentile scores; not a directly reported total-score percentile.',
                                      'act':'Reported ACT composite percentile.',
                                      'scope':'Test scores of enrolled first-time students who submitted scores; not admissions probability.'},
         'source_registry':{SRC_ID:{'provider':'U.S. Department of Education','dataset':'College Scorecard / IPEDS admissions',
                                    'url':'https://collegescorecard.ed.gov/data/','release':'2026-06-10','cohort':'Fall 2024',
                                    'fields':'SAT_AVG, SATVR25/50/75, SATMT25/50/75, ACTCMMID, ACTCM25/50/75',
                                    'sat_composite_estimated':True}},
         'institutions':dict(sorted(records.items()))}
    return doc,counts

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--archive',required=True,type=Path);ap.add_argument('--output',required=True,type=Path); a=ap.parse_args()
    doc,c=build(a.archive)
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode()
    a.output.write_bytes(raw)
    zipped=gzip.compress(raw,mtime=0,compresslevel=9)
    print(json.dumps({'records_with_any_scores':len(doc['institutions']),'counts':dict(c),'size_json_bytes':len(raw),'gzip_bytes':len(zipped),
                      'total_with_national_gzip_bytes':len(zipped)+259736,'limit_bytes':750*1024,'sha256':hashlib.sha256(raw).hexdigest()},indent=2))