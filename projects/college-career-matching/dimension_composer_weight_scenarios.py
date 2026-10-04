#!/usr/bin/env python3
"""Compose normalized features into dimensions and generate explicit-priority scenarios.

No final production recommendation score is authorized here. Coverage is emitted
separately and dimensions absent from explicit user priorities receive no weight.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd


def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
 m=[c for c in cols if c not in df.columns]
 if m: raise ValueError(f"{label} missing columns: {m}")
def yes(v): return str(v).strip().lower() in {"1","true","yes","y"}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--normalized-features",type=Path,required=True,help="candidate_id,feature_id,dimension,normalized_value,evidence_state")
 p.add_argument("--composition-policy",type=Path,required=True,help="feature_id,within_dimension_weight,partial_policy")
 p.add_argument("--preferences",type=Path,required=True,help="dimension,importance,priority_explicit")
 p.add_argument("--perturbation",type=float,default=0.10,help="relative sensitivity perturbation; 0.10 = +/-10%%")
 p.add_argument("--out-dir",type=Path,required=True)
 a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
 f=read(a.normalized_features); req(f,["candidate_id","feature_id","dimension","normalized_value","evidence_state"],"normalized features")
 pol=read(a.composition_policy); req(pol,["feature_id","within_dimension_weight","partial_policy"],"composition policy")
 prefs=read(a.preferences); req(prefs,["dimension","importance","priority_explicit"],"preferences")
 if pol["feature_id"].duplicated().any(): raise ValueError("duplicate composition-policy feature_id")
 if prefs["dimension"].duplicated().any(): raise ValueError("duplicate preference dimension")
 f=f.merge(pol,on="feature_id",how="left",validate="many_to_one")
 if f["within_dimension_weight"].eq("").any(): raise ValueError("normalized feature lacks composition policy")
 f["value_num"]=pd.to_numeric(f["normalized_value"],errors="coerce")
 f["weight_num"]=pd.to_numeric(f["within_dimension_weight"],errors="raise")
 if (f["weight_num"]<0).any(): raise ValueError("within-dimension weights cannot be negative")
 bad=set(f["partial_policy"])-{"block","renormalize_observed"}
 if bad: raise ValueError(f"unsupported partial policies: {sorted(bad)}")
 # One policy per dimension prevents feature-specific missingness rules from changing composition unpredictably.
 if (f.groupby("dimension")["partial_policy"].nunique()>1).any(): raise ValueError("partial_policy must be consistent within each dimension")
 details=[]; dims=[]
 for (cid,dim),g in f.groupby(["candidate_id","dimension"],sort=False,dropna=False):
  expected=float(g["weight_num"].sum()); obs=g[g["value_num"].notna()].copy(); observed=float(obs["weight_num"].sum())
  coverage=(observed/expected) if expected>0 else None; policy=g["partial_policy"].iloc[0]
  complete=len(obs)==len(g)
  if expected<=0: value=None; status="invalid_zero_expected_weight"
  elif complete: value=float((obs["value_num"]*obs["weight_num"]).sum()/observed) if observed>0 else None; status="complete"
  elif policy=="renormalize_observed" and observed>0: value=float((obs["value_num"]*obs["weight_num"]).sum()/observed); status="partial_renormalized"
  else: value=None; status="partial_blocked"
  dims.append({"candidate_id":cid,"dimension":dim,"dimension_value":value,"dimension_status":status,"dimension_coverage_rate":coverage,
               "expected_feature_weight":expected,"observed_feature_weight":observed,"partial_policy":policy})
  for _,r in g.iterrows():
   details.append({"candidate_id":cid,"dimension":dim,"feature_id":r["feature_id"],"normalized_value":r["value_num"],"within_dimension_weight":r["weight_num"],"evidence_state":r["evidence_state"],"partial_policy":policy})
 dimdf=pd.DataFrame(dims); detail=pd.DataFrame(details)
 # Only explicit dimensions generate scenario weights.
 active=prefs[prefs["priority_explicit"].map(yes)].copy(); active["importance_num"]=pd.to_numeric(active["importance"],errors="raise")
 if (active["importance_num"]<0).any(): raise ValueError("importance cannot be negative")
 if len(active) and active["importance_num"].sum()<=0: raise ValueError("explicit priorities sum to zero")
 scenarios=[]
 if len(active):
  base=active.set_index("dimension")["importance_num"].to_dict()
  def emit(sid,weights):
   total=sum(weights.values())
   if total<=0: return
   for d,w in weights.items(): scenarios.append({"scenario_id":sid,"dimension":d,"weight":w/total})
  emit("baseline",base)
  for d in base:
   up=dict(base); up[d]=base[d]*(1+a.perturbation); emit(f"perturb_up__{d}",up)
   down=dict(base); down[d]=base[d]*max(0,1-a.perturbation); emit(f"perturb_down__{d}",down)
   loo={k:v for k,v in base.items() if k!=d}; emit(f"leave_out__{d}",loo)
 scen=pd.DataFrame(scenarios,columns=["scenario_id","dimension","weight"])
 dimdf.to_csv(a.out_dir/"composed_candidate_dimensions.csv",index=False)
 detail.to_csv(a.out_dir/"dimension_feature_contributions.csv",index=False)
 scen.to_csv(a.out_dir/"explicit_preference_weight_scenarios.csv",index=False)
 qa={"candidate_dimension_rows":int(len(dimdf)),"explicit_priority_dimensions":int(len(active)),"scenario_count":int(scen["scenario_id"].nunique()) if len(scen) else 0,
     "perturbation":a.perturbation,"rule":"Only explicit priority dimensions receive scenario weights. Coverage remains metadata and is never converted into desirability."}
 (a.out_dir/"dimension_composition_weight_scenario_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__": main()
