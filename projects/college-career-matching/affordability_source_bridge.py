#!/usr/bin/env python3
"""Assemble institution affordability/aid evidence at current UNITID grain.

Inputs are source-specific normalized extracts. Direct IPEDS Cost is preferred
for cost/net-price concepts; College Scorecard may fill a missing canonical
cost/net-price field, with provenance preserved. IPEDS SFA owns aid-type
participation/amount evidence. Older-source orphan UNITIDs are reported, never
fuzzy-matched.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from affordability_outcomes_product_adapter import normalize

COST_FIELDS=(
 "tuition_in_state","tuition_out_of_state","cost_of_attendance",
 "net_price_overall","net_price_income_0_30","net_price_income_30_48",
 "net_price_income_48_75","net_price_income_75_110","net_price_income_110_plus",
)
AID_FIELDS=("institutional_grant_share","work_study_share","state_local_grant_share")

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
def put(target,field,row,source_id,vintage):
 if row is None:return False
 value=clean(row.get(field));state=clean(row.get(f"{field}__state"))
 if value=="" and state=="":return False
 target[field]=value
 if state:target[f"{field}__state"]=state
 target[f"{field}__source_id"]=source_id
 target[f"{field}__source_vintage"]=vintage
 return True
def build(directory,cost=None,aid=None,scorecard=None,
          directory_vintage="",cost_vintage="",aid_vintage="",scorecard_vintage=""):
 if not directory:raise ValueError("directory extract is empty")
 d=index(directory,"directory");sources={
  "cost":index(cost or [],"cost"),
  "aid":index(aid or [],"aid"),
  "scorecard":index(scorecard or [],"scorecard"),
 }
 current=set(d);orphans={name:sorted(set(rows)-current) for name,rows in sources.items()}
 canonical=[];fallback_counts={field:0 for field in COST_FIELDS}
 for uid in d:
  x={"UNITID":uid}
  c=sources["cost"].get(uid);s=sources["scorecard"].get(uid);a=sources["aid"].get(uid)
  for field in COST_FIELDS:
   used=put(x,field,c,"ipeds_cost_2024",cost_vintage)
   if not used and put(x,field,s,"college_scorecard",scorecard_vintage):fallback_counts[field]+=1
  # Compatibility alias for older service requests; exact provenance follows overall ANP.
  if clean(x.get("net_price_overall"))!="":
   x["net_price"]=x["net_price_overall"]
   x["net_price__state"]=x.get("net_price_overall__state","observed")
   x["net_price__source_id"]=x.get("net_price_overall__source_id","")
   x["net_price__source_vintage"]=x.get("net_price_overall__source_vintage","")
  for field in AID_FIELDS:put(x,field,a,"ipeds_sfa_2023_24",aid_vintage)
  if any(k!="UNITID" for k in x):canonical.append(x)
 rows=normalize(canonical,"institution")
 qa={
  "current_directory_institutions":len(d),
  "affordability_records":len(rows),
  "source_match_counts":{name:sum(uid in source for uid in current) for name,source in sources.items()},
  "scorecard_fallback_counts":fallback_counts,
  "orphan_source_unitids":orphans,
  "source_vintages":{
   "directory":directory_vintage,
   "ipeds_cost_2024":cost_vintage,
   "ipeds_sfa_2023_24":aid_vintage,
   "college_scorecard":scorecard_vintage,
  },
  "rules":[
   "Current directory UNITID defines the institution universe.",
   "IPEDS Cost has precedence for cost and net-price concepts.",
   "College Scorecard may fill missing canonical cost/net-price fields only with its provenance retained.",
   "IPEDS SFA owns aid-type evidence in this bridge.",
   "Income-band net prices are institutional averages, not personalized estimates.",
   "Household size is not inferred.",
   "Older-source orphan UNITIDs are reported and never fuzzy-matched.",
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
 ap=argparse.ArgumentParser();ap.add_argument("--directory",type=Path,required=True);ap.add_argument("--cost",type=Path);ap.add_argument("--aid",type=Path);ap.add_argument("--scorecard",type=Path)
 ap.add_argument("--directory-vintage",required=True);ap.add_argument("--cost-vintage",default="");ap.add_argument("--aid-vintage",default="");ap.add_argument("--scorecard-vintage",default="");ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args()
 rows,qa=build(read(a.directory),read(a.cost) if a.cost else [],read(a.aid) if a.aid else [],read(a.scorecard) if a.scorecard else [],a.directory_vintage,a.cost_vintage,a.aid_vintage,a.scorecard_vintage)
 a.out_dir.mkdir(parents=True,exist_ok=True);write_csv(a.out_dir/"institution_affordability_outcomes.csv",rows);(a.out_dir/"affordability_source_qa.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
if __name__=="__main__":main()
