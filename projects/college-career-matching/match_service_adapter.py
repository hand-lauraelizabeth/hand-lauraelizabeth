#!/usr/bin/env python3
"""Pure-Python service boundary for the interactive College + Career matcher."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from labor_evidence_service_adapter import build_for_candidate
from career_pathway_service import career_summary
from constraint_field_registry import load_registry,validate_constraint
from ranking_binding_contract import validate_bundle,ranking_context_id
MODES={"broad_exploration","career_first","college_program_first","compare_known","transfer","returning_student"};UNKNOWN={"keep_visible","exclude_unknown"};DIMS={"college_fit","affordability","academic_program_fit","transfer_pathway_fit","admissions_context","career_pathway_fit","current_labor_market","long_term_outlook","geographic_fit","transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"};CAREER_OPS={"target_distance","higher_preferred","lower_preferred","range","categorical_match"};MISSING={None,"","NA","N/A","NULL","NONE"}
def clean(v:Any)->str:return str(v).strip() if v is not None else ""
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
 geography=r.get("geography") or {}
 if not isinstance(geography,dict):raise ValueError("geography must be an object")
 market=geography.get("intended_work_market")
 semantics=geography.get("work_market_semantics")
 if semantics is None:semantics="selected_market" if market else "unspecified"
 if semantics not in {"school_local","selected_market","national","remote_or_flexible","unspecified"}:raise ValueError("unsupported work_market_semantics")
 if semantics=="selected_market":
  if not isinstance(market,dict) or not clean(market.get("market_id")) or not clean(market.get("market_type")):raise ValueError("selected_market requires intended_work_market market_id and market_type")
 elif market not in (None,{}):
  raise ValueError("intended_work_market is only valid with selected_market semantics")
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
def reason(code,text,evidence_ids=None,supporting_evidence=None):return {"code":code,"text":text,"evidence_ids":list(evidence_ids or []),"supporting_evidence":list(supporting_evidence or [])}
def trace_row(evidence_id,family,state,row=None,geography=None):
 row=row or {};geography=geography or {}
 measures={};measure_states={}
 if family=="current_labor_market":
  measures={"employment":row.get("employment"),"median_wage":row.get("median_wage")}
  measure_states={"employment":row.get("employment_state","missing"),"median_wage":row.get("wage_state","missing")}
 elif family=="long_term_outlook":
  measures={"employment_change_pct":row.get("employment_change_pct"),"annual_openings":row.get("annual_openings"),"base_year":row.get("base_year"),"projection_year":row.get("projection_year")}
 return {"evidence_id":evidence_id,"evidence_family":family,"soc_code":clean(row.get("soc_code")) or None,"occupation_title":clean(row.get("occupation_title")) or None,"geography":{"market_id":clean(geography.get("market_id")) or None,"market_type":clean(geography.get("market_type")) or None,"market_label":clean(geography.get("market_label")) or None,"projection_geography":clean(row.get("projection_geography")) or clean(geography.get("projection_geography")) or None,"work_market_semantics":clean(geography.get("work_market_semantics")) or None},"source_vintage":clean(row.get("source_vintage")) or None,"evidence_state":clean(state) or "unknown","measures":measures,"measure_states":measure_states}
def labor_trace(family_name,family,geography=None):
 rows=sorted((family or {}).get("soc_evidence") or [],key=lambda r:(clean(r.get("soc_code")),clean(r.get("occupation_title")),clean(r.get("source_vintage"))))
 state=(family or {}).get("evidence_state") or "unknown"
 geo=dict(geography or {})
 if family_name=="current_labor_market":
  for k in ["market_id","market_type","market_label"]:
   if (family or {}).get(k) not in (None,""):geo[k]=(family or {}).get(k)
 if not rows:return [trace_row(f"labor:{family_name}:summary",family_name,state,geography=geo)]
 out=[]
 for i,row in enumerate(rows,1):
  soc=clean(row.get("soc_code")) or "unknown";out.append(trace_row(f"labor:{family_name}:soc:{soc}:{i}",family_name,state,row,geo))
 return out
def explicit_priority(request,dimension):
 for p in request.get("preferences",[]):
  if p.get("priority_explicit") is True and p.get("dimension")==dimension and (num(p.get("importance")) or 0)>0:return p
 return None
def labor_priority_explanations(request,labor):
 context=[];unknowns=[];geography=request.get("geography") or {}
 current=explicit_priority(request,"current_labor_market")
 if current:
  family=(labor or {}).get("selected_work_market") or {};state=family.get("evidence_state")
  ids=[f"preference:{current.get('preference_id') or 'current_labor_market'}","labor:selected_work_market"]
  trace=labor_trace("current_labor_market",family,{"work_market_semantics":geography.get("work_market_semantics")})
  ids+= [x["evidence_id"] for x in trace]
  if state=="observed" and family.get("soc_evidence"):
   label=clean(family.get("market_label")) or "the selected work market"
   context.append(reason("CURRENT_LABOR_PRIORITY_EVIDENCE_AVAILABLE",f"Current occupation-level labor-market evidence is available for {label}, which you marked as a priority. Wage and employment values remain descriptive here and are not treated as inherently positive or converted into a browser-side score.",ids,trace))
  elif state=="unavailable":
   unknowns.append(reason("CURRENT_LABOR_PRIORITY_EVIDENCE_UNAVAILABLE","You marked current labor-market context as a priority, but governed current-market evidence is unavailable for this candidate in the selected market. Missing evidence is not treated as weak demand or a negative score.",ids,trace))
  else:
   semantics=clean(geography.get("work_market_semantics")) or "unspecified"
   unknowns.append(reason("CURRENT_LABOR_PRIORITY_MARKET_NOT_EVALUATED",f"You marked current labor-market context as a priority, but no candidate-specific current-market evidence was evaluated under the '{semantics}' work-market setting. No current-market value is assumed.",ids,trace))
 future=explicit_priority(request,"long_term_outlook")
 if future:
  family=(labor or {}).get("long_term_outlook") or {};state=family.get("evidence_state");ids=[f"preference:{future.get('preference_id') or 'long_term_outlook'}","labor:long_term_outlook"]
  trace=labor_trace("long_term_outlook",family)
  ids+= [x["evidence_id"] for x in trace]
  if state=="observed" and family.get("soc_evidence"):
   context.append(reason("LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_AVAILABLE","Long-term occupational projection evidence is available for related pathways, which you marked as a priority. Projected change and openings remain descriptive and are not treated as current hiring evidence or an automatic positive signal.",ids,trace))
  else:
   unknowns.append(reason("LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_UNAVAILABLE","You marked long-term occupational outlook as a priority, but governed projection evidence is unavailable for this candidate's related pathways. Missing projections are not converted to zero or treated as a negative score.",ids,trace))
 return context,unknowns
def result(c,status,codes,labor=None,request=None):
 dims=dimension_rows(c);unknown=[x for x in codes if x.startswith("constraint_unknown")];coverage=[d["coverage_rate"] for d in dims];avg=sum(coverage)/len(coverage) if coverage else 0;labor=labor or {"selected_work_market":{"evidence_state":"not_loaded"},"long_term_outlook":{"evidence_state":"not_loaded"}};priority_context,priority_unknowns=labor_priority_explanations(request or {},labor)
 return {"candidate_id":str(c["candidate_id"]),"institution":{"unitid":str(c["UNITID"]),"name":str(c["institution_name"]),"city":c.get("city") or None,"state":c.get("state") or None},"program":{"program_id":str(c["program_id"]),"name":str(c["program_name"]),"cip_code":str(c["cip_code"]),"credential_level":c.get("credential_level") or None},"eligibility":{"status":status,"reason_codes":codes},"dimensions":dims,"explanation":{"why_it_matches":[reason("eligible_constraints","Meets the evaluated must-have constraints.",["constraints:evaluated"])] if status=="eligible" else [],"tradeoffs":[],"context":priority_context,"unknowns":[reason(x,"Evidence needed to evaluate one must-have constraint is currently unavailable.",[x]) for x in unknown]+priority_unknowns},"career_pathways":career_summary(c),"transfer":c.get("transfer"),"labor_market":labor,"evidence_coverage":{"overall_status":"broad" if avg>=.8 else ("partial" if avg>=.4 else "limited"),"review_flags":c.get("review_flags",[])},"source_freshness":c.get("source_freshness",[])}
def request_id(request,data_version,model_version):
 payload=json.dumps({"request":request,"data_version":data_version,"model_version":model_version},sort_keys=True,separators=(",",":"));return "req_"+hashlib.sha256(payload.encode()).hexdigest()[:20]
def match(request,candidates,data_version,model_version,current_labor=None,projections=None,generated_at_utc=None,ranking_bundle=None,production_authorized=False):
 validate_request(request);eligible=[];required={"candidate_id","UNITID","institution_name","program_id","program_name","cip_code"};current_labor=current_labor or [];projections=projections or [];work=request.get("geography",{}).get("intended_work_market") or None;seen=set()
 for c in candidates:
  miss=required-set(c)
  if miss:raise ValueError(f"candidate missing fields: {sorted(miss)}")
  cid=str(c.get("candidate_id","")).strip()
  if not cid:raise ValueError("candidate_id must be nonblank")
  if cid in seen:raise ValueError(f"duplicate candidate_id: {cid}")
  seen.add(cid);status,codes=disposition(c,request["constraints"])
  if status!="excluded":eligible.append(result(c,status,codes,build_for_candidate(c,current_labor,projections,work),request))
 eligible_ids=[x["candidate_id"] for x in eligible]
 if ranking_bundle is not None:
  ranked=validate_bundle(ranking_bundle,request,data_version,model_version,eligible_ids)
  for x in eligible:
   r=ranked.get(x["candidate_id"])
   if r:
    x["recommendation"]={"status":"review_eligible_ranked","rank":r["rank"],"baseline_score":r["baseline_score"],"review_eligibility":"eligible_for_review","production_authorized":bool(production_authorized)}
   else:
    x["recommendation"]={"status":"eligible_unranked","rank":None,"baseline_score":None,"review_eligibility":None,"production_authorized":bool(production_authorized)}
  eligible.sort(key=lambda x:(0,ranked[x["candidate_id"]]["rank"],x["candidate_id"]) if x["candidate_id"] in ranked else (1,x["institution"]["name"].casefold(),x["program"]["name"].casefold(),x["candidate_id"]))
  ordering={"mode":"review_eligible_ranking","ranking_context_id":ranking_context_id(request,data_version,model_version),"review_eligible_ranked_count":len(ranked),"unranked_eligible_count":len(eligible)-len(ranked),"production_authorized":bool(production_authorized)}
 else:
  for x in eligible:x["recommendation"]={"status":"not_ranked","rank":None,"baseline_score":None,"review_eligibility":None,"production_authorized":bool(production_authorized)}
  eligible.sort(key=lambda x:(x["institution"]["name"].casefold(),x["program"]["name"].casefold(),x["candidate_id"]))
  ordering={"mode":"deterministic_unranked","ranking_context_id":None,"review_eligible_ranked_count":0,"unranked_eligible_count":len(eligible),"production_authorized":bool(production_authorized)}
 page=int(request.get("page",1));size=int(request.get("page_size",20));start=(page-1)*size;total=len(eligible);pages=(total+size-1)//size if total else 0;stamp=generated_at_utc or datetime.now(timezone.utc).isoformat()
 return {"schema_version":"1.0","request_id":request_id(request,data_version,model_version),"data_version":data_version,"model_version":model_version,"generated_at_utc":stamp,"result_count":total,"pagination":{"page":page,"page_size":size,"total_pages":pages,"has_next":page<pages,"has_previous":page>1 and pages>0},"ordering":ordering,"warnings":[],"results":eligible[start:start+size]}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--request",type=Path,required=True);ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--current-labor",type=Path);ap.add_argument("--projections",type=Path);ap.add_argument("--ranking-bundle",type=Path);ap.add_argument("--data-version",required=True);ap.add_argument("--model-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args();req=json.loads(a.request.read_text());cands=json.loads(a.candidates.read_text());load=lambda p:json.loads(p.read_text()) if p else [];response=match(req,cands,a.data_version,a.model_version,load(a.current_labor),load(a.projections),ranking_bundle=load(a.ranking_bundle));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(response,indent=2))
if __name__=="__main__":main()
