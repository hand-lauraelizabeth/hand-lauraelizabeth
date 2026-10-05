#!/usr/bin/env python3
"""Build a deterministic fictional product snapshot for HTTP staging.

All institutions/programs are invented. This bundle exists only to exercise the
service/deployment boundary and must never be presented as college data.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

ROWS=[
 {"candidate_id":"SYN001:P1","UNITID":"SYN001","institution_name":"North Harbor College","city":"Harbor City","state":"NY","program_id":"P1","program_name":"Data & Information Systems","cip_code":"11.0101","cip_title":"Computer and Information Sciences, General","credential_level":"Bachelors","online_available":"true","finance__net_price":"14800","finance__net_price__state":"observed","career__soc_count":"2","career__soc_codes":"15-2051|15-1211","coverage__career_pathways":"1"},
 {"candidate_id":"SYN002:P2","UNITID":"SYN002","institution_name":"Metro Public College","city":"Metro City","state":"NY","program_id":"P2","program_name":"Information Technology","cip_code":"11.0103","cip_title":"Information Technology","credential_level":"Bachelors","online_available":"false","finance__net_price":"11200","finance__net_price__state":"observed","career__soc_count":"2","career__soc_codes":"15-1211|15-1212","coverage__career_pathways":"1"},
 {"candidate_id":"SYN003:P3","UNITID":"SYN003","institution_name":"River State University","city":"River City","state":"NJ","program_id":"P3","program_name":"Applied Computing","cip_code":"11.0199","cip_title":"Computer and Information Sciences, Other","credential_level":"Bachelors","online_available":"true","finance__net_price":"17350","finance__net_price__state":"observed","career__soc_count":"2","career__soc_codes":"15-1252|15-2051","coverage__career_pathways":"1"},
 {"candidate_id":"SYN004:P4","UNITID":"SYN004","institution_name":"Cedar Valley College","city":"Cedar City","state":"PA","program_id":"P4","program_name":"Cybersecurity Systems","cip_code":"11.1003","cip_title":"Computer and Information Systems Security/Auditing/Information Assurance","credential_level":"Bachelors","online_available":"false","finance__net_price":"15950","finance__net_price__state":"observed","career__soc_count":"2","career__soc_codes":"15-1212|15-1299","coverage__career_pathways":"1"}
]

def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def build(out_dir,data_version="synthetic-http-staging-1"):
 out_dir=Path(out_dir);out_dir.mkdir(parents=True,exist_ok=True)
 snapshot=out_dir/"institution_program_product_snapshot.csv"
 fields=list(ROWS[0])
 with snapshot.open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(ROWS)
 manifest={
  "schema_version":"1.3","data_version":data_version,
  "generated_at_utc":datetime.now(timezone.utc).isoformat(),
  "candidate_grain":"UNITID x program_id","candidate_count":len(ROWS),
  "institution_count":len({r["UNITID"] for r in ROWS}),
  "enrichment_registry_version":"synthetic-staging-1",
  "input_sha256":{},"output_sha256":sha256(snapshot),
  "coverage":{"career_pathways":len(ROWS)},
  "source_vintages":{"synthetic_fixture":"FICTIONAL"},
  "rule":"Fictional staging data only. No institution or program record is authoritative."
 }
 manifest_path=out_dir/"institution_program_product_snapshot_manifest.json"
 manifest_path.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 return snapshot,manifest_path

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out-dir",type=Path,required=True);ap.add_argument("--data-version",default="synthetic-http-staging-1");a=ap.parse_args()
 snapshot,manifest=build(a.out_dir,a.data_version)
 print(json.dumps({"snapshot":str(snapshot),"manifest":str(manifest),"data_version":a.data_version}))
if __name__=="__main__":main()
