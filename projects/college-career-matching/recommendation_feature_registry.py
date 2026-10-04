#!/usr/bin/env python3
"""Validate and materialize the declarative recommendation feature registry.

The registry is the only allowed bridge from assembled evidence columns to named
recommendation dimensions. It does not assign weights or compute a final score.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

ALLOWED_DIMENSIONS={
 "college_fit","affordability","academic_program_fit","transfer_pathway_fit",
 "admissions_context","career_pathway_fit","current_labor_market_evidence",
 "long_term_outlook","geographic_fit","evidence_quality_coverage"
}
ALLOWED_ROLES={"comparison","context","coverage","explanation_only"}
ALLOWED_DIRECTIONS={"higher_better","lower_better","target_match","none"}

def read(p): return pd.read_csv(p,dtype=str,keep_default_na=False)
def req(df,cols,label):
 m=[c for c in cols if c not in df.columns]
 if m: raise ValueError(f"{label} missing columns: {m}")

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--features",type=Path,required=True,help="model_ready_candidate_features.csv")
 p.add_argument("--registry",type=Path,required=True)
 p.add_argument("--out-dir",type=Path,required=True)
 a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
 features=read(a.features); req(features,["candidate_id"],"features")
 if features["candidate_id"].duplicated().any(): raise ValueError("duplicate candidate_id")
 reg=read(a.registry)
 req(reg,["feature_id","source_column","dimension","role","direction","source_family","source_vintage","grain","normalization_policy"],"registry")
 if reg["feature_id"].duplicated().any(): raise ValueError("duplicate feature_id")
 bad_dim=set(reg["dimension"])-ALLOWED_DIMENSIONS
 bad_role=set(reg["role"])-ALLOWED_ROLES
 bad_dir=set(reg["direction"])-ALLOWED_DIRECTIONS
 if bad_dim: raise ValueError(f"unsupported dimensions: {sorted(bad_dim)}")
 if bad_role: raise ValueError(f"unsupported roles: {sorted(bad_role)}")
 if bad_dir: raise ValueError(f"unsupported directions: {sorted(bad_dir)}")
 missing_cols=reg[~reg["source_column"].isin(features.columns)].copy()
 active=reg[reg["source_column"].isin(features.columns)].copy()
 # Comparison features require explicit normalization and direction. No ad hoc scoring columns.
 bad_comp=active[(active["role"]=="comparison") & ((active["normalization_policy"].str.strip()=="") | (active["direction"]=="none"))]
 if len(bad_comp): raise ValueError(f"comparison features missing normalization/direction: {bad_comp['feature_id'].tolist()}")
 # Coverage features cannot be used as positive/negative fit signals.
 bad_cov=active[(active["role"]=="coverage") & (active["direction"]!="none")]
 if len(bad_cov): raise ValueError(f"coverage features must use direction=none: {bad_cov['feature_id'].tolist()}")
 lineage_cols=["feature_id","source_column","dimension","role","direction","source_family","source_vintage","grain","normalization_policy"]
 for optional in ["description","source_url_field","evidence_state_field","specificity","notes"]:
  if optional in reg.columns: lineage_cols.append(optional)
 active[lineage_cols].to_csv(a.out_dir/"recommendation_feature_lineage.csv",index=False)
 missing_cols.to_csv(a.out_dir/"recommendation_feature_registry_missing_columns.csv",index=False)
 # Long form makes downstream audit/normalization consume declared feature IDs rather than raw column names.
 frames=[]
 for r in active.itertuples(index=False):
  t=features[["candidate_id",r.source_column]].copy(); t=t.rename(columns={r.source_column:"raw_value"})
  t["feature_id"]=r.feature_id; t["dimension"]=r.dimension; t["role"]=r.role; t["direction"]=r.direction; t["normalization_policy"]=r.normalization_policy
  frames.append(t)
 long=pd.concat(frames,ignore_index=True) if frames else pd.DataFrame(columns=["candidate_id","raw_value","feature_id","dimension","role","direction","normalization_policy"])
 long.to_csv(a.out_dir/"recommendation_registered_features_long.csv",index=False)
 dim=active.groupby(["dimension","role"],dropna=False).size().rename("registered_feature_count").reset_index()
 dim.to_csv(a.out_dir/"recommendation_dimension_registry_summary.csv",index=False)
 qa={"registered_features":int(len(active)),"missing_source_columns":int(len(missing_cols)),"candidate_count":int(len(features)),
     "dimensions_present":sorted(active["dimension"].unique().tolist()),
     "rule":"Only registry-declared comparison features may proceed to normalization/scenario scoring; coverage and explanation-only fields cannot silently become fit signals."}
 (a.out_dir/"recommendation_feature_registry_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__": main()
