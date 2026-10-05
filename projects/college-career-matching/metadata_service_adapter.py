#!/usr/bin/env python3
"""Build the version/readiness metadata response for the interactive matcher.

This endpoint reports what build is being inspected. It does not turn review
eligibility into production authorization and does not invent source freshness.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from service_activation_guard import validate_activation_record

PRODUCT_ELIGIBLE={"ELIGIBLE_FOR_ACTIVATION_REVIEW"}
RECOMMENDATION_ELIGIBLE={"ELIGIBLE_FOR_REVIEW"}
BLOCKED={"BLOCKED"}

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def clean(v): return str(v).strip() if v is not None else ""
def valid_sha256(v):
 s=clean(v)
 return len(s)==64 and all(c in "0123456789abcdefABCDEF" for c in s)

def build_metadata(snapshot_manifest,model_version,product_release=None,recommendation_release=None,activation_record=None):
 data_version=clean(snapshot_manifest.get("data_version"))
 if not data_version: raise ValueError("snapshot manifest data_version must be nonblank")
 model_version=clean(model_version)
 if not model_version: raise ValueError("model_version must be nonblank")
 output_hash=clean(snapshot_manifest.get("output_sha256"))
 if not valid_sha256(output_hash): raise ValueError("snapshot manifest output_sha256 must be a valid SHA-256")
 product_decision=clean((product_release or {}).get("decision")) or "NOT_EVALUATED"
 recommendation_decision=clean((recommendation_release or {}).get("release_decision")) or "NOT_EVALUATED"
 production_authorized=False
 if activation_record is not None:
  validate_activation_record(activation_record,data_version,model_version,output_hash)
  production_authorized=True
 if production_authorized:
  serving_state="production"
 elif product_decision in BLOCKED or recommendation_decision in BLOCKED:
  serving_state="blocked"
 elif product_decision in PRODUCT_ELIGIBLE and recommendation_decision in RECOMMENDATION_ELIGIBLE:
  serving_state="review_eligible"
 elif product_decision in PRODUCT_ELIGIBLE and recommendation_decision=="NOT_EVALUATED":
  serving_state="data_review_eligible_model_not_evaluated"
 else:
  serving_state="not_evaluated"
 vintages=snapshot_manifest.get("source_vintages") or {}
 if not isinstance(vintages,dict): raise ValueError("source_vintages must be an object when present")
 return {
  "schema_version":"1.0",
  "data_version":data_version,
  "model_version":model_version,
  "serving_state":serving_state,
  "production_authorized":production_authorized,
  "snapshot":{
   "generated_at_utc":snapshot_manifest.get("generated_at_utc"),
   "candidate_grain":snapshot_manifest.get("candidate_grain"),
   "candidate_count":snapshot_manifest.get("candidate_count"),
   "institution_count":snapshot_manifest.get("institution_count"),
   "output_sha256":output_hash,
   "enrichment_registry_version":snapshot_manifest.get("enrichment_registry_version"),
  },
  "source_vintages":{k:vintages[k] for k in sorted(vintages)},
  "release":{
   "product_snapshot_decision":product_decision,
   "recommendation_decision":recommendation_decision,
   "product_checks":(product_release or {}).get("checks",[]),
   "blocked_recommendation_checks":(recommendation_release or {}).get("blocked_required_checks"),
  },
  "semantic_rules":{
   "review_eligibility_is_not_production_authorization":True,
   "source_vintage_is_not_inferred_freshness":True,
   "browser_must_not_select_versions_independently":True,
   "production_requires_exact_activation_record":True
  }
 }

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--snapshot-manifest",type=Path,required=True)
 ap.add_argument("--model-version",required=True)
 ap.add_argument("--product-release",type=Path)
 ap.add_argument("--recommendation-release",type=Path)
 ap.add_argument("--activation-record",type=Path)
 ap.add_argument("--output",type=Path,required=True)
 a=ap.parse_args()
 response=build_metadata(
  load_json(a.snapshot_manifest),a.model_version,
  load_json(a.product_release) if a.product_release else None,
  load_json(a.recommendation_release) if a.recommendation_release else None,
  load_json(a.activation_record) if a.activation_record else None)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 a.output.write_text(json.dumps(response,indent=2),encoding="utf-8")

if __name__=="__main__": main()
