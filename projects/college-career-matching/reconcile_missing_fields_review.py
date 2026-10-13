"""Read-only, provenance-preserving gap reconciliation for normalized matcher records.

Requires baseline institutions as a mapping of six-digit UNITID to named fields.
The compact production v3 row arrays require a separate schema adapter.
"""
import json
from collections import Counter
from pathlib import Path
from validate_enrichment import validate

FIELDS=('locale','undergraduate_size','net_price','annual_cost','sat_avg','act_mid','sat_bands','act_bands')
GAPS={'locale':531,'undergraduate_size':781,'net_price':1222,'annual_cost':1221,'sat_avg':5079,'act_mid':5228,'sat_bands':5192,'act_bands':5278}

def reconcile(schools, candidates, *, strict=True):
    if not isinstance(schools,dict):
        raise ValueError('Normalize production row arrays before reconciliation')
    if strict and len(schools)!=6243:
        raise ValueError('Expected exactly 6243 institutions')
    accepted={};counts=Counter();rejected=Counter();seen=set()
    for row in candidates:
        validate(row)
        uid=str(row['unitid']);field=row['field'];key=(uid,field)
        if key in seen:raise ValueError('Duplicate UNITID and field')
        seen.add(key)
        if uid not in schools:
            rejected['not_in_universe']+=1;continue
        if not isinstance(schools[uid],dict):
            raise ValueError('Expected named baseline fields')
        if schools[uid].get(field) is not None:
            rejected['already_present']+=1;continue
        accepted.setdefault(uid,{})[field]={k:row[k] for k in ('value','source_url','source_dataset','cohort','source_field')}
        counts[field]+=1
    if strict:
        for f in FIELDS:
            n=sum(v.get(f) is None for v in schools.values())
            if n!=GAPS[f]:raise ValueError(f'Baseline {f} mismatch: {n} vs {GAPS[f]}')
    return {'accepted':accepted,'accepted_counts':{f:counts[f] for f in FIELDS},
            'remaining_gaps':{f:GAPS[f]-counts[f] for f in FIELDS},
            'rejected_counts':dict(rejected),'review_only':True}

if __name__=='__main__':
    import sys
    base=json.loads(Path(sys.argv[1]).read_text())
    candidates=[json.loads(s) for s in Path(sys.argv[2]).read_text().splitlines() if s.strip()]
    print(json.dumps(reconcile(base,candidates),indent=2))
