#!/usr/bin/env python3
"""Pure-Python service boundary for the interactive College + Career matcher.

This module deliberately performs no shell execution and no live-source retrieval.
It validates the product-facing request, applies explicit constraints to a validated
candidate snapshot, and assembles a stable response for a future UI. Rich scoring,
career, transfer, and explanation components can be injected upstream as governed
candidate fields without changing the browser contract.
"""
from __future__ import annotations
import argparse, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODES={"broad_exploration","career_first","college_program_first","compare_known","transfer","returning_student"}
OPS={"eq","neq","in","not_in","gte","gt","lte","lt","not_applicable"}
UNKNOWN={"keep_visible","exclude_unknown"}
DIMS={"college_fit","affordability","academic_program_fit","transfer_pathway_fit","admissions_context","career_pathway_fit","current_labor_market","long_term_outlook","geographic_fit"}
CAREER_OPS={"target_distance","higher_preferred","lower_preferred","range","categorical_match"}
MISSING={None,"","NA","N/A","NULL","NONE"}

def missing(v:Any)->bool:return v is None or (isinstance(v,str) and v.strip().upper() in {str(x).upper() for x in MISSING if x is not None})
def num(v):
 try:return float(v)
 except (TypeError,ValueError):return None

def validate_request(r:dict)->None:
 if r.get("schema_version")!="1.0":raise ValueError("unsupported schema_version")
 if r.get("decision_mode") not in MODES:raise ValueError("unsupported decision_mode")
 if not isinstance(r.get("constraints"),list) or not isinstance(r.get("preferences"),list):raise ValueError("constraints and preferences must be arrays")
 ids=set()
 for c in r["constraints"]:
  for k in ["constraint_id","field","operator","value","unknown_policy"]:
   if k not in c:raise ValueError(f"constraint missing {k}")
  if c["constraint_id"] in ids:raise ValueError("duplicate constraint_id")
  ids.add(c["constraint_id"])
  if c["operator"] not in OPS:raise ValueError(f"unsupported constraint operator {c['operator']}")
  if c["unknown_policy"] not in UNKNOWN:raise ValueError("unsupported unknown_policy")
 pids=set()
 for p in r["preferences"]:
  if p.get("priority_explicit") is not True:raise ValueError("only explicit preferences may be submitted")
  if p.get("dimension") not in DIMS:raise ValueError(f"unsupported dimension {p.get('dimension')}")
  if p.get("preference_id") in pids:raise ValueError("duplicate preference_id")
  pids.add(p.get("preference_id")); imp=num(p.get("importance"))
  if imp is None or imp<0:raise ValueError("preference importance must be nonnegative numeric")
 for p in r.get("career_preferences",[]):
  if p.get("priority_explicit") is not True or p.get("operator") not in CAREER_OPS:raise ValueError("invalid career preference")

def compare(actual,op,expected):
 if op=="not_applicable":return True
 if op in {"in","not_in"}:
  vals=expected if isinstance(expected,list) else [expected]; hit=actual in vals;return hit if op=="in" else not hit
 if op=="eq":return actual==expected
 if op=="neq":return actual!=expected
 a,b=num(actual),num(expected)
 if a is None or b is None:return False
 return {"gte":a>=b,"gt":a>b,"lte":a<=b,"lt":a<b}[op]

def disposition(candidate:dict,constraints:list[dict]):
 reasons=[];unknowns=[]
 for c in constraints:
  actual=candidate.get(c["field"])
  if missing(actual):
   if c["unknown_policy"]=="exclude_unknown":return "excluded",[f"constraint_unknown:{c['constraint_id']}"]
   unknowns.append(f"constraint_unknown:{c['constraint_id']}");continue
  if not compare(actual,c["operator"],c["value"]):return "excluded",[f"constraint_failed:{c['constraint_id']}"]
  reasons.append(f"constraint_passed:{c['constraint_id']}")
 return ("eligible_with_unknown" if unknowns else "eligible"),reasons+unknowns

def dimension_rows(c:dict):
 out=[]
 for dim in sorted(DIMS):
  vk=f"dimension__{dim}";ck=f"coverage__{dim}";sk=f"state__{dim}"
  if vk in c or ck in c or sk in c:
   v=num(c.get(vk));cov=num(c.get(ck));cov=0.0 if cov is None else max(0.0,min(1.0,cov))
   out.append({"dimension":dim,"value":v,"coverage_rate":cov,"evidence_state":c.get(sk) or ("observed" if v is not None else "insufficient")})
 return out

def reason(code,text,evidence=None):return {"code":code,"text":text,"evidence_ids":evidence or []}
def result(c:dict,status:str,codes:list[str]):
 dims=dimension_rows(c); unknown=[x for x in codes if x.startswith("constraint_unknown")]
 why=[reason("eligible_constraints","Meets the evaluated must-have constraints.")] if status=="eligible" else []
 unknown_reasons=[reason(x,"Evidence needed to evaluate one must-have constraint is currently unavailable.") for x in unknown]
 coverage=[d["coverage_rate"] for d in dims];avg=sum(coverage)/len(coverage) if coverage else 0
 overall="broad" if avg>=.8 else ("partial" if avg>=.4 else "limited")
 return {"candidate_id":str(c["candidate_id"]),"institution":{"unitid":str(c["UNITID"]),"name":str(c["institution_name"]),"city":c.get("city") or None,"state":c.get("state") or None},"program":{"program_id":str(c["program_id"]),"name":str(c["program_name"]),"cip_code":str(c["cip_code"]),"credential_level":c.get("credential_level") or None},"eligibility":{"status":status,"reason_codes":codes},"dimensions":dims,"explanation":{"why_it_matches":why,"tradeoffs":[],"unknowns":unknown_reasons},"career_pathways":{"pathway_count":int(num(c.get("pathway_count")) or 0),"representative_pathways":c.get("representative_pathways",[])},"transfer":c.get("transfer"),"labor_market":c.get("labor_market",{}),"evidence_coverage":{"overall_status":overall,"review_flags":c.get("review_flags",[])},"source_freshness":c.get("source_freshness",[])}

def match(request:dict,candidates:list[dict],data_version:str,model_version:str)->dict:
 validate_request(request);eligible=[]
 required={"candidate_id","UNITID","institution_name","program_id","program_name","cip_code"}
 for c in candidates:
  miss=required-set(c)
  if miss:raise ValueError(f"candidate missing fields: {sorted(miss)}")
  status,codes=disposition(c,request["constraints"])
  if status!="excluded":eligible.append(result(c,status,codes))
 eligible.sort(key=lambda x:(x["institution"]["name"].casefold(),x["program"]["name"].casefold(),x["candidate_id"]))
 page=int(request.get("page",1));size=int(request.get("page_size",20));start=(page-1)*size
 return {"schema_version":"1.0","request_id":str(uuid.uuid4()),"data_version":data_version,"model_version":model_version,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"result_count":len(eligible),"warnings":[],"results":eligible[start:start+size]}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--data-version",required=True);ap.add_argument("--model-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 req=json.loads(a.request.read_text(encoding="utf-8"));cands=json.loads(a.candidates.read_text(encoding="utf-8"));response=match(req,cands,a.data_version,a.model_version);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(response,indent=2),encoding="utf-8")
if __name__=="__main__":main()
