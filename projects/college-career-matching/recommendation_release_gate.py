#!/usr/bin/env python3
"""Fail-closed release gate for recommendation pipeline artifacts.

The gate evaluates only explicitly configured checks. It never invents numeric
acceptance thresholds. Missing required stages block release.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd


def read_json(p): return json.loads(p.read_text(encoding="utf-8"))
def truth(v): return str(v).strip().lower() in {"1","true","yes","y"}

def resolve(obj,path):
 cur=obj
 for part in path.split("."):
  if isinstance(cur,dict) and part in cur: cur=cur[part]
  else: return None,False
 return cur,True

def compare(actual,op,expected):
 if op=="exists": return actual is not None
 if op=="eq": return str(actual)==str(expected)
 if op=="neq": return str(actual)!=str(expected)
 try: a=float(actual); e=float(expected)
 except (TypeError,ValueError): return False
 return {"gte":a>=e,"gt":a>e,"lte":a<=e,"lt":a<e}.get(op,False)

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--gate-manifest",type=Path,required=True,help="stage_id,artifact_path,required,check_path,operator,expected")
 p.add_argument("--out-dir",type=Path,required=True)
 a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
 m=pd.read_csv(a.gate_manifest,dtype=str,keep_default_na=False)
 required=["stage_id","artifact_path","required","check_path","operator","expected"]
 miss=[c for c in required if c not in m.columns]
 if miss: raise ValueError(f"gate manifest missing columns: {miss}")
 if m["stage_id"].duplicated().any(): raise ValueError("stage_id must be unique")
 rows=[]
 for r in m.itertuples(index=False):
  path=Path(r.artifact_path); required_stage=truth(r.required)
  if not path.exists():
   status="BLOCK" if required_stage else "NOT_AVAILABLE_OPTIONAL"
   rows.append({"stage_id":r.stage_id,"artifact_path":str(path),"required":required_stage,"artifact_present":False,"check_path":r.check_path,"operator":r.operator,"expected":r.expected,"actual":"","status":status,"reason":"artifact_missing"}); continue
  try: obj=read_json(path)
  except Exception as e:
   rows.append({"stage_id":r.stage_id,"artifact_path":str(path),"required":required_stage,"artifact_present":True,"check_path":r.check_path,"operator":r.operator,"expected":r.expected,"actual":"","status":"BLOCK" if required_stage else "OPTIONAL_CHECK_FAILED","reason":f"invalid_json:{type(e).__name__}"}); continue
  actual,found=resolve(obj,r.check_path) if r.check_path.strip() else (obj,True)
  if not found:
   passed=False; reason="check_path_missing"
  else:
   passed=compare(actual,r.operator.strip().lower(),r.expected); reason="check_passed" if passed else "check_failed"
  status="PASS" if passed else ("BLOCK" if required_stage else "OPTIONAL_CHECK_FAILED")
  rows.append({"stage_id":r.stage_id,"artifact_path":str(path),"required":required_stage,"artifact_present":True,"check_path":r.check_path,"operator":r.operator,"expected":r.expected,"actual":json.dumps(actual) if isinstance(actual,(dict,list)) else str(actual),"status":status,"reason":reason})
 detail=pd.DataFrame(rows)
 blocked=detail[detail["status"]=="BLOCK"]
 decision="BLOCKED" if len(blocked) else "ELIGIBLE_FOR_REVIEW"
 detail.to_csv(a.out_dir/"recommendation_release_gate_detail.csv",index=False)
 result={"release_decision":decision,"required_stage_count":int(detail["required"].sum()),"blocked_required_checks":int(len(blocked)),"optional_check_failures":int((detail["status"]=="OPTIONAL_CHECK_FAILED").sum()),
         "rule":"ELIGIBLE_FOR_REVIEW is not production authorization. The gate evaluates only manifest-declared checks and invents no thresholds."}
 (a.out_dir/"recommendation_release_decision.json").write_text(json.dumps(result,indent=2),encoding="utf-8")

if __name__=="__main__": main()
