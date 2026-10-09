"""Public-data contract for the NY twenty-school *directory* release.

This gate is intentionally narrower than the production College + Career Matcher
release gate. A public directory permits stable institutional identities and source
links, NOT college-specific predictions, financial-aid offers, housing claims,
composite rankings or activated matching services.
"""
from __future__ import annotations
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

EXPECTED={'CUNY':15,'SUNY-affiliated':4,'BOCES / vocational':1}
FORBIDDEN_TERMS=('applicant_name','applicant_email','api_key','access_token','student_email',
                 'admission_likelihood','admissions_odds','predictive_acceptance_rate',
                 'affordability_rank','tuition_after_aid_estimate','accessible_room_available_now')

def validate_directory(payload:dict)->dict:
    failures=[]
    if payload.get('schema_version')!=1:failures.append('incorrect_schema_version')
    if payload.get('publication_scope')!='PUBLIC_REFERENCE_DIRECTORY_ONLY':failures.append('wrong_scope')
    if payload.get('matcher_activation_authorized') is not False:failures.append('production_not_disabled')
    rows=payload.get('institutions')
    if not isinstance(rows,list) or len(rows)!=20:
        return {'pass':False,'failures':failures+['not_20_institutions'],'count':len(rows) if isinstance(rows,list) else 0}
    ids=[]; groups=[]
    for i,r in enumerate(rows):
        unitid=r.get('unitid')
        if not isinstance(unitid,str) or not re.fullmatch(r'\d{6}',unitid):failures.append(f'{i}:bad_unitid')
        else:ids.append(unitid)
        if not isinstance(r.get('name'),str) or len(r['name'].strip())<4:failures.append(f'{i}:bad_name')
        groups.append(r.get('system'))
        if r.get('reference_only') is not True:failures.append(f'{i}:not_reference_only')
        for k in ('admission_probability','recommendation_score'):
            if r.get(k,'MISSING') is not None:failures.append(f'{i}:prohibited_{k}')
        for k in ('program_exhaustive_verified','current_student_accessible_housing_verified'):
            if r.get(k,'MISSING') is not False:failures.append(f'{i}:unsupported_{k}')
        for k in ('program_directory_url','accessibility_resource_url','admissions_directory_url'):
            url=r.get(k)
            if url is None:continue
            try:
                p=urlsplit(url)
                host=p.hostname or ''
                if p.scheme!='https' or not (host.endswith('.edu') or host.endswith('.gov') or host in ('www.cves.org','cves.org')) or p.username or p.password:
                    failures.append(f'{i}:untrusted_{k}')
            except Exception:failures.append(f'{i}:malformed_{k}')
        serialized=json.dumps(r).lower()
        if any(token in serialized for token in FORBIDDEN_TERMS):failures.append(f'{i}:prohibited_sensitive_field')
    if len(set(ids))!=20:failures.append('duplicate_unitids')
    if dict(Counter(groups))!=EXPECTED:failures.append('category_count_mismatch')
    return {'pass':not failures,'failures':failures,'count':len(rows),'by_sector':dict(Counter(groups))}

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('jsonfile');a=p.parse_args()
    result=validate_directory(json.loads(Path(a.jsonfile).read_text(encoding='utf-8')))
    print(json.dumps(result,sort_keys=True));raise SystemExit(0 if result['pass'] else 1)
if __name__=='__main__':main()