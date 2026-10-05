#!/usr/bin/env python3
"""Materialize an explicit-priority baseline ranking without imputing evidence.

Consumes composed candidate dimensions plus the baseline scenario produced from
explicit user priorities. A candidate is rankable only when every baseline
weighted dimension has a usable value. Missing/unresolved dimensions never
become zero and never get weight renormalized away at the candidate level.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

USABLE_STATUSES={"complete","partial_renormalized"}

def clean(v):return str(v).strip() if v is not None else ""

def read(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def numeric(v,label):
 try:
  x=float(clean(v))
 except Exception as exc:
  raise ValueError(f"{label}: expected numeric value, got {v!r}") from exc
 if not math.isfinite(x):raise ValueError(f"{label}: value must be finite")
 return x

def build(dimensions,weights):
 if not dimensions:raise ValueError("dimension table is empty")
 baseline=[r for r in weights if clean(r.get("scenario_id"))=="baseline"]
 if not baseline:
  candidate_ids=sorted({clean(r.get("candidate_id")) for r in dimensions if clean(r.get("candidate_id"))})
  rows=[{"candidate_id":cid,"ranking_status":"unranked_no_explicit_priorities","baseline_score":"","rank":"","missing_weighted_dimensions":"","partial_weighted_dimensions":"","weighted_dimension_count":0} for cid in candidate_ids]
  return rows,[],rows,[],{"status":"NO_EXPLICIT_PRIORITIES","candidate_count":len(candidate_ids),"ranked_candidate_count":0,"unranked_candidate_count":len(candidate_ids),"weighted_dimension_count":0,"baseline_weight_sum":0.0,"rules":["No baseline scenario means no explicit dimension priorities; no rank is manufactured."]}
 dims=[clean(r.get("dimension")) for r in baseline]
 if not all(dims) or len(dims)!=len(set(dims)):raise ValueError("baseline scenario contains blank or duplicate dimensions")
 parsed={}
 for r in baseline:
  w=numeric(r.get("weight"),f"baseline weight {r.get('dimension')}")
  if w<0:raise ValueError("baseline weights cannot be negative")
  parsed[clean(r["dimension"])]=w
 total=sum(parsed.values())
 if total<=0:raise ValueError("baseline weights must sum to a positive value")
 parsed={d:w/total for d,w in parsed.items()}
 by_candidate={}
 seen=set()
 for i,row in enumerate(dimensions,1):
  cid=clean(row.get("candidate_id"));dim=clean(row.get("dimension"))
  if not cid or not dim:raise ValueError(f"dimension row {i}: blank candidate_id/dimension")
  key=(cid,dim)
  if key in seen:raise ValueError(f"duplicate candidate dimension: {key}")
  seen.add(key);by_candidate.setdefault(cid,{})[dim]=row
 output=[];rankable=[]
 for cid in sorted(by_candidate):
  missing=[];partial=[];values={}
  for dim in parsed:
   r=by_candidate[cid].get(dim)
   if r is None:
    missing.append(dim);continue
   status=clean(r.get("dimension_status") or r.get("dimension_evidence_state"))
   raw=clean(r.get("dimension_value"))
   if status not in USABLE_STATUSES or raw=="":
    missing.append(dim);continue
   value=numeric(raw,f"{cid}/{dim}")
   if not 0<=value<=1:raise ValueError(f"{cid}/{dim}: dimension_value outside [0,1]")
   values[dim]=value
   if status=="partial_renormalized":partial.append(dim)
  if missing:
   output.append({"candidate_id":cid,"ranking_status":"unranked_unresolved_weighted_dimension","baseline_score":"","rank":"","missing_weighted_dimensions":"|".join(sorted(missing)),"partial_weighted_dimensions":"|".join(sorted(partial)),"weighted_dimension_count":len(parsed)})
  else:
   score=sum(values[d]*parsed[d] for d in parsed)
   row={"candidate_id":cid,"ranking_status":"ranked_pending_validation","baseline_score":score,"rank":"","missing_weighted_dimensions":"","partial_weighted_dimensions":"|".join(sorted(partial)),"weighted_dimension_count":len(parsed)}
   output.append(row);rankable.append(row)
 rankable.sort(key=lambda r:(-r["baseline_score"],r["candidate_id"]))
 last_score=None;rank=0
 for i,row in enumerate(rankable,1):
  if last_score is None or row["baseline_score"]!=last_score:rank=i;last_score=row["baseline_score"]
  row["rank"]=rank
 byid={r["candidate_id"]:r for r in rankable}
 for row in output:
  if row["candidate_id"] in byid:row["rank"]=byid[row["candidate_id"]]["rank"]
 unranked=[r for r in output if r["ranking_status"]!="ranked_pending_validation"]
 sensitivity=[]
 for cid in [r["candidate_id"] for r in rankable]:
  wide={"candidate_id":cid}
  for dim in parsed:
   wide[dim]=numeric(by_candidate[cid][dim]["dimension_value"],f"{cid}/{dim}")
  sensitivity.append(wide)
 summary={
  "status":"RANKING_READY_FOR_VALIDATION" if rankable else "NO_RANKABLE_CANDIDATES",
  "candidate_count":len(output),
  "ranked_candidate_count":len(rankable),
  "unranked_candidate_count":len(unranked),
  "weighted_dimension_count":len(parsed),
  "baseline_weight_sum":sum(parsed.values()),
  "weighted_dimensions":sorted(parsed),
  "partial_evidence_ranked_candidate_count":sum(bool(r["partial_weighted_dimensions"]) for r in rankable),
  "rules":[
   "Only the explicit baseline preference scenario is used.",
   "Weights are normalized globally across explicit baseline dimensions, never separately by candidate.",
   "A missing/unresolved weighted dimension leaves the candidate unranked; missing dimensions are not converted to zero or dropped from the denominator.",
   "Partial-renormalized dimensions are usable only because their within-dimension policy explicitly allowed it and remain flagged.",
   "Exact score ties share a rank; candidate_id is used only for deterministic row ordering.",
   "ranked_pending_validation is not review eligibility or production authorization."
  ]
 }
 return output,rankable,unranked,sensitivity,summary

def write_csv(path,rows,columns=None):
 if columns is None:
  columns=[]
  for row in rows:
   for key in row:
    if key not in columns:columns.append(key)
 if not columns:return
 with Path(path).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--dimensions",type=Path,required=True);ap.add_argument("--weights",type=Path,required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 rows,ranked,unranked,sensitivity,summary=build(read(a.dimensions),read(a.weights))
 cols=["candidate_id","ranking_status","baseline_score","rank","missing_weighted_dimensions","partial_weighted_dimensions","weighted_dimension_count"]
 write_csv(a.out_dir/"recommendation_baseline_all_candidates.csv",rows,cols)
 write_csv(a.out_dir/"recommendation_baseline_ranked.csv",ranked,cols)
 write_csv(a.out_dir/"recommendation_baseline_unranked.csv",unranked,cols)
 write_csv(a.out_dir/"recommendation_sensitivity_candidate_dimensions.csv",sensitivity)
 (a.out_dir/"recommendation_baseline_summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")

if __name__=="__main__":main()
