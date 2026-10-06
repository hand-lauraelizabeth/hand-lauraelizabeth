#!/usr/bin/env python3
"""Build a stable, evidence-aware candidate-detail response for the interactive product."""
from __future__ import annotations
import json
from labor_evidence_service_adapter import build_for_candidate
from career_pathway_service import career_summary

def clean(v): return str(v).strip() if v is not None else ""
def listish(value):
    if value in (None,""): return []
    if isinstance(value,list): return value
    if isinstance(value,(tuple,set)): return list(value)
    text=clean(value)
    if text.startswith("["):
      try:
       parsed=json.loads(text)
       if isinstance(parsed,list): return parsed
      except Exception: pass
    return [x.strip() for x in text.split("|") if x.strip()]
def evidence(value,state=None,source_id=None,source_vintage=None):
    if state: s=state
    elif value in (None,""): s="missing"
    else: s="observed"
    return {"value":value,"evidence_state":s,"source_id":source_id or None,"source_vintage":source_vintage or None}
def measure(candidate,prefix,name):
    key=f"{prefix}{name}"
    return evidence(candidate.get(key),candidate.get(f"{key}__state"),candidate.get(f"{key}__source_id"),candidate.get(f"{key}__source_vintage"))
def candidate_detail(candidate,current_labor=None,projections=None,work_market=None,data_version=None):
    labor=build_for_candidate(candidate,current_labor or [],projections or [],work_market)
    return {
      "schema_version":"1.0","data_version":data_version,"candidate_id":clean(candidate.get("candidate_id")),
      "institution":{"unitid":clean(candidate.get("UNITID")),"name":clean(candidate.get("institution_name")),"city":candidate.get("city") or None,"state":candidate.get("state") or None,"accreditation":{"covered":clean(candidate.get("coverage__accreditation"))=="1","statuses":listish(candidate.get("accreditation__statuses") or candidate.get("accreditation__status")),"agency_names":listish(candidate.get("accreditation__agency_names")),"record_count":candidate.get("accreditation__record_count"),"source_record_ids":listish(candidate.get("accreditation__source_record_ids"))}},
      "program":{"program_id":clean(candidate.get("program_id")),"name":clean(candidate.get("program_name")),"cip_code":clean(candidate.get("cip_code")),"cip_title":candidate.get("cip_title") or None,"credential_level":candidate.get("credential_level") or None,"online_available":evidence(candidate.get("online_available"))},
      "affordability":{"net_price":measure(candidate,"finance__","net_price"),"tuition_in_state":measure(candidate,"finance__","tuition_in_state"),"tuition_out_of_state":measure(candidate,"finance__","tuition_out_of_state"),"cost_of_attendance":measure(candidate,"finance__","cost_of_attendance"),"institution_median_debt":measure(candidate,"finance__","median_debt")},
      "aid_context":{"institutional_grant_share":measure(candidate,"finance__","institutional_grant_share"),"work_study_share":measure(candidate,"finance__","work_study_share"),"state_local_grant_share":measure(candidate,"finance__","state_local_grant_share"),"institutional_grant_evidence":clean(candidate.get("finance__institutional_grant_evidence")) or None,"work_study_evidence":clean(candidate.get("finance__work_study_evidence")) or None,"state_local_grant_evidence":clean(candidate.get("finance__state_local_grant_evidence")) or None},
      "program_outcomes":{"covered":clean(candidate.get("coverage__program_outcomes"))=="1","median_earnings":measure(candidate,"program_outcomes__","median_earnings"),"median_debt":measure(candidate,"program_outcomes__","median_debt"),"completion_rate":measure(candidate,"program_outcomes__","completion_rate")},
      "transfer":{"covered":clean(candidate.get("coverage__transfer"))=="1","evidence_record_count":candidate.get("transfer__evidence_record_count"),"evidence_levels":listish(candidate.get("transfer__evidence_levels")),"source_systems":listish(candidate.get("transfer__source_systems"))},
      "career":{"covered":clean(candidate.get("coverage__career_pathways"))=="1","soc_count":candidate.get("career__soc_count"),**career_summary(candidate)},
      "labor_market":labor,
      "freshness":{"source_freshness":listish(candidate.get("source_freshness",[])),"data_version":data_version},
      "unknowns":[k for k,v in candidate.items() if k.endswith("__state") and clean(v) in {"missing","suppressed","unresolved","not_published"}]
    }
