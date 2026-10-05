#!/usr/bin/env python3
"""Translate governed questionnaire answers into a v1 match-service request."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from constraint_field_registry import load_registry,validate_constraint
def load(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def answered(v):return v is not None and v!="" and v!=[] and v!={}
def validate_definitions(defs,registry=None):
 registry=registry or load_registry();ids=set()
 for q in defs.get("questions",[]):
  qid=q.get("question_id")
  if not qid or qid in ids:raise ValueError(f"invalid or duplicate question_id: {qid}")
  ids.add(qid);m=q.get("mapping",{})
  if m.get("target") in {"constraint","conditional_constraint"}:validate_constraint({"field":m.get("field"),"operator":m.get("operator")},registry)
 return True
def option_values(options,path):
 cur=options
 for part in path.split("."):
  cur=cur.get(part,{}) if isinstance(cur,dict) else {}
 return {str(x.get("value")) for x in cur if isinstance(x,dict)} if isinstance(cur,list) else set()
def map_answers(defs,answers,options=None):
 validate_definitions(defs);qs={q["question_id"]:q for q in defs["questions"]};unknown=set(answers)-set(qs)
 if unknown:raise ValueError(f"unknown question ids: {sorted(unknown)}")
 mode=answers.get("decision_mode")
 if not mode:raise ValueError("decision_mode is required")
 out={"schema_version":"1.0","decision_mode":mode,"constraints":[],"preferences":[],"career_preferences":[],"geography":{"school_location_semantics":"no_preference","selected_states":[],"work_market_semantics":"unspecified","intended_work_market":None},"transfer_context":None,"pinned_candidate_ids":[],"page":1,"page_size":20,"data_version":options.get("data_version") if options else None,"model_version":None}
 for qid,val in answers.items():
  if qid=="decision_mode" or not answered(val):continue
  q=qs[qid]
  if q.get("visible_for_modes") and mode not in q["visible_for_modes"]:raise ValueError(f"{qid} is not applicable to decision mode {mode}")
  vw=q.get("visible_when")
  if vw and answers.get(vw["question_id"])!=vw["value"]:raise ValueError(f"{qid} is not currently visible")
  if options and q.get("option_source"):
   allowed=option_values(options,q["option_source"]);vals=val if isinstance(val,list) else [val]
   bad=[x for x in vals if str(x) not in allowed]
   if bad:raise ValueError(f"{qid} contains values outside active options: {bad}")
  m=q["mapping"];target=m["target"]
  if target=="constraint":
   c={"constraint_id":qid,"field":m["field"],"operator":m["operator"],"value":val,"unknown_policy":m["unknown_policy"],"source_question_id":qid};validate_constraint(c);out["constraints"].append(c)
   if qid=="school_states":out["geography"]["school_location_semantics"]="selected_places";out["geography"]["selected_states"]=val
  elif target=="conditional_constraint":
   if val==m["when_value"]:
    c={"constraint_id":qid,"field":m["field"],"operator":m["operator"],"value":m["value"],"unknown_policy":m["unknown_policy"],"source_question_id":qid};validate_constraint(c);out["constraints"].append(c)
  elif target=="preference":
   imp=float(val)
   if imp<0:raise ValueError(f"negative importance for {qid}")
   out["preferences"].append({"preference_id":qid,"dimension":m["dimension"],"importance":imp,"priority_explicit":True,"source_question_id":qid})
  elif target=="career_preference":
   imp=float(val)
   if imp<0:raise ValueError(f"negative importance for {qid}")
   out["career_preferences"].append({"preference_id":qid,"attribute_id":m["attribute_id"],"operator":m["operator"],"importance":imp,"priority_explicit":True,"target_value":None,"target_min":None,"target_max":None,"scale_min":None,"scale_max":None,"source_question_id":qid})
  elif target=="geography.work_market_semantics":out["geography"]["work_market_semantics"]=val
  elif target=="geography.intended_work_market":
   if not isinstance(val,dict) or not val.get("market_id") or not val.get("market_type"):raise ValueError("work_market requires market_id and market_type")
   out["geography"]["intended_work_market"]={"market_id":str(val["market_id"]),"market_type":str(val["market_type"])}
  elif target=="transfer_context.source_institution_id":out["transfer_context"]={"source_institution_id":val,"source_system":None,"completed_course_ids":[],"target_program_required":False}
  elif target!="decision_mode":raise ValueError(f"unsupported mapping target {target}")
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument("--definitions",type=Path,required=True);p.add_argument("--answers",type=Path,required=True);p.add_argument("--options",type=Path);p.add_argument("--output",type=Path,required=True);a=p.parse_args();r=map_answers(load(a.definitions),load(a.answers),load(a.options) if a.options else None);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2),encoding="utf-8")
if __name__=="__main__":main()
