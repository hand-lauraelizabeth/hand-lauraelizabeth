#!/usr/bin/env python3
"""Attach composed recommendation dimensions to service-ready candidate rows.

No ranking or score is created. This bridge only materializes the dimension,
coverage, and evidence-state columns already understood by match_service_adapter.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

def clean(v):return str(v).strip() if v is not None else ""

def read(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def number_or_blank(v,label):
 x=clean(v)
 if x=="":return ""
 try:return float(x)
 except Exception as exc:raise ValueError(f"{label}: expected numeric or blank, got {v!r}") from exc

def build(candidates,dimensions):
 if not candidates:raise ValueError("candidate table is empty")
 seen=set();base={}
 for i,row in enumerate(candidates,1):
  cid=clean(row.get("candidate_id"))
  if not cid:raise ValueError(f"candidate row {i}: blank candidate_id")
  if cid in seen:raise ValueError(f"duplicate candidate_id: {cid}")
  seen.add(cid);base[cid]=dict(row)
 dseen=set();dimension_names=set()
 for i,row in enumerate(dimensions,1):
  cid=clean(row.get("candidate_id"));dim=clean(row.get("dimension"))
  if not cid or not dim:raise ValueError(f"dimension row {i}: blank candidate_id/dimension")
  if cid not in base:raise ValueError(f"orphan dimension candidate_id: {cid}")
  key=(cid,dim)
  if key in dseen:raise ValueError(f"duplicate candidate dimension: {key}")
  dseen.add(key);dimension_names.add(dim)
  value=number_or_blank(row.get("dimension_value"),f"{cid}/{dim} dimension_value")
  coverage=number_or_blank(row.get("dimension_coverage_rate"),f"{cid}/{dim} dimension_coverage_rate")
  if value!="" and not 0<=value<=1:raise ValueError(f"{cid}/{dim}: dimension_value outside [0,1]")
  if coverage!="" and not 0<=coverage<=1:raise ValueError(f"{cid}/{dim}: coverage outside [0,1]")
  base[cid][f"dimension__{dim}"]=value
  base[cid][f"coverage__{dim}"]=coverage
  base[cid][f"state__{dim}"]=clean(row.get("dimension_status") or row.get("dimension_evidence_state"))
 rows=[base[cid] for cid in sorted(base)]
 qa={
  "candidate_count":len(rows),
  "dimension_row_count":len(dimensions),
  "dimensions":sorted(dimension_names),
  "candidates_with_any_dimension":len({cid for cid,_ in dseen}),
  "rules":[
   "Candidate identity and row count are preserved.",
   "Dimension values and coverage remain separate service fields.",
   "No recommendation score, ordinal rank, or default preference weight is created.",
   "Orphan or duplicate dimension rows fail closed."
  ]
 }
 return rows,qa

def write_csv(path,rows):
 if not rows:return
 cols=[]
 for row in rows:
  for key in row:
   if key not in cols:cols.append(key)
 with Path(path).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--candidates",type=Path,required=True);ap.add_argument("--dimensions",type=Path,required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
 rows,qa=build(read(a.candidates),read(a.dimensions));write_csv(a.out_dir/"service_candidate_snapshot.csv",rows);(a.out_dir/"service_candidate_dimension_bridge_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__":main()
