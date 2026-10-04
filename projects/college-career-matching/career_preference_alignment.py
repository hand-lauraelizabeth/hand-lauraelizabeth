#!/usr/bin/env python3
"""Align explicit career preferences to occupation attributes at pathway grain.

This is a validation/feature layer, not a final recommendation score. It never
creates preferences for profile dimensions the user did not explicitly activate.
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
    p.add_argument("--pathways",type=Path,required=True,help="program/candidate pathway evidence with occ_code")
    p.add_argument("--occupation-attributes",type=Path,required=True,help="occ_code,attribute_id,attribute_value")
    p.add_argument("--preferences",type=Path,required=True,help="preference_id,attribute_id,target_value,importance,priority_explicit")
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
    paths=read(a.pathways); req(paths,["occ_code"],"pathways")
    attrs=read(a.occupation_attributes); req(attrs,["occ_code","attribute_id","attribute_value"],"occupation attributes")
    prefs=read(a.preferences); req(prefs,["preference_id","attribute_id","target_value","importance","priority_explicit"],"preferences")
    if attrs[["occ_code","attribute_id"]].duplicated().any(): raise ValueError("duplicate occupation attribute")
    if prefs["preference_id"].duplicated().any(): raise ValueError("duplicate preference_id")
    prefs=prefs[prefs["priority_explicit"].map(yes)].copy()
    prefs["target_value_num"]=pd.to_numeric(prefs["target_value"],errors="raise")
    prefs["importance_num"]=pd.to_numeric(prefs["importance"],errors="raise")
    if (prefs["importance_num"]<0).any(): raise ValueError("importance cannot be negative")
    joined=paths.merge(attrs,on="occ_code",how="left",validate="many_to_many")
    joined=joined.merge(prefs,on="attribute_id",how="inner",validate="many_to_many")
    joined["attribute_value_num"]=pd.to_numeric(joined["attribute_value"],errors="coerce")
    # Alignment assumes both target and occupation attribute are on the same documented scale.
    # 1 - normalized absolute distance; scale bounds are preference-specific if supplied.
    if "scale_min" in prefs.columns and "scale_max" in prefs.columns:
        joined["scale_min_num"]=pd.to_numeric(joined["scale_min"],errors="coerce")
        joined["scale_max_num"]=pd.to_numeric(joined["scale_max"],errors="coerce")
        span=joined["scale_max_num"]-joined["scale_min_num"]
        joined["alignment"]=(1-(joined["attribute_value_num"]-joined["target_value_num"]).abs()/span).clip(0,1).where(span>0)
    else:
        joined["alignment"]=pd.NA
    joined["weighted_alignment_numerator"]=joined["alignment"]*joined["importance_num"]
    keycols=[c for c in ["candidate_id","UNITID","program_id","cip_code","occ_code"] if c in joined.columns]
    groupcols=[c for c in ["candidate_id","UNITID","program_id","cip_code","occ_code"] if c in joined.columns]
    summaries=[]
    for keys,g in joined.groupby(groupcols,dropna=False,sort=False):
        if not isinstance(keys,tuple): keys=(keys,)
        row=dict(zip(groupcols,keys)); obs=g[g["alignment"].notna()]
        denom=obs["importance_num"].sum()
        row["career_alignment_observed_preferences"]=int(len(obs))
        row["career_alignment_total_explicit_preferences"]=int(len(prefs))
        row["career_alignment_coverage_rate"]=(len(obs)/len(prefs)) if len(prefs) else None
        row["career_alignment_score"]=(obs["weighted_alignment_numerator"].sum()/denom) if denom>0 else None
        row["career_alignment_status"]="observed" if denom>0 else ("no_explicit_preferences" if len(prefs)==0 else "insufficient_attribute_evidence")
        summaries.append(row)
    summary=pd.DataFrame(summaries)
    joined.to_csv(a.out_dir/"career_preference_alignment_detail.csv",index=False)
    summary.to_csv(a.out_dir/"career_pathway_alignment.csv",index=False)
    qa={"explicit_preference_count":int(len(prefs)),"pathway_alignment_rows":int(len(summary)),
        "rule":"Alignment is computed only for explicit preferences with compatible documented scales; missing occupation attributes reduce coverage rather than becoming mismatch."}
    (a.out_dir/"career_preference_alignment_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__": main()
