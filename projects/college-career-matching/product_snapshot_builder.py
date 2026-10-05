#!/usr/bin/env python3
"""Assemble a versioned institution×program snapshot for matching and UI options.

Base identity is authoritative institution/program data. Optional enrichment files
are left-joined without changing the candidate universe. Institution- and program-
grain evidence remain separately namespaced; missing evidence is coverage, not zero.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
BASE_REQUIRED={"UNITID","institution_name","program_id","program_name","cip_code","credential_level","state"}
def read_csv(p):
 with Path(p).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def clean(v):return str(v).strip() if v is not None else ""
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def index(rows,keys,label):
 out={}
 for r in rows:
  k=tuple(clean(r.get(x)) for x in keys)
  if not all(k):raise ValueError(f"{label}: blank join key {k}")
  if k in out:raise ValueError(f"{label}: duplicate join key {k}")
  out[k]=r
 return out
def prefixed_merge(base,enrichment,prefix,skip):
 out=dict(base)
 for k,v in enrichment.items():
  if k not in skip:out[f"{prefix}__{k}"]=v
 return out
def build(base,accreditation=None,finance=None,program_outcomes=None,transfer=None,career=None):
 if not base:raise ValueError("base snapshot is empty")
 miss=BASE_REQUIRED-set(base[0])
 if miss:raise ValueError(f"base missing columns: {sorted(miss)}")
 baseidx=index(base,["UNITID","program_id"],"base");acc=index(accreditation or [],["UNITID"],"accreditation");fin=index(finance or [],["UNITID"],"finance");po=index(program_outcomes or [],["UNITID","program_id"],"program outcomes");tr=index(transfer or [],["UNITID","program_id"],"transfer");car=index(career or [],["UNITID","program_id"],"career")
 rows=[]
 for key,b in baseidx.items():
  uid,pid=key;r=dict(b);r["candidate_id"]=f"{uid}:{pid}"
  coverage={"accreditation":(uid,) in acc,"finance_outcomes":(uid,) in fin,"program_outcomes":key in po,"transfer":key in tr,"career_pathways":key in car}
  if (uid,) in acc:r=prefixed_merge(r,acc[(uid,)],"accreditation",{"UNITID"})
  if (uid,) in fin:r=prefixed_merge(r,fin[(uid,)],"finance",{"UNITID"})
  if key in po:r=prefixed_merge(r,po[key],"program_outcomes",{"UNITID","program_id"})
  if key in tr:r=prefixed_merge(r,tr[key],"transfer",{"UNITID","program_id"})
  if key in car:r=prefixed_merge(r,car[key],"career",{"UNITID","program_id"})
  for k,v in coverage.items():r[f"coverage__{k}"]="1" if v else "0"
  rows.append(r)
 rows.sort(key=lambda r:(clean(r["institution_name"]).casefold(),clean(r["program_name"]).casefold(),r["candidate_id"]));return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--base",type=Path,required=True);ap.add_argument("--accreditation",type=Path);ap.add_argument("--finance",type=Path);ap.add_argument("--program-outcomes",type=Path);ap.add_argument("--transfer",type=Path);ap.add_argument("--career",type=Path);ap.add_argument("--data-version",required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args()
 inputs={"base":a.base,"accreditation":a.accreditation,"finance":a.finance,"program_outcomes":a.program_outcomes,"transfer":a.transfer,"career":a.career};loaded={k:(read_csv(v) if v else []) for k,v in inputs.items()};rows=build(loaded["base"],loaded["accreditation"],loaded["finance"],loaded["program_outcomes"],loaded["transfer"],loaded["career"]);a.out_dir.mkdir(parents=True,exist_ok=True)
 cols=[]
 for r in rows:
  for k in r:
   if k not in cols:cols.append(k)
 with (a.out_dir/"institution_program_product_snapshot.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 families=["accreditation","finance_outcomes","program_outcomes","transfer","career_pathways"]
 manifest={"schema_version":"1.1","data_version":a.data_version,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_grain":"UNITID x program_id","candidate_count":len(rows),"institution_count":len({r['UNITID'] for r in rows}),"input_sha256":{k:sha(v) for k,v in inputs.items() if v},"coverage":{x:sum(r[f'coverage__{x}']=='1' for r in rows) for x in families},"rule":"Missing optional enrichment is coverage state, not negative evidence. Institution and program grains remain separately namespaced."}
 (a.out_dir/"institution_program_product_snapshot_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
if __name__=="__main__":main()
