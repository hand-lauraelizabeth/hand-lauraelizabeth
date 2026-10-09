"""Fail-closed independent-data reconciler for the New York 20-school pilot.

Reads private existing pilot JSON plus an NCES HD2025 CSV or original HD2025 ZIP.
The 2026 Scorecard archive is NOT independent evidence for NCES locale.
A signed-off cohort map is optional; absence never creates a fake cohort year.
Run: python ny_pilot_independent_source_audit.py --pilot ...json \
  [--hd2025 HD2025.zip] [--hd2025-source-url OFFICIAL_URL] \
  [--cohort-map reviewed_cohort_map.csv] --output-dir folder
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

OFFICIAL_DIRECTORY_URL = 'https://nces.ed.gov/ipeds/datacenter/data/HD2025.zip'
OFFICIAL_DICTIONARY_URL = 'https://collegescorecard.ed.gov/files/CollegeScorecardDataDictionary.xlsx'
YEAR_RE = re.compile(r'^20\d{2}-\d{2}$')
FIVE = ('NPT41_PUB','NPT42_PUB','NPT43_PUB','NPT44_PUB','NPT45_PUB')

def sha256(path):
    h = hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def read_hd2025(path):
    """Never treat a Scorecard file as an independent NCES directory."""
    p=Path(path)
    if 'HD2025' not in p.name.upper(): raise ValueError('Directory basename must identify HD2025')
    if p.suffix.lower()=='.zip':
        with zipfile.ZipFile(p) as z:
            names=[x for x in z.namelist() if re.search(r'(^|/)HD2025\.CSV$',x,re.I) and not x.startswith('__MACOSX/')]
            if len(names)!=1: raise ValueError('HD2025.zip must contain exactly one HD2025.csv')
            binary=z.read(names[0])
    elif p.suffix.lower()=='.csv':binary=p.read_bytes()
    else:raise ValueError('HD2025 source must be ZIP/CSV')
    decoded=binary.decode('utf-8-sig',errors='replace')
    reader=csv.DictReader(io.StringIO(decoded))
    need={'UNITID','INSTNM','LOCALE','CITY','STABBR'}
    if not reader.fieldnames or not need.issubset({x.upper() for x in reader.fieldnames}):
        raise ValueError('Missing required HD2025 directory columns')
    rows={}
    for row in reader:
        r={k.upper():v for k,v in row.items()}
        uid=(r.get('UNITID') or '').strip()
        if not uid: continue
        if uid in rows:raise ValueError('Duplicate UNITID in HD2025 data: '+uid)
        rows[uid]=r
    return rows

def attestation_valid(attestation_path, source_url, digest):
    """Document human chain-of-custody; URL text alone is never verification."""
    if not attestation_path or not digest: return False
    with open(attestation_path,encoding='utf-8') as f: att=json.load(f)
    return bool(att.get('review_authorized') is True
        and att.get('source_url') == OFFICIAL_DIRECTORY_URL
        and source_url == OFFICIAL_DIRECTORY_URL
        and att.get('file_sha256') == digest
        and att.get('retrieval_method') == 'direct_official_download'
        and str(att.get('reviewer','')).strip()
        and re.fullmatch(r'20\d{2}-\d{2}-\d{2}',str(att.get('review_date',''))))

def reconcile_locale(pilot,hdrows=None,*,source_url=None,sha=None,source_attested=False):
    src_confirmed=source_url==OFFICIAL_DIRECTORY_URL and bool(sha) and source_attested
    results=[]
    for row in pilot['institutions']:
        uid=str(row['UNITID']).strip()
        candidate=str(row.get('Scorecard_locale_candidate') or '').strip()
        match=hdrows.get(uid) if hdrows else None
        out={'UNITID':uid,'institution':row.get('School'),
             'scorecard_locale_candidate':candidate or None,
             'nces_hd2025_locale':(match or {}).get('LOCALE') or None,
             'nces_hd2025_instnm':(match or {}).get('INSTNM') or None,
             'nces_hd2025_city':(match or {}).get('CITY') or None,
             'nces_hd2025_state':(match or {}).get('STABBR') or None,
             'nces_hd2025_zip':(match or {}).get('ZIP') or None,
             'hd2025_sha256':sha,'hd2025_source_url':source_url,
             'current_site_address_confirmed_by_hd2025':False,
             'publication_status':'DO_NOT_PUBLISH'}
        if hdrows is None: state='AWAITING_INDEPENDENT_HD2025_FILE'
        elif match is None: state='UNITID_NOT_IN_HD2025_REVIEW'
        elif not candidate or not out['nces_hd2025_locale']: state='INCOMPLETE_LOCALE_EVIDENCE'
        elif match['STABBR'].strip().upper()!='NY':state='DIRECTORY_STATE_CONFLICT'
        elif candidate!=match['LOCALE'].strip():state='SCORECARD_NCES_LOCALE_CONFLICT'
        elif not src_confirmed:state='VALUE_MATCH_SOURCE_PROVENANCE_NOT_ESTABLISHED'
        else:state='HD2025_LOCALE_VALUE_CROSSCHECKED__ADDRESS_NOT_CERTIFIED'
        out['locale_review_state']=state
        out['locale_field_verified']=state=='HD2025_LOCALE_VALUE_CROSSCHECKED__ADDRESS_NOT_CERTIFIED'
        results.append(out)
    return results

def read_reviewed_cohort_map(path,*,expected_document_sha256=None):
    """Import only manually source-reviewed rows with explicit worksheet coordinates.

    Does not parse a public Scorecard dictionary or infer cohort years.
    """
    if not path: return {}
    with open(path,encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if not rows:raise ValueError('Cohort map contains no reviewed fields')
    out={}
    for r in rows:
        field=r.get('scorecard_field','').strip()
        if field not in FIVE:raise ValueError('Unrecognized pilot field: '+field)
        if field in out:raise ValueError('Duplicate cohort field: '+field)
        source=r.get('dictionary_source_url','').strip()
        year=r.get('official_cohort_year','').strip()
        sheet=r.get('dictionary_sheet','').strip()
        cell=r.get('dictionary_cell','').strip()
        doc_hash=r.get('dictionary_sha256','').strip().lower()
        release=r.get('release_date','').strip()
        authorized=(r.get('human_source_review','').strip().upper()=='APPROVED')
        valid=all([source==OFFICIAL_DICTIONARY_URL,year and YEAR_RE.fullmatch(year),sheet,cell,re.fullmatch(r'[A-Z]{1,3}[1-9]\d*',cell),re.fullmatch('[0-9a-f]{64}',doc_hash),release=='2026-06-10',authorized])
        if expected_document_sha256 and doc_hash!=expected_document_sha256.lower():valid=False
        out[field]={'official_cohort_year':year or None,'dictionary_sheet':sheet or None,
                    'dictionary_cell':cell or None,'dictionary_sha256':doc_hash or None,
                    'cohort_review_state':'REVIEWED_DICTIONARY_FIELD' if valid else 'INVALID_OR_UNATTESTED_COHORT_MAPPING'}
    return out

def reconcile_cohort(pilot,mapping):
    out=[]
    for r in pilot['cohort_field_audit']:
        field=r.get('candidate_scorecard_field_public','')
        m=mapping.get(field)
        state=(m or {}).get('cohort_review_state','AWAITING_2026_DICTIONARY_COHORT_MAP')
        ok=state=='REVIEWED_DICTIONARY_FIELD' and r.get('source_field_value_match')=='MATCH'
        out.append({'UNITID':str(r['UNITID']),'school':r.get('INSTNM'), 'field':field,
                    'observed_value':r.get('observed_value'),'scorecard_archive_match':r.get('source_field_value_match'),
                    'cohort_year':m['official_cohort_year'] if ok else None,
                    'dictionary_sheet':m['dictionary_sheet'] if ok else None,
                    'dictionary_cell':m['dictionary_cell'] if ok else None,
                    'cohort_review_state':state if ok or not m else 'FIELD_OR_COHORT_REVIEW_BLOCKED',
                    'cohort_year_independently_verified':bool(ok), 'publication_status':'DO_NOT_PUBLISH'})
    return out

def build_report(pilot,hd=None,source_url=None,cohort_map=None,expected_document_sha256=None,source_attestation=None):
    if len(pilot.get('institutions',[]))!=20 or len({str(x['UNITID']) for x in pilot['institutions']})!=20:
        raise ValueError('Pilot identity / size does not equal 20 unique UNITIDs')
    if len(pilot.get('cohort_field_audit',[]))!=100: raise ValueError('Expected 100 field audit rows')
    hdrows=read_hd2025(hd) if hd else None
    directory_hash=sha256(hd) if hd else None
    locale=reconcile_locale(pilot,hdrows,source_url=source_url,sha=directory_hash,source_attested=attestation_valid(source_attestation,source_url,directory_hash))
    if cohort_map and not expected_document_sha256: raise ValueError('Dictionary XLSX bytes and SHA-256 required to accept manually reviewed cohort map')
    map_rows=read_reviewed_cohort_map(cohort_map,expected_document_sha256=expected_document_sha256)
    cohort=reconcile_cohort(pilot,map_rows)
    counts={'pilot_institutions':len(locale),'independent_nces_locale_matches':sum(x['locale_field_verified'] for x in locale),
            'scorecard_band_values':len(cohort),'verified_exact_band_cohort_years':sum(x['cohort_year_independently_verified'] for x in cohort),
            'locale_conflicts':sum('CONFLICT' in x['locale_review_state'] for x in locale),
            'unresolved_locale':sum(not x['locale_field_verified'] for x in locale),
            'unresolved_cohort_years':sum(not x['cohort_year_independently_verified'] for x in cohort)}
    return {'metadata':{'report_type':'NY_PILOT_INDEPENDENT_SOURCE_AUDIT','private_only':True,
                        'publication_status':'DO_NOT_PUBLISH','source_scorecard_alone_cannot_verify_locale':True,
                        'required_hd2025_source_url':OFFICIAL_DIRECTORY_URL,
                        'required_scorecard_dictionary_url':OFFICIAL_DICTIONARY_URL},
            'counts':counts,'locale':locale,'cohorts':cohort}

def write_report(report,output_dir):
    dest=Path(output_dir);dest.mkdir(parents=True,exist_ok=True)
    (dest/'ny_pilot_independent_source_audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    for name,rows in [('ny_pilot_hd2025_reconciliation.csv',report['locale']),('ny_pilot_cohort_map_reconciliation.csv',report['cohorts'])]:
        with (dest/name).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--pilot',required=True);p.add_argument('--hd2025');p.add_argument('--hd2025-source-url');p.add_argument('--hd2025-attestation');p.add_argument('--cohort-map');p.add_argument('--dictionary-xlsx');p.add_argument('--output-dir',required=True)
    a=p.parse_args();dictionary_hash=sha256(a.dictionary_xlsx) if a.dictionary_xlsx else None
    report=build_report(json.loads(Path(a.pilot).read_text()),a.hd2025,a.hd2025_source_url,a.cohort_map,dictionary_hash,a.hd2025_attestation)
    write_report(report,a.output_dir);print(json.dumps(report['counts'],indent=2))
if __name__=='__main__':main()