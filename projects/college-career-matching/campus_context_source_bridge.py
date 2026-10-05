#!/usr/bin/env python3
"""Assemble governed campus-context source extracts at current UNITID grain.

Inputs are source-specific normalized extracts, not raw federal files. This
bridge keeps field provenance/vintage and never treats older-source UNITIDs
absent from the current directory universe as a fuzzy-match opportunity.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from campus_context_product_adapter import normalize

def clean(v):return str(v).strip() if v is not None else ""
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def index(rows,label):
 out={}
 for i,r in enumerate(rows,1):
  uid=clean(r.get("UNITID"))
  if not uid:raise ValueError(f"{label}: blank UNITID at row {i}")
  if uid in out:raise ValueError(f"{label}: duplicate UNITID {uid}")
  out[uid]=r
 return out
def put(target,field,row,source_id,vintage,source_field=None):
 source_field=source_field or field
 if row is None:return
 value=clean(row.get(source_field))
 state=clean(row.get(f"{source_field}__state"))
 if value=="" and state=="":return
 target[field]=value
 if state:target[f"{field}__state"]=state
 target[f"{field}__source_id"]=source_id
 target[f"{field}__source_vintage"]=vintage
def build(directory,cost=None,services=None,transit=None,walkability=None,
          directory_vintage="",cost_vintage="",services_vintage="",
          transit_vintage="",walkability_vintage=""):
 if not directory:raise ValueError("directory extract is empty")
 d=index(directory,"directory");sources={
  "cost":index(cost or [],"cost"),
  "services":index(services or [],"services"),
  "transit":index(transit or [],"transit"),
  "walkability":index(walkability or [],"walkability"),
 }
 current=set(d);orphans={name:sorted(set(rows)-current) for name,rows in sources.items()}
 canonical=[]
 for uid,row in d.items():
  x={"UNITID":uid}
  put(x,"locale_code",row,"ipeds_directory_2025",directory_vintage)
  c=sources["cost"].get(uid)
  put(x,"housing_available",c,"ipeds_cost_2024",cost_vintage)
  put(x,"housing_capacity",c,"ipeds_cost_2024",cost_vintage)
  put(x,"housing_required_all_ftft",c,"ipeds_cost_2024",cost_vintage)
  s=sources["services"].get(uid)
  put(x,"disability_services_registered_share",s,"ipeds_ic_2025",services_vintage)
  t=sources["transit"].get(uid)
  put(x,"transit_stop_distance_m",t,"bts_national_transit_map",transit_vintage)
  put(x,"transit_stop_count_800m",t,"bts_national_transit_map",transit_vintage)
  w=sources["walkability"].get(uid)
  put(x,"walkability_index",w,"epa_walkability_2021",walkability_vintage)
  if any(k!="UNITID" for k in x):canonical.append(x)
 rows=normalize(canonical)
 qa={
  "current_directory_institutions":len(d),
  "campus_context_records":len(rows),
  "source_match_counts":{name:sum(uid in source for uid in current) for name,source in sources.items()},
  "orphan_source_unitids":orphans,
  "source_vintages":{
   "ipeds_directory_2025":directory_vintage,
   "ipeds_cost_2024":cost_vintage,
   "ipeds_ic_2025":services_vintage,
   "bts_national_transit_map":transit_vintage,
   "epa_walkability_2021":walkability_vintage,
  },
  "rules":[
   "Current IPEDS directory UNITID defines the institution universe.",
   "Older-source orphan UNITIDs are reported in QA and are never fuzzy-matched.",
   "Each canonical field retains source_id and source_vintage.",
   "Transit and walkability remain distinct from disability-services evidence.",
   "Missing evidence remains unknown rather than false or zero."
  ]
 }
 return rows,qa
def write_csv(path,rows):
 if not rows:return
 cols=[]
 for r in rows:
  for k in r:
   if k not in cols:cols.append(k)
 with path.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--directory",type=Path,required=True);ap.add_argument("--cost",type=Path);ap.add_argument("--services",type=Path);ap.add_argument("--transit",type=Path);ap.add_argument("--walkability",type=Path)
 ap.add_argument("--directory-vintage",required=True);ap.add_argument("--cost-vintage",default="");ap.add_argument("--services-vintage",default="");ap.add_argument("--transit-vintage",default="");ap.add_argument("--walkability-vintage",default="")
 ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args()
 rows,qa=build(read(a.directory),read(a.cost) if a.cost else [],read(a.services) if a.services else [],read(a.transit) if a.transit else [],read(a.walkability) if a.walkability else [],a.directory_vintage,a.cost_vintage,a.services_vintage,a.transit_vintage,a.walkability_vintage)
 a.out_dir.mkdir(parents=True,exist_ok=True);write_csv(a.out_dir/"campus_context_enrichment.csv",rows);(a.out_dir/"campus_context_source_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
if __name__=="__main__":main()
