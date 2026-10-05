#!/usr/bin/env python3
"""Build the browser runtime configuration for College + Career Explorer.

Default is fail-closed fixture mode. Production mode is emitted only from an
already validated production activation record and an explicit HTTPS service URL.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
from urllib.parse import urlparse
from service_activation_guard import validate_activation_record

def clean(v): return str(v).strip() if v is not None else ""

def valid_sha(v):
 s=clean(v)
 return len(s)==64 and all(c in "0123456789abcdefABCDEF" for c in s)

def service_url(value,production=False):
 base=clean(value).rstrip("/")
 parsed=urlparse(base)
 if production:
  if parsed.scheme!="https" or not parsed.netloc:raise ValueError("production service_base_url must be an absolute HTTPS URL")
 else:
  loopback=parsed.hostname in {"127.0.0.1","localhost","::1"}
  if not parsed.netloc or not (parsed.scheme=="https" or (parsed.scheme=="http" and loopback)):raise ValueError("staging service_base_url must use HTTPS or loopback HTTP")
 return base

def build_staging(service_base_url,data_version,model_version,snapshot_sha256):
 if not clean(data_version) or not clean(model_version):raise ValueError("staging data_version and model_version must be nonblank")
 if not valid_sha(snapshot_sha256):raise ValueError("staging snapshot_sha256 must be a valid SHA-256")
 return {
  "schema_version":"1.0","mode":"staging","production_authorized":False,
  "fixture_url":"","service_base_url":service_url(service_base_url,False),
  "expected_identity":{"data_version":clean(data_version),"model_version":clean(model_version),"snapshot_sha256":clean(snapshot_sha256).lower(),"activation_bundle_sha256":None},
  "rules":{"fixture_is_non_authoritative":True,"staging_is_non_authoritative":True,"production_requires_activation_record":True,"browser_must_verify_metadata_identity":True}
 }

def build(activation_record=None,service_base_url=None,fixture_url="contract-fixtures.json"):
 if activation_record is None:
  return {
   "schema_version":"1.0",
   "mode":"fixture",
   "production_authorized":False,
   "fixture_url":clean(fixture_url) or "contract-fixtures.json",
   "service_base_url":"",
   "expected_identity":None,
   "rules":{
    "fixture_is_non_authoritative":True,
    "production_requires_activation_record":True,
    "browser_must_verify_metadata_identity":True
   }
  }
 validate_activation_record(activation_record)
 base=service_url(service_base_url,True)
 return {
  "schema_version":"1.0",
  "mode":"production",
  "production_authorized":True,
  "fixture_url":"",
  "service_base_url":base,
  "expected_identity":{
   "data_version":clean(activation_record["data_version"]),
   "model_version":clean(activation_record["model_version"]),
   "snapshot_sha256":clean(activation_record["snapshot_sha256"]).lower(),
   "activation_bundle_sha256":clean(activation_record["activation_bundle_sha256"]).lower()
  },
  "rules":{
   "fixture_is_non_authoritative":True,
   "production_requires_activation_record":True,
   "browser_must_verify_metadata_identity":True
  }
 }

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--activation-record",type=Path);ap.add_argument("--service-base-url");ap.add_argument("--fixture-url",default="contract-fixtures.json");ap.add_argument("--staging-manifest",type=Path);ap.add_argument("--staging-model-version");ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 if a.staging_manifest:
  if a.activation_record:ap.error("--staging-manifest and --activation-record are mutually exclusive")
  m=json.loads(a.staging_manifest.read_text(encoding="utf-8"))
  out=build_staging(a.service_base_url,m.get("data_version"),a.staging_model_version,m.get("output_sha256"))
 else:
  record=json.loads(a.activation_record.read_text(encoding="utf-8")) if a.activation_record else None
  out=build(record,a.service_base_url,a.fixture_url)
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
