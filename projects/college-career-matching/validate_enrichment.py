"""Strict source evidence gate for national matcher review-only enrichment."""
import re
FIELDS={'locale','undergraduate_size','net_price','annual_cost','sat_avg','act_mid','sat_bands','act_bands'}
SCORE={'sat_avg','act_mid','sat_bands','act_bands'}
LIMITS={'undergraduate_size':(0,2000000),'net_price':(0,200000),'annual_cost':(0,200000),'sat_avg':(400,1600),'act_mid':(1,36)}
def validate(row):
    assert re.fullmatch(r'[0-9]{6}',str(row['unitid'])), 'Six-digit UNITID required'
    f=row['field'];assert f in FIELDS,'Unknown field'
    assert all(isinstance(row.get(k),str) and row[k].strip() for k in ('source_url','source_dataset','cohort','source_field')),'Attribution required'
    assert row['source_url'].startswith('https://'),'HTTPS evidence required'
    v=row.get('value');assert v is not None,'Null is not enrichment'
    if f=='locale':assert v in ('city','suburb','town','rural')
    elif f in LIMITS:
        lo,hi=LIMITS[f];assert type(v) is int and lo<=v<=hi,'Invalid value'
    else:
        lo,hi=(400,1600) if f=='sat_bands' else (1,36)
        assert isinstance(v,list) and len(v)==2 and all(type(x) is int for x in v)
        assert lo<=v[0]<=v[1]<=hi
    if f in SCORE:
        assert row.get('score_cohort')==row['cohort'],'Score year required'
        assert row.get('is_estimate') is False,'Do not label derived scores verified'
    assert row.get('current_policy_inferred') is not True,'Do not infer test policy'
    return True
