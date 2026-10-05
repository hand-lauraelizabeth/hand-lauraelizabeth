#!/usr/bin/env python3
"""Build versioned interface choices from an approved institution×program snapshot.

The frontend should consume this artifact (or a service wrapping it) instead of
maintaining independent, stale dropdown taxonomies.
"""
from __future__ import annotations
import argparse,csv,json
from datetime import datetime,timezone
from pathlib import Path

def clean(v):return str(v).strip() if v is not None else ""
def truth(v):return clean(v).lower() in {"1","true","yes","y"}
def unique(rows,key,label=None):
 seen={}
 for r in rows:
  k=clean(r.get(key));lab=clean(r.get(label or key))
  if k and lab:seen[k]=lab
 return [{"value":k,"label":seen[k]} for k in sorted(seen,key=lambda x:(seen[x].casefold(),x))]
def build(rows,data_version):
 required={"UNITID","institution_name","program_id","program_name","cip_code","credential_level","state"}
 if not rows:raise ValueError("snapshot is empty")
 missing=required-set(rows[0])
 if missing:raise ValueError(f"snapshot missing columns: {sorted(missing)}")
 ids=set()
 for r in rows:
  cid=(clean(r["UNITID"]),clean(r["program_id"]))
  if not all(cid):raise ValueError("blank UNITID/program_id")
  if cid in ids:raise ValueError(f"duplicate institution-program identity: {cid}")
  ids.add(cid)
 institutions={}
 for r in rows:
  uid=clean(r["UNITID"]);institutions[uid]={"value":uid,"label":clean(r["institution_name"]),"state":clean(r.get("state")) or None,"city":clean(r.get("city")) or None}
 programs=[{"value":f"{clean(r['UNITID'])}:{clean(r['program_id'])}","label":clean(r["program_name"]),"unitid":clean(r["UNITID"]),"program_id":clean(r["program_id"]),"cip_code":clean(r["cip_code"]),"credential_level":clean(r["credential_level"])} for r in rows]
 programs.sort(key=lambda x:(x["label"].casefold(),x["unitid"],x["program_id"]))
 states=sorted({clean(r["state"]) for r in rows if clean(r["state"])})
 campus_settings=unique(rows,"campus__locale_category") if "campus__locale_category" in rows[0] else []
 housing=[]
 if "campus__housing_available" in rows[0]:
  housing.append({"value":"available","label":"Institutionally controlled housing available","available":any(truth(r.get("campus__housing_available")) for r in rows)})
 if "campus__housing_required_all_ftft" in rows[0]:
  housing.append({"value":"choice","label":"Housing available without universal FTFT residency requirement","available":any(truth(r.get("campus__housing_available")) and not truth(r.get("campus__housing_required_all_ftft")) for r in rows)})
  housing.append({"value":"required","label":"Universal FTFT residency requirement reported","available":any(truth(r.get("campus__housing_required_all_ftft")) for r in rows)})
 affordability={"income_bands":[{"value":"overall","label":"Overall average"},{"value":"0_30","label":"$0–30,000"},{"value":"30_48","label":"$30,001–48,000"},{"value":"48_75","label":"$48,001–75,000"},{"value":"75_110","label":"$75,001–110,000"},{"value":"110_plus","label":"$110,001+"}],"semantics":"Average net price after grants/scholarships; not a personalized estimate."}
 modalities=[]
 if "online_available" in rows[0]:
  vals={"online_available":any(truth(r.get("online_available")) for r in rows),"online_evidence_present":any(clean(r.get("online_available")) for r in rows)}
  if vals["online_evidence_present"]:modalities.append({"value":"online_available","label":"Online availability reported","available":vals["online_available"]})
 cips={}
 for r in rows:
  code=clean(r["cip_code"]);title=clean(r.get("cip_title")) or code
  if code:cips[code]=title
 return {"schema_version":"1.1","data_version":data_version,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"counts":{"institutions":len(institutions),"institution_programs":len(programs),"states":len(states),"cip_codes":len(cips)},"states":[{"value":x,"label":x} for x in states],"campus_settings":campus_settings,"housing":housing,"affordability":affordability,"credential_levels":unique(rows,"credential_level"),"institutions":sorted(institutions.values(),key=lambda x:(x["label"].casefold(),x["value"])),"programs":programs,"cip_fields":[{"value":k,"label":cips[k]} for k in sorted(cips,key=lambda x:(cips[x].casefold(),x))],"modalities":modalities}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",type=Path,required=True);ap.add_argument("--data-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 with a.snapshot.open(newline="",encoding="utf-8-sig") as f:rows=list(csv.DictReader(f))
 out=build(rows,a.data_version);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
