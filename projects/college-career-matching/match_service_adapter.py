#!/usr/bin/env python3
"""Pure-Python service boundary for the interactive College + Career matcher."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from labor_evidence_service_adapter import build_for_candidate
from constraint_field_registry import load_registry,validate_constraint
MODES={"broad_exploration","career_first","college_program_first","compare_known","transfer","returning_student"};UNKNOWN={"keep_visible","exclude_unknown"};DIMS={"college_fit","affordability","academic_program_fit","transfer_pathway_fit","admissions_context","career_pathway_fit","current_labor_market","long_term_outlook","geographic_fit","transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"};CAREER_OPS={"target_distance","higher_preferred","lower_preferred","range","categorical_match"};MISSING={None,"","NA","N/A","NULL","NONE"}
def missing(v:Any)->bool:return v is None or (isinstance(v,str) and v.strip().upper() in {str(x).upper() for x in MISSING if x is not None})
def num(v):
 try:return float(v)
 except (TypeError,ValueError):return None
def validate_request(r):
 if r.get("schema_version")!="1.0":raise ValueError("unsupported schema_version")
 if r.get("decision_mode") not in MODES:raise ValueError("unsupported decision_mode")
 if not isinstance(r.get("constraints"),list) or not isinstance(r.get("preferences"),list):raise ValueError("constraints and preferences must be arrays")
 try:page=int(r.get("page",1));size=int(r.get("page_size",20))
 except (TypeError,ValueError):raise ValueError("page and page_size must be integers")
 if page<1 or size<1 or size>100:raise ValueError("page must be >=1 and page_size must be 1..100")
 registry=load_registry();ids=set()
 for c in r["constraints"]:
  for k in ["constraint_id","field","operator","value","unknown_policy"]:
   if k not in c:raise ValueError(f"constraint missing {k}")
  if c["constraint_id"] in ids:raise ValueError("duplicate constraint_id")
  ids.add(c["constraint_id"])
  if c["unknown_policy"] not in UNKNOWN:raise ValueError("unsupported unknown_policy")
  validate_constraint(c,registry)
 pids=set()
 for p in r["preferences"]:
  if p.get("priority_explicit") is not True or p.get("dimension") not in DIMS:raise ValueError("invalid preference")
  if p.get("preference_id") in pids:raise ValueError("duplicate preference_id")
  pids.add(p.get("preference_id"));imp=num(p.get("importance"))
  if imp is None or imp<0:raise ValueError("preference importance must be nonnegative numeric")
 for p in r.get("career_preferences",[]):
  if p.get("priority_explicit") is not True or p.get("operator") not in CAREER_OPS:raise ValueError("invalid career preference")
def boolean_value(v):
 if isinstance(v,bool):return v
 if isinstance(v,str):
  x=v.strip().lower()
  if x in {"1","true","yes","y"}:return True
  if x in {"0","false","no","n"}:return False
 return None
def compare(actual,op,expected):
 if isinstance(expected,bool):
  a=boolean_value(actual)
  if a is not None:
   if op=="eq":return a is expected
   if op=="neq":return a is not expected
 if op in {"in","not_in"}:
  vals=expected if isinstance(expected,list) else [expected];hit=actual in vals;return hit if op=="in" else not hit
 if op=="eq":return actual==expected
 if op=="neq":return actual!=expected
 a,b=num(actual),num(expected)
 if a is None or b is None:return False
 return {"gte":a>=b,"gt":a>b,"lte":a<=b,"lt":a<b}[op]
def disposition(c,constraints):
 reasons=[];unknowns=[]
 for x in constraints:
  actual=c.get(x["field"])
  if missing(actual):
   if x["unknown_policy"]=="exclude_unknown":return "excluded",[f"constraint_unknown:{x['constraint_id']}"]
   unknowns.append(f"constraint_unknown:{x['constraint_id']}");continue
  if not compare(actual,x["operator"],x["value"]):return "excluded",[f"constraint_failed:{x['constraint_id']}"]
  reasons.append(f"constraint_passed:{x['constraint_id']}")
 return ("eligible_with_unknown" if unknowns else "eligible"),reasons+unknowns
def dimension_rows(c):
 out=[]
 for d in sorted(DIMS):
  vk=f"dimension__{d}";ck=f"coverage__{d}";sk=f"state__{d}"
  if vk in c or ck in c or sk in c:
   v=num(c.get(vk));cov=num(c.get(ck));cov=0 if cov is None else max(0,min(1,cov));out.append({"dimension":d,"value":v,"coverage_rate":cov,"evidence_state":c.get(sk) or ("observed" if v is not None else "insufficient")})
 return out
def reason(code,text):return {"code":code,"text":text,"evidence_ids":[]}
def result(c,status,codes,labor=None):
 dims=dimension_rows(c);unknown=[x for x in codes if x.startswith("constraint_unknown")];coverage=[d["coverage_rate"] for d in dims];avg=sum(coverage)/len(coverage) if coverage else 0
 return {"candidate_id":str(c["candidate_id"]),"institution":{"unitid":str(c["UNITID"]),"name":str(c["institution_name"]),"city":c.get("city") or None,"state":c.get("state") or None},"program":{"program_id":str(c["program_id"]),"name":str(c["program_name"]),"cip_code":str(c["cip_code"]),"credential_level":c.get("credential_level") or None},"eligibility":{"status":status,"reason_codes":codes},"dimensions":dims,"explanation":{"why_it_matches":[reason("eligible_constraints","Meets the evaluated must-have constraints.")] if status=="eligible" else [],"tradeoffs":[],"unknowns":[reason(x,"Evidence needed to evaluate one must-have constraint is currently unavailable.") for x in unknown]},"career_pathways":{"pathway_count":int(num(c.get("career__soc_count",c.get("pathway_count"))) or 0),"soc_codes":[x.strip() for x in str(c.get("career__soc_codes","")).split("|") if x.strip()],"representative_pathways":c.get("representative_pathways",[])},"transfer":c.get("transfer"),"labor_market":labor or {"selected_work_market":{"evidence_state":"not_loaded"},"long_term_outlook":{"evidence_state":"not_loaded"}},"evidence_coverage":{"overall_status":"broad" if avg>=.8 else ("partial" if avg>=.4 else "limited"),"review_flags":c.get("review_flags",[])},"source_freshness":c.get("source_freshness",[])}
def request_id(request,data_version,model_version):
 payload=json.dumps({"request":request,"data_version":data_version,"model_version":model_version},sort_keys=True,separators=(",",":"));return "req_"+hashlib.sha256(payload.encode()).hexdigest()[:20]
def match(request,candidates,data_version,model_version,current_labor=None,projections=None,generated_at_utc=None):
 validate_request(request);eligible=[];required={"candidate_id","UNITID","institution_name","program_id","program_name","cip_code"};current_labor=current_labor or [];projections=projections or [];work=request.get("geography",{}).get("intended_work_market") or None;seen=set()
 for c in candidates:
  miss=required-set(c)
  if miss:raise ValueError(f"candidate missing fields: {sorted(miss)}")
  cid=str(c.get("candidate_id","")).strip()
  if not cid:raise ValueError("candidate_id must be nonblank")
  if cid in seen:raise ValueError(f"duplicate candidate_id: {cid}")
  seen.add(cid);status,codes=disposition(c,request["constraints"])
  if status!="excluded":eligible.append(result(c,status,codes,build_for_candidate(c,current_labor,projections,work)))
 eligible.sort(key=lambda x:(x["institution"]["name"].casefold(),x["program"]["name"].casefold(),x["candidate_id"]));page=int(request.get("page",1));size=int(request.get("page_size",20));start=(page-1)*size;total=len(eligible);pages=(total+size-1)//size if total else 0;stamp=generated_at_utc or datetime.now(timezone.utc).isoformat()
 return {"schema_version":"1.0","request_id":request_id(request,data_version,model_version),"data_version":data_version,"model_version":model_version,"generated_at_utc":stamp,"result_count":total,"pagination":{"page":page,"page_size":size,"total_pages":pages,"has_next":page<pages,"has_previous":page>1 and pages>0},"warnings":[],"results":eligible[start:start+size]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--current-labor",type=Path);ap.add_argument("--projections",type=Path);ap.add_argument("--data-version",required=True);ap.add_argument("--model-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args();req=json.loads(a.request.read_text());cands=json.loads(a.candidates.read_text());load=lambda p:json.loads(p.read_text()) if p else [];response=match(req,cands,a.data_version,a.model_version,load(a.current_labor),load(a.projections));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(response,indent=2))
if __name__=="__main__":main()
