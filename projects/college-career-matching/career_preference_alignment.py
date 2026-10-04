#!/usr/bin/env python3
"""Align explicit career preferences to occupation attributes at pathway grain."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd
OPS={"target_distance","higher_preferred","lower_preferred","range","categorical_match"}
def read(p):return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
 m=[c for c in cols if c not in df.columns]
 if m:raise ValueError(f"{label} missing columns: {m}")
def yes(v):return str(v).strip().lower() in {"1","true","yes","y"}
def numeric(v):return pd.to_numeric(v,errors="coerce")
def align_row(r):
 op=r["operator"]
 if op=="categorical_match":
  if str(r["attribute_value"]).strip()=="":return None
  return 1.0 if str(r["attribute_value"]).strip().casefold()==str(r["target_value"]).strip().casefold() else 0.0
 x=r["attribute_value_num"];lo=r["scale_min_num"];hi=r["scale_max_num"]
 if pd.isna(x) or pd.isna(lo) or pd.isna(hi) or hi<=lo:return None
 span=hi-lo
 if op=="target_distance":
  t=r["target_value_num"];return None if pd.isna(t) else max(0.0,min(1.0,1-abs(x-t)/span))
 if op=="higher_preferred":return max(0.0,min(1.0,(x-lo)/span))
 if op=="lower_preferred":return max(0.0,min(1.0,(hi-x)/span))
 if op=="range":
  a=r["target_min_num"];b=r["target_max_num"]
  if pd.isna(a) or pd.isna(b) or b<a:return None
  if a<=x<=b:return 1.0
  return max(0.0,min(1.0,1-(a-x if x<a else x-b)/span))
 return None
def main():
 p=argparse.ArgumentParser();p.add_argument("--pathways",type=Path,required=True);p.add_argument("--occupation-attributes",type=Path,required=True);p.add_argument("--preferences",type=Path,required=True);p.add_argument("--out-dir",type=Path,required=True);a=p.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 paths=read(a.pathways);req(paths,["occ_code"],"pathways");attrs=read(a.occupation_attributes);req(attrs,["occ_code","attribute_id","attribute_value"],"occupation attributes");prefs=read(a.preferences);req(prefs,["preference_id","attribute_id","target_value","importance","priority_explicit","operator"],"preferences")
 if attrs[["occ_code","attribute_id"]].duplicated().any():raise ValueError("duplicate occupation attribute")
 if prefs["preference_id"].duplicated().any():raise ValueError("duplicate preference_id")
 prefs=prefs[prefs["priority_explicit"].map(yes)].copy();bad=set(prefs["operator"])-OPS
 if bad:raise ValueError(f"unsupported preference operators: {sorted(bad)}")
 prefs["importance_num"]=pd.to_numeric(prefs["importance"],errors="raise")
 if (prefs["importance_num"]<0).any():raise ValueError("importance cannot be negative")
 for c in ["target_value","scale_min","scale_max","target_min","target_max"]:
  if c not in prefs:prefs[c]=""
  prefs[c+"_num"]=numeric(prefs[c])
 numeric_ops=prefs["operator"].isin(["target_distance","higher_preferred","lower_preferred","range"])
 if (numeric_ops & (prefs["scale_min_num"].isna()|prefs["scale_max_num"].isna()|(prefs["scale_max_num"]<=prefs["scale_min_num"]))).any():raise ValueError("numeric preference operators require valid scale_min < scale_max")
 if ((prefs["operator"]=="target_distance") & prefs["target_value_num"].isna()).any():raise ValueError("target_distance requires numeric target_value")
 if ((prefs["operator"]=="range") & (prefs["target_min_num"].isna()|prefs["target_max_num"].isna()|(prefs["target_max_num"]<prefs["target_min_num"]))).any():raise ValueError("range requires target_min <= target_max")
 joined=paths.merge(attrs,on="occ_code",how="left",validate="many_to_many").merge(prefs,on="attribute_id",how="inner",validate="many_to_many");joined["attribute_value_num"]=numeric(joined["attribute_value"]);joined["alignment"]=joined.apply(align_row,axis=1);joined["weighted_alignment_numerator"]=joined["alignment"]*joined["importance_num"]
 groupcols=[c for c in ["candidate_id","UNITID","program_id","cip_code","occ_code"] if c in joined];summaries=[]
 for keys,g in joined.groupby(groupcols,dropna=False,sort=False):
  if not isinstance(keys,tuple):keys=(keys,)
  row=dict(zip(groupcols,keys));obs=g[g["alignment"].notna()];denom=obs["importance_num"].sum();row["career_alignment_observed_preferences"]=int(len(obs));row["career_alignment_total_explicit_preferences"]=int(len(prefs));row["career_alignment_coverage_rate"]=(len(obs)/len(prefs)) if len(prefs) else None;row["career_alignment_score"]=(obs["weighted_alignment_numerator"].sum()/denom) if denom>0 else None;row["career_alignment_status"]="observed" if denom>0 else ("no_explicit_preferences" if len(prefs)==0 else "insufficient_attribute_evidence");summaries.append(row)
 pd.DataFrame(joined).to_csv(a.out_dir/"career_preference_alignment_detail.csv",index=False);pd.DataFrame(summaries).to_csv(a.out_dir/"career_pathway_alignment.csv",index=False);qa={"explicit_preference_count":int(len(prefs)),"pathway_alignment_rows":int(len(summaries)),"operators_used":sorted(prefs["operator"].unique().tolist()),"rule":"Alignment operator semantics are explicit per preference. Missing attributes reduce coverage rather than becoming mismatch; unspecified preferences never participate."};(a.out_dir/"career_preference_alignment_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
if __name__=="__main__":main()
