#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from service_activation_guard import authorize,canonical_sha256,validate_activation_record
from metadata_service_adapter import build_metadata

def bundle():
 return {"schema_version":"1.0","activation_status":"READY_FOR_HUMAN_ACTIVATION_REVIEW","production_authorized":False,"data_version":"D1","model_version":"M1","snapshot_sha256":"a"*64,"candidate_count":2,"institution_count":2,"interface_option_counts":{},"release_check_summary":{"pass":5,"warn":0,"fail":0},"required_next_action":"human_activation_review","semantic_rules":[]}
def decision(b):
 return {"decision":"APPROVED_FOR_PRODUCTION_SERVICE","activation_bundle_sha256":canonical_sha256(b),"snapshot_sha256":b["snapshot_sha256"],"data_version":b["data_version"],"model_version":b["model_version"],"approved_by":"Human Reviewer","approved_at_utc":"2026-10-05T19:00:00Z","decision_reference":"review-1"}

class ServiceActivationGuardTests(unittest.TestCase):
 def test_exact_human_approval_creates_pinned_authorization(self):
  b=bundle();r=authorize(b,decision(b));self.assertTrue(r["production_authorized"]);self.assertEqual(r["activation_state"],"PRODUCTION_SERVICE_AUTHORIZED");self.assertEqual(r["activation_bundle_sha256"],canonical_sha256(b))
 def test_nonapproval_fails_closed(self):
  b=bundle();d=decision(b);d["decision"]="REJECTED"
  with self.assertRaises(ValueError):authorize(b,d)
 def test_changed_bundle_invalidates_approval(self):
  b=bundle();d=decision(b);b["candidate_count"]=3
  with self.assertRaisesRegex(ValueError,"bundle hash"):authorize(b,d)
 def test_changed_data_version_invalidates_approval(self):
  b=bundle();d=decision(b);d["data_version"]="D2"
  with self.assertRaisesRegex(ValueError,"data_version"):authorize(b,d)
 def test_malformed_production_record_fails_closed(self):
  b=bundle();record=authorize(b,decision(b));record["approved_by"]=""
  with self.assertRaisesRegex(ValueError,"approved_by"):validate_activation_record(record,"D1","M1","a"*64)
 def test_metadata_can_become_production_only_with_matching_activation_record(self):
  b=bundle();record=authorize(b,decision(b));manifest={"data_version":"D1","output_sha256":"a"*64,"candidate_count":2,"institution_count":2,"source_vintages":{}}
  m=build_metadata(manifest,"M1",activation_record=record);self.assertTrue(m["production_authorized"]);self.assertEqual(m["serving_state"],"production")
 def test_metadata_rejects_mismatched_activation_record(self):
  b=bundle();record=authorize(b,decision(b));record["model_version"]="M2";manifest={"data_version":"D1","output_sha256":"a"*64,"candidate_count":2,"institution_count":2,"source_vintages":{}}
  with self.assertRaises(ValueError):build_metadata(manifest,"M1",activation_record=record)

if __name__=="__main__":unittest.main()
