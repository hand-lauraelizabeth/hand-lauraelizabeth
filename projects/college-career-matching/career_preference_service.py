#!/usr/bin/env python3
"""Pure-Python descriptive alignment for governed career-preference attributes."""
from __future__ import annotations
from statistics import median
from career_pathway_service import career_summary
from onet_career_attribute_registry import by_attribute

def clean(v):return str(v).strip() if v is not None else ""
def num(v):
 try:return float(v)
 except (TypeError,ValueError):return None
def align(value,p):
 x=num(value);lo=num(p.get("scale_min"));hi=num(p.get("scale_max"));op=p.get("operator")
 if x is None or lo is None or hi is None or hi<=lo:return None
 span=hi-lo
 if op=="higher_preferred":return max(0.0,min(1.0,(x-lo)/span))
 if op=="lower_preferred":return max(0.0,min(1.0,(hi-x)/span))
 if op=="target_distance":
  t=num(p.get("target_value"));return None if t is None else max(0.0,min(1.0,1-abs(x-t)/span))
 if op=="range":
  a=num(p.get("target_min"));b=num(p.get("target_max"))
  if a is None or b is None or b<a:return None
  if a<=x<=b:return 1.0
  return max(0.0,min(1.0,1-(a-x if x<a else x-b)/span))
 return None
def validate_preferences(preferences,attributes):
 registry=by_attribute();available={clean(x.get("attribute_id")) for x in attributes or []}
 for p in preferences or []:
  aid=clean(p.get("attribute_id"));spec=registry.get(aid)
  if not spec:raise ValueError(f"career preference attribute is not in the approved O*NET registry: {aid}")
  if aid not in available:raise ValueError(f"career preference attribute is not loaded in active career evidence: {aid}")
  if p.get("operator")!=spec["operator"]:raise ValueError(f"career preference operator does not match approved registry: {aid}")
  if num(p.get("scale_min"))!=float(spec["scale_min"]) or num(p.get("scale_max"))!=float(spec["scale_max"]):raise ValueError(f"career preference scale does not match approved registry: {aid}")
 return True
def build(candidate,preferences,attributes):
 prefs=[p for p in (preferences or []) if p.get("priority_explicit") is True and (num(p.get("importance")) or 0)>0]
 socs=career_summary(candidate)["soc_codes"]
 if not prefs:return {"status":"no_explicit_preferences","explicit_preference_count":0,"pathway_count":len(socs),"observed_pathway_count":0,"pathway_coverage_rate":None,"score_summary":{"median":None,"min":None,"max":None},"pathways":[],"semantic_note":"No work-characteristic preference was explicitly selected."}
 validate_preferences(prefs,attributes)
 lookup={(clean(x.get("occ_code")),clean(x.get("attribute_id"))):x for x in attributes or []};pathways=[]
 for soc in socs:
  details=[];numerator=0.0;denominator=0.0;observed=0
  for p in prefs:
   row=lookup.get((soc,clean(p.get("attribute_id"))));state=clean((row or {}).get("evidence_state")) or "missing";value=(row or {}).get("attribute_value");a=align(value,p) if state=="observed" else None;importance=num(p.get("importance")) or 0
   if a is not None:observed+=1;numerator+=a*importance;denominator+=importance
   details.append({"preference_id":p.get("preference_id"),"attribute_id":p.get("attribute_id"),"attribute_value":num(value) if a is not None else None,"alignment":a,"importance":importance,"evidence_state":state,"element_id":(row or {}).get("element_id"),"element_name":(row or {}).get("element_name"),"scale_id":(row or {}).get("scale_id"),"source_release":(row or {}).get("source_release"),"source_vintage":(row or {}).get("source_vintage")})
  score=numerator/denominator if denominator>0 else None
  pathways.append({"soc_code":soc,"alignment_score":score,"observed_preference_count":observed,"explicit_preference_count":len(prefs),"coverage_rate":observed/len(prefs) if prefs else None,"preferences":details})
 scores=[x["alignment_score"] for x in pathways if x["alignment_score"] is not None]
 return {"status":"observed" if scores else "insufficient_attribute_evidence","explicit_preference_count":len(prefs),"pathway_count":len(socs),"observed_pathway_count":len(scores),"pathway_coverage_rate":len(scores)/len(socs) if socs else None,"score_summary":{"median":median(scores) if scores else None,"min":min(scores) if scores else None,"max":max(scores) if scores else None},"pathways":pathways,"semantic_note":"Alignment compares explicit work-characteristic preferences with reviewed O*NET Work Activity Importance ratings. Missing evidence reduces coverage rather than becoming mismatch; alignment does not change service ordering in this implementation."}
