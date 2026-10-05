#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from metadata_service_adapter import build_metadata

def manifest():
 return {"data_version":"SYN-DATA-1","generated_at_utc":"2026-10-05T00:00:00Z","candidate_grain":"UNITID x program_id","candidate_count":2,"institution_count":2,"output_sha256":"a"*64,"enrichment_registry_version":"1.0","source_vintages":{"IPEDS":"2025","OEWS":"May 2025"}}
def activation_record(data_version="SYN-DATA-1",model_version="SYN-MODEL-1"):
 return {"schema_version":"1.0","activation_state":"PRODUCTION_SERVICE_AUTHORIZED","production_authorized":True,"data_version":data_version,"model_version":model_version,"snapshot_sha256":"a"*64,"activation_bundle_sha256":"b"*64,"approved_by":"Human Reviewer","approved_at_utc":"2026-10-05T19:00:00Z","decision_reference":"review-1","recorded_at_utc":"2026-10-05T19:01:00Z","rules":[]}
class MetadataServiceTests(unittest.TestCase):
 def test_review_eligible_is_not_production_authorized(self):
  r=build_metadata(manifest(),"SYN-MODEL-1",{"decision":"ELIGIBLE_FOR_ACTIVATION_REVIEW","checks":[]},{"release_decision":"ELIGIBLE_FOR_REVIEW","blocked_required_checks":0})
  self.assertEqual(r["serving_state"],"review_eligible");self.assertFalse(r["production_authorized"]);self.assertTrue(r["semantic_rules"]["review_eligibility_is_not_production_authorization"])
 def test_exact_activation_record_enables_production_state(self):
  record=activation_record()
  r=build_metadata(manifest(),"SYN-MODEL-1",activation_record=record);self.assertEqual(r["serving_state"],"production");self.assertTrue(r["production_authorized"]);self.assertTrue(r["semantic_rules"]["production_requires_exact_activation_record"])
 def test_mismatched_activation_record_fails_closed(self):
  record=activation_record("OTHER","M")
  with self.assertRaisesRegex(ValueError,"data_version mismatch"):build_metadata(manifest(),"M",activation_record=record)
 def test_blocked_gate_blocks_serving_state(self):
  r=build_metadata(manifest(),"M",{"decision":"BLOCKED"},{"release_decision":"ELIGIBLE_FOR_REVIEW"})
  self.assertEqual(r["serving_state"],"blocked")
 def test_model_not_evaluated_stays_explicit(self):
  r=build_metadata(manifest(),"M",{"decision":"ELIGIBLE_FOR_ACTIVATION_REVIEW"})
  self.assertEqual(r["serving_state"],"data_review_eligible_model_not_evaluated");self.assertEqual(r["release"]["recommendation_decision"],"NOT_EVALUATED")
 def test_source_vintages_are_preserved_not_reinterpreted(self):
  r=build_metadata(manifest(),"M")
  self.assertEqual(r["source_vintages"],{"IPEDS":"2025","OEWS":"May 2025"});self.assertTrue(r["semantic_rules"]["source_vintage_is_not_inferred_freshness"])
 def test_invalid_snapshot_hash_fails_closed(self):
  m=manifest();m["output_sha256"]="not-a-hash"
  with self.assertRaisesRegex(ValueError,"output_sha256"):build_metadata(m,"M")
 def test_blank_versions_fail_closed(self):
  m=manifest();m["data_version"]=""
  with self.assertRaisesRegex(ValueError,"data_version"):build_metadata(m,"M")
  with self.assertRaisesRegex(ValueError,"model_version"):build_metadata(manifest(),"")
 def test_schema_required_top_level_fields_present(self):
  schema=json.loads((P/"schemas/metadata_response.schema.json").read_text())
  r=build_metadata(manifest(),"M")
  self.assertFalse(set(schema["required"])-set(r))
if __name__=="__main__":unittest.main()
