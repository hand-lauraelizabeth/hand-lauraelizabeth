#!/usr/bin/env python3
"""Validate an explicit human activation decision against a review bundle.

This module creates no approval. It only verifies a separately supplied human
decision and pins it to the exact activation-review bundle and data/model
identity. Mismatches fail closed.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

APPROVED="APPROVED_FOR_PRODUCTION_SERVICE"

def clean(v): return str(v).strip() if v is not None else ""
def canonical_sha256(obj):
 payload=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")
 return hashlib.sha256(payload).hexdigest()
def valid_iso(v):
 try:
  x=datetime.fromisoformat(clean(v).replace("Z","+00:00"))
  return x.tzinfo is not None
 except Exception:return False

def authorize(bundle,decision):
 if bundle.get("production_authorized") is not False:
  raise ValueError("activation-review bundle must not already claim production authorization")
 if clean(bundle.get("activation_status"))!="READY_FOR_HUMAN_ACTIVATION_REVIEW":
  raise ValueError("activation-review bundle is not ready for human review")
 if clean(decision.get("decision"))!=APPROVED:
  raise ValueError("human activation decision is not APPROVED_FOR_PRODUCTION_SERVICE")
 approver=clean(decision.get("approved_by"))
 if not approver: raise ValueError("approved_by must be nonblank")
 approved_at=clean(decision.get("approved_at_utc"))
 if not valid_iso(approved_at): raise ValueError("approved_at_utc must be timezone-aware ISO 8601")
 bundle_hash=canonical_sha256(bundle)
 if clean(decision.get("activation_bundle_sha256")).lower()!=bundle_hash:
  raise ValueError("activation decision does not match activation-review bundle hash")
 for key in ("snapshot_sha256","data_version","model_version"):
  if clean(decision.get(key))!=clean(bundle.get(key)):
   raise ValueError(f"activation decision {key} mismatch")
 return {
  "schema_version":"1.0",
  "activation_state":"PRODUCTION_SERVICE_AUTHORIZED",
  "production_authorized":True,
  "data_version":clean(bundle["data_version"]),
  "model_version":clean(bundle["model_version"]),
  "snapshot_sha256":clean(bundle["snapshot_sha256"]),
  "activation_bundle_sha256":bundle_hash,
  "approved_by":approver,
  "approved_at_utc":approved_at,
  "decision_reference":clean(decision.get("decision_reference")) or None,
  "recorded_at_utc":datetime.now(timezone.utc).isoformat(),
  "rules":[
   "This record verifies a separately supplied human approval; it does not create that approval.",
   "Any change to the activation-review bundle, snapshot, data version, or model version invalidates the authorization.",
   "Production authorization applies only to the exact identity pinned here."
  ]
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--activation-bundle",type=Path,required=True);ap.add_argument("--human-decision",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 bundle=json.loads(a.activation_bundle.read_text(encoding="utf-8"));decision=json.loads(a.human_decision.read_text(encoding="utf-8"));out=authorize(bundle,decision);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
