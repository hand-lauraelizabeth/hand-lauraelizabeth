#!/usr/bin/env python3
"""Normalize campus-context preference evidence without hidden thresholds or weights.

Numeric transit/walkability features use an empirical percentile against an
explicit, versioned institution-level reference population. Housing and
disability-services evidence use exact categorical semantics. Missing evidence
remains missing and coverage never becomes desirability.
"""
from __future__ import annotations

import argparse,csv,hashlib,json
from pathlib import Path

POLICY_VERSION="campus_context_preference_normalization.v1"
NUMERIC_FEATURES=(
 {
  "feature_id":"campus_transit_nearest_stop_distance",
  "source_column":"campus__transit_stop_distance_m",
  "state_column":"campus__transit_stop_distance_m__state",
  "dimension":"transit_access_fit",
  "direction":"lower_better",
  "source_family":"bts_national_transit_map",
 },
 {
  "feature_id":"campus_walkability_index",
  "source_column":"campus__walkability_index",
  "state_column":"campus__walkability_index__state",
  "dimension":"walkability_fit",
  "direction":"higher_better",
  "source_family":"epa_walkability_2021",
 },
)
CATEGORICAL_FEATURES=(
 {
  "feature_id":"campus_housing_choice",
  "source_column":"campus__housing_choice_state",
  "dimension":"housing_context_fit",
  "target":"choice_available",
  "source_family":"campus_context_derived",
 },
 {
  "feature_id":"campus_disability_services_documented",
  "source_column":"campus__disability_services_evidence_available",
  "state_column":"campus__disability_services_registered_share__state",
  "dimension":"accessibility_evidence_fit",
  "target":"true",
  "source_family":"ipeds_ic_2025",
 },
)

def clean(v):return str(v).strip() if v is not None else ""

def read(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def number(v,label):
 try:return float(clean(v))
 except Exception as exc:raise ValueError(f"{label}: expected numeric observed value, got {v!r}") from exc

def unique(rows,keys,label):
 seen=set()
 for i,row in enumerate(rows,1):
  key=tuple(clean(row.get(k)) for k in keys)
  if not all(key):raise ValueError(f"{label}: blank identity at row {i}: {key}")
  if key in seen:raise ValueError(f"{label}: duplicate identity {key}")
  seen.add(key)

def observed_numeric_reference(rows,spec):
 vals=[]
 for row in rows:
  state=clean(row.get(spec["state_column"])).lower()
  value=clean(row.get(spec["source_column"]))
  if state=="observed":
   vals.append(number(value,spec["source_column"]))
  elif value and state not in {"missing","suppressed","unresolved","not_published","source_not_covered",""}:
   raise ValueError(f"{spec['source_column']}: unsupported evidence state {state!r}")
 return vals

def empirical_midrank(value,reference,direction):
 if not reference:raise ValueError("empirical percentile reference is empty")
 less=sum(x<value for x in reference);equal=sum(x==value for x in reference);n=len(reference)
 pct=(less+0.5*equal)/n
 return 1-pct if direction=="lower_better" else pct

def evidence_state(row,state_column,value_column):
 value=clean(row.get(value_column))
 if state_column:
  state=clean(row.get(state_column)).lower()
  if state=="observed":return "observed"
  if state:return state
 return "observed" if value else "missing"

def normalize(candidates,reference,reference_id):
 if not clean(reference_id):raise ValueError("reference_id must be nonblank")
 if not candidates:raise ValueError("candidate table is empty")
 if not reference:raise ValueError("reference population is empty")
 unique(candidates,["candidate_id"],"candidates")
 unique(reference,["UNITID"],"reference")
 ref={}
 for spec in NUMERIC_FEATURES:
  values=observed_numeric_reference(reference,spec)
  if len(values)<2:raise ValueError(f"{spec['feature_id']}: reference population needs at least 2 observed institutions")
  ref[spec["feature_id"]]=values
 rows=[]
 for candidate in candidates:
  cid=clean(candidate.get("candidate_id"))
  for spec in NUMERIC_FEATURES:
   state=evidence_state(candidate,spec["state_column"],spec["source_column"])
   raw=clean(candidate.get(spec["source_column"]))
   value=None
   if state=="observed":
    x=number(raw,spec["source_column"]);value=empirical_midrank(x,ref[spec["feature_id"]],spec["direction"])
   rows.append({
    "candidate_id":cid,"feature_id":spec["feature_id"],"dimension":spec["dimension"],
    "raw_value":raw,"normalized_value":value,"evidence_state":state,
    "transform":"empirical_midrank_reference","direction":spec["direction"],
    "reference_id":reference_id,"source_family":spec["source_family"],
   })
  for spec in CATEGORICAL_FEATURES:
   raw=clean(candidate.get(spec["source_column"]))
   state=evidence_state(candidate,spec.get("state_column"),spec["source_column"])
   if spec["feature_id"]=="campus_housing_choice" and raw.lower()=="unknown":state="missing"
   value=None if state!="observed" else (1.0 if raw.casefold()==spec["target"].casefold() else 0.0)
   rows.append({
    "candidate_id":cid,"feature_id":spec["feature_id"],"dimension":spec["dimension"],
    "raw_value":raw,"normalized_value":value,"evidence_state":state,
    "transform":"categorical_match","direction":"target_match",
    "reference_id":reference_id,"source_family":spec["source_family"],
   })
 qa={
  "policy_version":POLICY_VERSION,
  "reference_id":reference_id,
  "candidate_count":len(candidates),
  "reference_institution_count":len(reference),
  "feature_count":len(NUMERIC_FEATURES)+len(CATEGORICAL_FEATURES),
  "reference_observed_counts":{spec["feature_id"]:len(ref[spec["feature_id"]]) for spec in NUMERIC_FEATURES},
  "normalized_observed_counts":{fid:sum(r["feature_id"]==fid and r["evidence_state"]=="observed" for r in rows) for fid in [x["feature_id"] for x in NUMERIC_FEATURES+CATEGORICAL_FEATURES]},
  "rules":[
   "Reference population is institution-grain so institutions with more programs do not receive extra calibration weight.",
   "Numeric percentiles use the pinned reference population, never the displayed result set.",
   "Transit fit uses nearest-stop distance only; stop counts remain contextual until a separate service-quality policy is validated.",
   "Walkability is relative location-efficiency context and is not physical-accessibility evidence.",
   "Housing preference is an exact match to housing available without a universal FTFT residency requirement.",
   "Disability-services fit represents documented evidence availability only, not service quality or legal compliance.",
   "Missing evidence remains missing and never becomes a zero fit value.",
   "Each dimension has one comparison feature in v1, so no hidden within-dimension weighting is introduced."
  ]
 }
 policy=[{
  "feature_id":spec["feature_id"],"dimension":spec["dimension"],"within_dimension_weight":"1","partial_policy":"block"
 } for spec in NUMERIC_FEATURES+CATEGORICAL_FEATURES]
 return rows,policy,qa

def write_csv(path,rows):
 if not rows:return
 cols=[]
 for row in rows:
  for key in row:
   if key not in cols:cols.append(key)
 with Path(path).open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--candidates",type=Path,required=True)
 ap.add_argument("--reference",type=Path,required=True)
 ap.add_argument("--reference-id",required=True)
 ap.add_argument("--out-dir",type=Path,required=True)
 a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 rows,policy,qa=normalize(read(a.candidates),read(a.reference),a.reference_id)
 qa["candidate_sha256"]=sha256(a.candidates);qa["reference_sha256"]=sha256(a.reference)
 write_csv(a.out_dir/"campus_context_normalized_features.csv",rows)
 write_csv(a.out_dir/"campus_context_composition_policy.csv",policy)
 (a.out_dir/"campus_context_normalization_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__":main()
