#!/usr/bin/env python3
"""Build a stable, evidence-aware candidate-detail response for the interactive product."""
from __future__ import annotations
from labor_evidence_service_adapter import build_for_candidate

def clean(v): return str(v).strip() if v is not None else ""
def evidence(value,state=None):
    if state: s=state
    elif value in (None,""): s="missing"
    else: s="observed"
    return {"value":value,"evidence_state":s}
def candidate_detail(candidate,current_labor=None,projections=None,work_market=None,data_version=None):
    labor=build_for_candidate(candidate,current_labor or [],projections or [],work_market)
    return {
      "schema_version":"1.0","data_version":data_version,"candidate_id":clean(candidate.get("candidate_id")),
      "institution":{"unitid":clean(candidate.get("UNITID")),"name":clean(candidate.get("institution_name")),"city":candidate.get("city") or None,"state":candidate.get("state") or None,"accreditation":{"covered":clean(candidate.get("coverage__accreditation"))=="1","status":candidate.get("accreditation__status") or None}},
      "program":{"program_id":clean(candidate.get("program_id")),"name":clean(candidate.get("program_name")),"cip_code":clean(candidate.get("cip_code")),"cip_title":candidate.get("cip_title") or None,"credential_level":candidate.get("credential_level") or None,"online_available":evidence(candidate.get("online_available"))},
      "affordability":{"net_price":evidence(candidate.get("finance__net_price"),candidate.get("finance__net_price__state")),"tuition_in_state":evidence(candidate.get("finance__tuition_in_state"),candidate.get("finance__tuition_in_state__state")),"tuition_out_of_state":evidence(candidate.get("finance__tuition_out_of_state"),candidate.get("finance__tuition_out_of_state__state")),"cost_of_attendance":evidence(candidate.get("finance__cost_of_attendance"),candidate.get("finance__cost_of_attendance__state")),"institution_median_debt":evidence(candidate.get("finance__median_debt"),candidate.get("finance__median_debt__state"))},
      "program_outcomes":{"covered":clean(candidate.get("coverage__program_outcomes"))=="1","median_earnings":evidence(candidate.get("program_outcomes__median_earnings"),candidate.get("program_outcomes__median_earnings__state")),"median_debt":evidence(candidate.get("program_outcomes__median_debt"),candidate.get("program_outcomes__median_debt__state")),"completion_rate":evidence(candidate.get("program_outcomes__completion_rate"),candidate.get("program_outcomes__completion_rate__state"))},
      "transfer":{"covered":clean(candidate.get("coverage__transfer"))=="1","evidence_record_count":candidate.get("transfer__evidence_record_count"),"evidence_levels":candidate.get("transfer__evidence_levels"),"source_systems":candidate.get("transfer__source_systems")},
      "career":{"covered":clean(candidate.get("coverage__career_pathways"))=="1","soc_count":candidate.get("career__soc_count"),"soc_codes":[x.strip() for x in clean(candidate.get("career__soc_codes")).split("|") if x.strip()]},
      "labor_market":labor,
      "freshness":{"source_freshness":candidate.get("source_freshness",[]),"data_version":data_version},
      "unknowns":[k for k,v in candidate.items() if k.endswith("__state") and clean(v) in {"missing","suppressed","unresolved","not_published"}]
    }
