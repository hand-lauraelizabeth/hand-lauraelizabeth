#!/usr/bin/env python3
"""Assemble a governed versioned institution×program product snapshot."""
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from product_enrichment_registry import load_registry,validate_all
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
  if k not in skip:out[f"{prefix}{k}"]=v
 return out
def build(base,accreditation=None,finance=None,program_outcomes=None,transfer=None,career=None,registry=None):
 if not base:raise ValueError("base snapshot is empty")
 miss=BASE_REQUIRED-set(base[0])
 if miss:raise ValueError(f"base missing columns: {sorted(miss)}")
 baseidx=index(base,["UNITID","program_id"],"base");registry=registry or load_registry();enrich={"accreditation":accreditation or [],"finance_outcomes":finance or [],"program_outcomes":program_outcomes or [],"transfer":transfer or [],"career_pathways":career or []};validate_all(enrich,registry)
 indexes={name:index(rows,spec["join_grain"],name) for name,rows in enrich.items() for spec in [registry["families"][name]]}
 rows=[]
 for key,b in baseidx.items():
  uid,pid=key;r=dict(b);r["candidate_id"]=f"{uid}:{pid}"
  for name,spec in registry["families"].items():
   join_key=(uid,) if spec["join_grain"]==["UNITID"] else key;hit=indexes[name].get(join_key);r[spec["coverage_field"]]="1" if hit else "0"
   if hit:r=prefixed_merge(r,hit,spec["namespace"],set(spec["join_grain"]))
  rows.append(r)
 rows.sort(key=lambda r:(clean(r["institution_name"]).casefold(),clean(r["program_name"]).casefold(),r["candidate_id"]));return rows
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--base",type=Path,required=True);ap.add_argument("--accreditation",type=Path);ap.add_argument("--finance",type=Path);ap.add_argument("--program-outcomes",type=Path);ap.add_argument("--transfer",type=Path);ap.add_argument("--career",type=Path);ap.add_argument("--data-version",required=True);ap.add_argument("--out-dir",type=Path,required=True);a=ap.parse_args();inputs={"base":a.base,"accreditation":a.accreditation,"finance_outcomes":a.finance,"program_outcomes":a.program_outcomes,"transfer":a.transfer,"career_pathways":a.career};loaded={k:(read_csv(v) if v else []) for k,v in inputs.items()};registry=load_registry();rows=build(loaded["base"],loaded["accreditation"],loaded["finance_outcomes"],loaded["program_outcomes"],loaded["transfer"],loaded["career_pathways"],registry);a.out_dir.mkdir(parents=True,exist_ok=True)
 cols=[]
 for r in rows:
  for k in r:
   if k not in cols:cols.append(k)
 with (a.out_dir/"institution_program_product_snapshot.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
 manifest={"schema_version":"1.2","data_version":a.data_version,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"candidate_grain":"UNITID x program_id","candidate_count":len(rows),"institution_count":len({r['UNITID'] for r in rows}),"enrichment_registry_version":registry["schema_version"],"input_sha256":{k:sha(v) for k,v in inputs.items() if v},"coverage":{name:sum(r[spec['coverage_field']]=='1' for r in rows) for name,spec in registry["families"].items()},"rule":"All enrichments are registry-governed. Missing optional evidence is coverage state, not negative evidence."};(a.out_dir/"institution_program_product_snapshot_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
if __name__=="__main__":main()
