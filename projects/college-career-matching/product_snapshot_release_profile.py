#!/usr/bin/env python3
"""Create an evidence-only release profile for a product snapshot.

This module reports what is observed. It deliberately does not invent release
thresholds or turn current coverage into an approval policy.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from interface_options_builder import build as build_options

CORE_FIELDS=("candidate_id","UNITID","institution_name","program_id","program_name","cip_code","credential_level","state")

def clean(v): return str(v).strip() if v is not None else ""
def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def profile(snapshot,manifest,snapshot_hash):
 if not snapshot: raise ValueError("snapshot is empty")
 cols=set(snapshot[0])
 missing=[x for x in CORE_FIELDS if x not in cols]
 if missing: raise ValueError(f"snapshot missing core fields: {missing}")
 ids=[clean(r["candidate_id"]) for r in snapshot]
 unitids=[clean(r["UNITID"]) for r in snapshot]
 if any(not x for x in ids): raise ValueError("blank candidate_id")
 if len(ids)!=len(set(ids)): raise ValueError("duplicate candidate_id")
 required_completeness={f:sum(bool(clean(r.get(f))) for r in snapshot)/len(snapshot) for f in CORE_FIELDS}
 coverage={}
 for col in sorted(x for x in cols if x.startswith("coverage__")):
  observed=sum(clean(r.get(col)).lower() in {"1","true","yes"} for r in snapshot)
  coverage[col]=observed/len(snapshot)
 options=build_options(snapshot,clean(manifest.get("data_version")))
 expected=clean(manifest.get("output_sha256"))
 return {
  "schema_version":"1.0",
  "data_version":clean(manifest.get("data_version")),
  "snapshot_sha256":snapshot_hash,
  "manifest_output_sha256":expected or None,
  "manifest_hash_matches":bool(expected) and expected.lower()==snapshot_hash.lower(),
  "candidate_count":len(snapshot),
  "institution_count":len(set(x for x in unitids if x)),
  "core_field_completeness":required_completeness,
  "coverage_rates":coverage,
  "source_vintages":manifest.get("source_vintages",{}),
  "input_sha256":manifest.get("input_sha256",{}),
  "interface_option_counts":options.get("counts",{}),
  "policy_observation_only":True,
  "production_authorized":False,
  "rules":[
   "Observed counts and coverage are evidence, not release thresholds.",
   "No threshold is inferred from the current snapshot.",
   "A release policy must be explicitly configured and evaluated by product_snapshot_release_gate.py.",
   "This profile cannot authorize production activation."
  ]
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 out=profile(read_csv(a.snapshot),read_json(a.manifest),sha256(a.snapshot));a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
