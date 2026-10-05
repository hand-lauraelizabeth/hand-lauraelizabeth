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
 base=clean(service_base_url).rstrip("/")
 parsed=urlparse(base)
 if parsed.scheme!="https" or not parsed.netloc:
  raise ValueError("production service_base_url must be an absolute HTTPS URL")
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
 ap=argparse.ArgumentParser();ap.add_argument("--activation-record",type=Path);ap.add_argument("--service-base-url");ap.add_argument("--fixture-url",default="contract-fixtures.json");ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 record=json.loads(a.activation_record.read_text(encoding="utf-8")) if a.activation_record else None
 out=build(record,a.service_base_url,a.fixture_url);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2),encoding="utf-8")
if __name__=="__main__":main()
