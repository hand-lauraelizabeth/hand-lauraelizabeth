#!/usr/bin/env python3
"""Build a fail-closed activation-review bundle from a passed snapshot release gate.

The bundle is review evidence only. It cannot mark a snapshot production-ready.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from interface_options_builder import build as build_options

def clean(v): return str(v).strip() if v is not None else ""
def read_csv(path):
 with Path(path).open(newline="",encoding="utf-8-sig") as f:return list(csv.DictReader(f))
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
 return h.hexdigest()

def build(snapshot,manifest,release_decision,snapshot_hash,model_version):
 if clean(release_decision.get("decision"))!="ELIGIBLE_FOR_ACTIVATION_REVIEW":
  raise ValueError("snapshot release decision is not ELIGIBLE_FOR_ACTIVATION_REVIEW")
 checks=release_decision.get("checks")
 if not isinstance(checks,list) or any(clean(x.get("status"))=="FAIL" for x in checks):
  raise ValueError("snapshot release checks are missing or contain FAIL")
 data_version=clean(manifest.get("data_version"))
 if not data_version: raise ValueError("manifest data_version is blank")
 expected=clean(manifest.get("output_sha256"))
 if len(expected)!=64 or expected.lower()!=snapshot_hash.lower(): raise ValueError("snapshot hash does not match manifest output_sha256")
 if manifest.get("candidate_count")!=len(snapshot): raise ValueError("manifest candidate_count mismatch")
 if not clean(model_version): raise ValueError("model_version must be nonblank")
 options=build_options(snapshot,data_version)
 return {
  "schema_version":"1.0",
  "activation_status":"READY_FOR_HUMAN_ACTIVATION_REVIEW",
  "production_authorized":False,
  "data_version":data_version,
  "model_version":clean(model_version),
  "snapshot_sha256":snapshot_hash,
  "candidate_count":len(snapshot),
  "institution_count":options["counts"]["institutions"],
  "interface_option_counts":options["counts"],
  "release_check_summary":{
   "pass":sum(clean(x.get("status"))=="PASS" for x in checks),
   "warn":sum(clean(x.get("status"))=="WARN" for x in checks),
   "fail":sum(clean(x.get("status"))=="FAIL" for x in checks)
  },
  "required_next_action":"human_activation_review",
  "semantic_rules":[
   "READY_FOR_HUMAN_ACTIVATION_REVIEW is not production authorization.",
   "The exact snapshot hash, data version, and model version are pinned in this bundle.",
   "Changing the snapshot requires a new release-gate evaluation and a new bundle.",
   "The public explorer must remain in fixture mode until an activation decision is explicitly recorded elsewhere."
  ]
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--snapshot",type=Path,required=True);ap.add_argument("--manifest",type=Path,required=True);ap.add_argument("--release-decision",type=Path,required=True);ap.add_argument("--model-version",required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 out=build(read_csv(a.snapshot),read_json(a.manifest),read_json(a.release_decision),sha256(a.snapshot),a.model_version);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
