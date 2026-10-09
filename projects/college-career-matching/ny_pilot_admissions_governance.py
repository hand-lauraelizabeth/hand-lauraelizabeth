"""Admission-evidence gates for New York 20-school pilot.

This module does NOT estimate admission probabilities from college averages.
Calibration requires a separate legally permitted, labeled and held-out dataset.
"""
from __future__ import annotations
from collections import defaultdict
from math import log
from typing import Any

SCALES = {"hs_percent_100":(0.0,100.0),"college_gpa_4":(0.0,4.0),"sat_total_1600":(400.0,1600.0),"act_composite_36":(1.0,36.0)}

def validate_score(value: Any, scale: str)->float:
    if scale not in SCALES: raise ValueError("Unknown explicit grading/test scale")
    if isinstance(value,bool) or not isinstance(value,(float,int)):raise ValueError("Score must be numeric")
    lo,hi=SCALES[scale]
    if not lo <= float(value) <= hi: raise ValueError("Score outside named scale")
    return float(value)

def compare_reported_means(user_value: Any, user_scale: str, school_mean: Any, mean_scale: str, source: str)->dict:
    """Only compare same-scale inputs; comparison is not a cutoff/odds."""
    if user_value is None or school_mean is None or not source:
        return {"state":"insufficient_evidence","admission_probability":None}
    a=validate_score(user_value,user_scale)
    b=validate_score(school_mean,mean_scale)
    if user_scale != mean_scale:
        return {"state":"incomparable_grading_scales","admission_probability":None,"requires":"school-specific documented scale conversion or another same-scale input"}
    return {"state":"descriptive_mean_comparison_only","difference_in_original_scale":round(a-b,3),"scale":user_scale,
            "mean_source":source,"admission_probability":None,
            "caution":"Admitted cohort mean is neither minimum nor chance of admission; do not infer percent likelihood."}

def calibration_audit(observations:list[dict], *, min_total:int=200, min_bin:int=20, bins:int=10, validation_data_authorized:bool=False)->dict:
    """Compute diagnostics on permitted, independent offer-outcome observations.

    observations: probability model output, observed binary offer outcome, stable cohort label.
    The output reports diagnostics, not independent proof of calibration or fairness.
    """
    if not validation_data_authorized:
        return {"status":"BLOCKED_NO_AUTHORIZED_LABELLED_VALIDATION_DATA","admission_probability_publication_allowed":False}
    if len(observations)<min_total:
        return {"status":"INSUFFICIENT_VALIDATION_SAMPLE","n":len(observations),"min_total":min_total,"admission_probability_publication_allowed":False}
    n=len(observations); pts=[]; bucket=defaultdict(list)
    for rec in observations:
        p=rec.get('predicted_probability'); outcome=rec.get('admitted_offer')
        if isinstance(p,bool) or not isinstance(p,(float,int)) or p<0 or p>1: raise ValueError('Predicted probabilities must be numbers in [0,1]')
        if outcome not in (0,1,False,True):raise ValueError('Offer outcome must be binary')
        if not str(rec.get('independent_holdout_cohort','')).strip():raise ValueError('Independent holdout cohort provenance required')
        p=float(p);outcome=int(outcome);pts.append((p,outcome)); b=min(int(p*bins),bins-1);bucket[b].append((p,outcome))
    brier=sum((p-y)**2 for p,y in pts)/n
    eps=1e-12
    logloss=-sum(y*log(max(eps,min(1-eps,p)))+(1-y)*log(max(eps,min(1-eps,1-p))) for p,y in pts)/n
    ece=0.0;line=[];small=[]
    for b in range(bins):
        v=bucket[b]
        if not v:continue
        pm=sum(p for p,_ in v)/len(v);obs=sum(y for _,y in v)/len(v)
        ece+=len(v)/n*abs(pm-obs)
        line.append({'bucket':b,'n':len(v),'mean_predicted':round(pm,5),'mean_offered':round(obs,5)})
        if len(v)<min_bin:small.append(b)
    return {'status':'DIAGNOSTIC_ONLY_NOT_CALIBRATION_APPROVAL','n':n,'brier_score':round(brier,6),
            'log_loss':round(logloss,6),'expected_calibration_error':round(ece,6),
            'small_bins':small,'bins':line,'admission_probability_publication_allowed':False,
            'remaining_review':['train/test leakage','selective application and admitted-offer labels','subgroup coverage','confidence intervals','distribution shift','human approval']}