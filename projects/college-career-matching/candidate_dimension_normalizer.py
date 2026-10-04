#!/usr/bin/env python3
"""Build auditable normalized recommendation dimensions without scoring candidates.

The engine consumes a candidate table and a versioned feature manifest. It does
not invent direction, reference bounds, feature weights, missing-data rules, or
permission to renormalize partially observed dimensions.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

REQUIRED_MANIFEST=["feature","dimension","transform","direction","feature_weight","missing_policy","reference_id","reference_min","reference_max","partial_policy"]
VALID_TRANSFORMS={"identity_0_1","minmax_reference"}
VALID_DIRECTIONS={"higher_better","lower_better"}
VALID_PARTIAL={"block","renormalize_observed"}
MISSING_TOKENS={"","NA","N/A","NULL","NONE"}

def read(path): return pd.read_csv(path,dtype=str,keep_default_na=False)
def num(value,label):
 try:return float(str(value).strip())
 except Exception as exc: raise ValueError(f"{label} must be numeric: {value!r}") from exc
def is_missing(value): return str(value).strip().upper() in MISSING_TOKENS

def normalize_value(raw,row):
 if is_missing(raw): return None,(row["missing_policy"].strip().lower() or "unknown")
 x=num(raw,row["feature"]); transform=row["transform"].strip(); direction=row["direction"].strip()
 if transform not in VALID_TRANSFORMS: raise ValueError(f"unsupported transform {transform!r} for {row['feature']}")
 if direction not in VALID_DIRECTIONS: raise ValueError(f"unsupported direction {direction!r} for {row['feature']}")
 if transform=="identity_0_1":
  if not 0<=x<=1: raise ValueError(f"identity_0_1 value outside [0,1] for {row['feature']}: {x}")
  z=x
 else:
  lo=num(row["reference_min"],f"reference_min {row['feature']}"); hi=num(row["reference_max"],f"reference_max {row['feature']}")
  if hi<=lo: raise ValueError(f"invalid reference range for {row['feature']}: {lo}, {hi}")
  z=(min(max(x,lo),hi)-lo)/(hi-lo)
 if direction=="lower_better": z=1-z
 return z,"observed"

def build(candidates,manifest,candidate_id):
 if candidate_id not in candidates: raise ValueError(f"candidate table missing {candidate_id}")
 if candidates[candidate_id].duplicated().any(): raise ValueError("candidate IDs are not unique at declared grain")
 missing=[c for c in REQUIRED_MANIFEST if c not in manifest]
 if missing: raise ValueError(f"feature manifest missing columns: {missing}")
 if manifest["feature"].duplicated().any(): raise ValueError("feature manifest contains duplicate feature rows")
 bad=set(manifest["partial_policy"].str.strip())-VALID_PARTIAL
 if bad: raise ValueError(f"unsupported partial policies: {sorted(bad)}")
 if (manifest.groupby("dimension")["partial_policy"].nunique()>1).any(): raise ValueError("partial_policy must be consistent within each dimension")
 detail_rows=[]
 for _,m in manifest.iterrows():
  feature=m["feature"].strip(); weight=num(m["feature_weight"],f"feature_weight {feature}")
  if weight<0: raise ValueError(f"negative feature weight for {feature}")
  if feature not in candidates:
   for cid in candidates[candidate_id]: detail_rows.append({candidate_id:cid,"feature":feature,"dimension":m["dimension"],"raw_value":"","normalized_value":None,"evidence_state":"field_absent_from_candidate_schema","feature_weight":weight,"reference_id":m["reference_id"],"partial_policy":m["partial_policy"]})
   continue
  for cid,raw in zip(candidates[candidate_id],candidates[feature]):
   z,state=normalize_value(raw,m); detail_rows.append({candidate_id:cid,"feature":feature,"dimension":m["dimension"],"raw_value":raw,"normalized_value":z,"evidence_state":state,"feature_weight":weight,"reference_id":m["reference_id"],"partial_policy":m["partial_policy"]})
 detail=pd.DataFrame(detail_rows); rows=[]
 for (cid,dimension),g in detail.groupby([candidate_id,"dimension"],sort=False):
  expected_n=len(g); obs=g[g["evidence_state"].eq("observed")].copy(); observed_n=len(obs); coverage=observed_n/expected_n if expected_n else 0.0; policy=g["partial_policy"].iloc[0]
  expected_weight=float(pd.to_numeric(g["feature_weight"],errors="raise").sum()); observed_weight=float(pd.to_numeric(obs["feature_weight"],errors="raise").sum()) if observed_n else 0.0
  complete=observed_n==expected_n
  if expected_weight<=0: value=None; state="invalid_zero_expected_weight"
  elif complete:
   value=float((pd.to_numeric(obs["normalized_value"])*pd.to_numeric(obs["feature_weight"])).sum()/observed_weight) if observed_weight>0 else None; state="complete"
  elif policy=="renormalize_observed" and observed_weight>0:
   value=float((pd.to_numeric(obs["normalized_value"])*pd.to_numeric(obs["feature_weight"])).sum()/observed_weight); state="partial_renormalized"
  elif observed_n: value=None; state="partial_blocked"
  else: value=None; state="insufficient"
  rows.append({candidate_id:cid,"dimension":dimension,"dimension_value":value,"observed_feature_count":observed_n,"expected_feature_count":expected_n,"dimension_coverage_rate":coverage,"dimension_evidence_state":state,"expected_feature_weight":expected_weight,"observed_feature_weight":observed_weight,"partial_policy":policy})
 dimensions=pd.DataFrame(rows); values=dimensions.pivot(index=candidate_id,columns="dimension",values="dimension_value").reset_index(); cov=dimensions.pivot(index=candidate_id,columns="dimension",values="dimension_coverage_rate"); cov.columns=[f"{c}__coverage" for c in cov.columns]; model=values.merge(cov.reset_index(),on=candidate_id,how="left")
 summary={"candidate_count":int(candidates[candidate_id].nunique()),"feature_count":int(manifest["feature"].nunique()),"dimension_count":int(manifest["dimension"].nunique()),"fully_observed_dimension_rows":int(dimensions["dimension_evidence_state"].eq("complete").sum()),"partial_renormalized_dimension_rows":int(dimensions["dimension_evidence_state"].eq("partial_renormalized").sum()),"partial_blocked_dimension_rows":int(dimensions["dimension_evidence_state"].eq("partial_blocked").sum()),"insufficient_dimension_rows":int(dimensions["dimension_evidence_state"].eq("insufficient").sum()),"note":"Partial dimensions receive a value only when the manifest explicitly permits renormalize_observed. Coverage remains evidence metadata, not desirability."}
 return detail,dimensions,model,summary

def main():
 p=argparse.ArgumentParser(); p.add_argument("--candidates",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); p.add_argument("--candidate-id",default="candidate_id"); p.add_argument("--out-dir",type=Path,required=True); a=p.parse_args(); a.out_dir.mkdir(parents=True,exist_ok=True)
 detail,dimensions,model,summary=build(read(a.candidates),read(a.manifest),a.candidate_id); detail.to_csv(a.out_dir/"candidate_normalized_feature_detail.csv",index=False); dimensions.to_csv(a.out_dir/"candidate_dimensions_long.csv",index=False); model.to_csv(a.out_dir/"candidate_dimension_model_table.csv",index=False); (a.out_dir/"candidate_dimension_normalization_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
if __name__=="__main__": main()
