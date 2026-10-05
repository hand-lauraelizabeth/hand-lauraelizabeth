#!/usr/bin/env python3
"""Normalize authoritative institution + program extracts into product-snapshot base grain.

Designed for current IPEDS-derived extracts or an equivalently governed upstream
institution/program build. It does not infer identities or CIP codes from names.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path

INST_REQUIRED={"UNITID","institution_name","state"}
PROG_REQUIRED={"UNITID","program_id","program_name","cip_code","credential_level"}
def read(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def clean(v):return str(v).strip() if v is not None else ""
def unique(rows,keys,label):
 seen={}
 for r in rows:
  k=tuple(clean(r.get(x)) for x in keys)
  if not all(k):raise ValueError(f"{label}: blank key {k}")
  if k in seen:raise ValueError(f"{label}: duplicate key {k}")
  seen[k]=r
 return seen
def build(inst,prog):
 if not inst or not prog:raise ValueError("institution and program extracts must be nonempty")
 mi=INST_REQUIRED-set(inst[0]);mp=PROG_REQUIRED-set(prog[0])
 if mi:raise ValueError(f"institution extract missing {sorted(mi)}")
 if mp:raise ValueError(f"program extract missing {sorted(mp)}")
 ii=unique(inst,["UNITID"],"institution");pi=unique(prog,["UNITID","program_id"],"program")
 out=[];unresolved=[]
 for (uid,pid),p in pi.items():
  i=ii.get((uid,))
  if not i:unresolved.append({"UNITID":uid,"program_id":pid,"reason":"program_unitid_not_in_institution_universe"});continue
  row={"UNITID":uid,"institution_name":clean(i["institution_name"]),"program_id":pid,"program_name":clean(p["program_name"]),"cip_code":clean(p["cip_code"]),"credential_level":clean(p["credential_level"]),"state":clean(i["state"]),"city":clean(i.get("city")),"cip_title":clean(p.get("cip_title")),"online_available":clean(p.get("online_available"))}
  if not row["institution_name"] or not row["program_name"] or not row["cip_code"] or not row["credential_level"] or not row["state"]:raise ValueError(f"required product field blank for {(uid,pid)}")
  out.append(row)
 out.sort(key=lambda r:(r["institution_name"].casefold(),r["program_name"].casefold(),r["UNITID"],r["program_id"]))
 return out,unresolved

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--institutions",type=Path,required=True);ap.add_argument("--programs",type=Path,required=True);ap.add_argument("--institution-vintage",required=True);ap.add_argument("--program-vintage",required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();rows,unresolved=build(read(a.institutions),read(a.programs));a.out_dir.mkdir(parents=True,exist_ok=True)
 cols=["UNITID","institution_name","program_id","program_name","cip_code","credential_level","state","city","cip_title","online_available"]
 with (a.out_dir/"current_college_backbone.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 (a.out_dir/"current_college_backbone_qa.json").write_text(json.dumps({"institution_vintage":a.institution_vintage,"program_vintage":a.program_vintage,"candidate_count":len(rows),"institution_count":len({r['UNITID'] for r in rows}),"unresolved_program_identity_count":len(unresolved),"unresolved_program_identities":unresolved},indent=2),encoding="utf-8")
if __name__=="__main__":main()
