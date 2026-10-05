#!/usr/bin/env python3
"""Build a versioned institution-level campus-context reference population.

The product snapshot is institution×program grain. Reference calibration must
weight institutions once, not once per program, so all repeated campus-context
values for a UNITID must agree before one institution row is emitted.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

REFERENCE_FIELDS=(
 "campus__transit_stop_distance_m",
 "campus__transit_stop_distance_m__state",
 "campus__transit_stop_distance_m__source_id",
 "campus__transit_stop_distance_m__source_vintage",
 "campus__walkability_index",
 "campus__walkability_index__state",
 "campus__walkability_index__source_id",
 "campus__walkability_index__source_vintage",
)

def clean(v):return str(v).strip() if v is not None else ""

def read(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def build(rows,data_version):
 if not clean(data_version):raise ValueError("data_version must be nonblank")
 if not rows:raise ValueError("product snapshot is empty")
 by_unit={}
 for i,row in enumerate(rows,1):
  uid=clean(row.get("UNITID"))
  if not uid:raise ValueError(f"snapshot row {i}: blank UNITID")
  values={field:clean(row.get(field)) for field in REFERENCE_FIELDS}
  if uid not in by_unit:by_unit[uid]=values
  else:
   diffs=[field for field in REFERENCE_FIELDS if by_unit[uid][field]!=values[field]]
   if diffs:raise ValueError(f"UNITID {uid}: inconsistent institution-level campus context across programs: {diffs}")
 out=[{"UNITID":uid,**by_unit[uid]} for uid in sorted(by_unit)]
 qa={
  "data_version":data_version,
  "snapshot_candidate_rows":len(rows),
  "reference_institution_rows":len(out),
  "transit_observed_institutions":sum(r["campus__transit_stop_distance_m__state"].lower()=="observed" for r in out),
  "walkability_observed_institutions":sum(r["campus__walkability_index__state"].lower()=="observed" for r in out),
  "rules":[
   "Each UNITID contributes at most one reference-population row.",
   "Institution-level campus context must be identical across every program row for the same UNITID.",
   "Missing evidence remains in the reference population with its state; only observed values enter percentile calibration.",
   "The reference population is pinned to the product snapshot data_version."
  ]
 }
 return out,qa

def write_csv(path,rows):
 if not rows:return
 cols=list(rows[0])
 with Path(path).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",type=Path,required=True);ap.add_argument("--data-version",required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args()
 rows,qa=build(read(a.snapshot),a.data_version);a.out_dir.mkdir(parents=True,exist_ok=True)
 ref=a.out_dir/"campus_context_reference_population.csv";write_csv(ref,rows)
 qa.update({"generated_at_utc":datetime.now(timezone.utc).isoformat(),"snapshot_sha256":sha256(a.snapshot),"reference_sha256":sha256(ref)})
 (a.out_dir/"campus_context_reference_manifest.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")

if __name__=="__main__":main()
