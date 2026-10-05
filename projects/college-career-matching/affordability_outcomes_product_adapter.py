#!/usr/bin/env python3
"""Normalize affordability/outcomes evidence without collapsing source grains."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from measure_metadata_registry import load_registry,evidence_state
INST_REQUIRED={"UNITID"};FIELD_REQUIRED={"UNITID","cip_code","credential_level"}
INST_MEASURES=("tuition_in_state","tuition_out_of_state","cost_of_attendance","net_price","median_debt","completion_rate");FIELD_MEASURES=("median_earnings","median_debt","completion_rate")
def clean(v):return str(v).strip() if v is not None else ""
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def unique(rows,keys,label):
 out={}
 for r in rows:
  k=tuple(clean(r.get(x)) for x in keys)
  if not all(k):raise ValueError(f"{label}: blank key {k}")
  if k in out:raise ValueError(f"{label}: duplicate key {k}")
  out[k]=r
 return out
def normalize(rows,grain):
 if not rows:return []
 required=INST_REQUIRED if grain=="institution" else FIELD_REQUIRED
 for i,r in enumerate(rows):
  miss=required-set(r)
  if miss:raise ValueError(f"{grain} extract row {i} missing {sorted(miss)}")
 measures=INST_MEASURES if grain=="institution" else FIELD_MEASURES;keys=["UNITID"] if grain=="institution" else ["UNITID","cip_code","credential_level"];unique(rows,keys,grain);registry=load_registry();out=[]
 for r in rows:
  x={k:clean(r.get(k)) for k in keys};x["evidence_grain"]=grain
  for m in measures:
   x[m]=clean(r.get(m));x[f"{m}__state"]=evidence_state(m,r,registry)
  x["source_vintage"]=clean(r.get("source_vintage"));x["source_record_id"]=clean(r.get("source_record_id"));out.append(x)
 return out
def attach_field_to_programs(programs,field_rows):
 idx=unique(field_rows,["UNITID","cip_code","credential_level"],"field outcomes") if field_rows else {};out=[]
 for p in programs:
  key=(clean(p.get("UNITID")),clean(p.get("cip_code")),clean(p.get("credential_level")));pid=clean(p.get("program_id"))
  if not pid:raise ValueError("program outcomes attachment requires nonblank program_id")
  r={"UNITID":key[0],"program_id":pid};hit=idx.get(key);r["field_outcomes_coverage"]="observed" if hit else "unknown"
  if hit:
   for k,v in hit.items():
    if k not in {"UNITID","cip_code","credential_level"}:r[k]=v
  out.append(r)
 return out
def write_csv(path,rows):
 if not rows:return
 cols=[]
 for r in rows:
  for k in r:
   if k not in cols:cols.append(k)
 with path.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--institution",type=Path);ap.add_argument("--field",type=Path);ap.add_argument("--programs",type=Path);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True);inst=normalize(read(a.institution),"institution") if a.institution else [];field=normalize(read(a.field),"field_of_study") if a.field else [];write_csv(a.out_dir/"institution_affordability_outcomes.csv",inst);write_csv(a.out_dir/"field_of_study_outcomes.csv",field);attached=attach_field_to_programs(read(a.programs),field) if a.programs and field else [];write_csv(a.out_dir/"program_field_outcomes_enrichment.csv",attached);qa={"institution_records":len(inst),"field_of_study_records":len(field),"program_field_rows":len(attached),"program_field_observed":sum(r.get("field_outcomes_coverage")=="observed" for r in attached),"semantic_rules":["Institution outcomes are not program outcomes.","Distinct affordability/outcome measures remain distinct.","Source-supplied suppressed/missing/unresolved/not-published states are preserved.","Blank without source state is missing, never inferred suppressed.","Field outcomes attach only by exact governed UNITID+CIP+credential identity."]};(a.out_dir/"affordability_outcomes_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
if __name__=="__main__":main()
