#!/usr/bin/env python3
"""Normalize reviewed O*NET 31.0 Work Activity Importance rows for career-preference alignment."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
from onet_career_attribute_registry import load_registry

MISSING={"","NA","N/A","NULL","NONE"}
def clean(v):return str(v).strip() if v is not None else ""
def key(row,*names):
 for n in names:
  if n in row:return row[n]
 return None
def base_soc(code):
 c=clean(code)
 if not c.endswith(".00"):return None
 base=c[:-3]
 return base if len(base)==7 and base[2]=="-" else None
def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def normalize(rows,registry=None):
 reg=registry or load_registry();src=reg["source"];wanted={a["element_id"]:a for a in reg["attributes"]};out=[];seen=set()
 for r in rows:
  soc=base_soc(key(r,"onetsoc_code","O*NET-SOC Code","ONET_SOC_CODE"))
  if not soc:continue
  element=clean(key(r,"element_id","Element ID"));scale=clean(key(r,"scale_id","Scale ID"))
  if element not in wanted or scale!=src["scale_id"]:continue
  spec=wanted[element];raw=clean(key(r,"data_value","Data Value"))
  suppress=clean(key(r,"recommend_suppress","Recommend Suppress")).upper()=="Y";not_rel=clean(key(r,"not_relevant","Not Relevant")).upper()=="Y"
  state="suppressed" if suppress else ("not_relevant" if not_rel else ("missing" if raw.upper() in MISSING else "observed"))
  value=""
  if state=="observed":
   try:value=float(raw)
   except ValueError:raise ValueError(f"non-numeric O*NET value for {soc} {element}")
   if not (spec["scale_min"]<=value<=spec["scale_max"]):raise ValueError(f"O*NET value outside governed scale for {soc} {element}: {value}")
  k=(soc,spec["attribute_id"])
  if k in seen:raise ValueError(f"duplicate base-SOC career attribute: {k}")
  seen.add(k)
  out.append({"occ_code":soc,"attribute_id":spec["attribute_id"],"attribute_value":value,"evidence_state":state,"onet_soc_code":soc+".00","element_id":element,"element_name":spec["element_name"],"scale_id":scale,"scale_name":clean(key(r,"scale_name","Scale Name")) or "Importance","scale_min":spec["scale_min"],"scale_max":spec["scale_max"],"source_release":"31.0","source_vintage":clean(key(r,"date_updated","Date","Date Updated")) or None,"domain_source":clean(key(r,"domain_source","Domain Source")) or None})
 return sorted(out,key=lambda x:(x["occ_code"],x["attribute_id"]))
def main():
 p=argparse.ArgumentParser();p.add_argument("--work-activities",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--qa",type=Path);a=p.parse_args()
 rows=normalize(read_csv(a.work_activities));a.output.parent.mkdir(parents=True,exist_ok=True)
 fields=list(rows[0]) if rows else ["occ_code","attribute_id","attribute_value","evidence_state","onet_soc_code","element_id","element_name","scale_id","scale_name","scale_min","scale_max","source_release","source_vintage","domain_source"]
 with a.output.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 if a.qa:
  reg=load_registry();observed=sum(x["evidence_state"]=="observed" for x in rows);a.qa.parent.mkdir(parents=True,exist_ok=True);a.qa.write_text(json.dumps({"source_release":"31.0","source_domain":"work_activities","base_soc_policy":"only .00 O*NET-SOC rows; no specialty averaging","approved_attribute_count":len(reg["attributes"]),"normalized_rows":len(rows),"observed_rows":observed,"unique_base_socs":len({x["occ_code"] for x in rows}),"semantic_rule":"Only reviewed Work Activity Importance mappings are emitted; missing/suppressed/not-relevant values remain nonnumeric evidence states."},indent=2),encoding="utf-8")
if __name__=="__main__":main()
