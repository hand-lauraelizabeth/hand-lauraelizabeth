#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from service_runtime_config import build
from public_explorer_deployment import inject

def record():
 return {"schema_version":"1.0","activation_state":"PRODUCTION_SERVICE_AUTHORIZED","production_authorized":True,"data_version":"D1","model_version":"M1","snapshot_sha256":"a"*64,"activation_bundle_sha256":"b"*64,"approved_by":"Human Reviewer","approved_at_utc":"2026-10-05T19:00:00Z","decision_reference":"review-1","recorded_at_utc":"2026-10-05T19:01:00Z","rules":[]}

class ServiceRuntimeConfigTests(unittest.TestCase):
 def test_no_activation_record_defaults_to_fixture(self):
  r=build();self.assertEqual(r["mode"],"fixture");self.assertFalse(r["production_authorized"]);self.assertIsNone(r["expected_identity"])
 def test_production_requires_https_and_authorized_record(self):
  with self.assertRaisesRegex(ValueError,"HTTPS"):build(record(),"http://example.org/api")
  bad=record();bad["production_authorized"]=False
  with self.assertRaisesRegex(ValueError,"does not authorize"):build(bad,"https://example.org/api")
 def test_production_config_pins_identity(self):
  r=build(record(),"https://example.org/api/");self.assertEqual(r["mode"],"production");self.assertTrue(r["production_authorized"]);self.assertEqual(r["service_base_url"],"https://example.org/api");self.assertEqual(r["expected_identity"]["data_version"],"D1")
 def test_deployment_injects_runtime_without_changing_source_semantics(self):
  src='<div id="leh-ccx"><p>Explorer</p></div>';r=build()
  out=inject(src,r);self.assertIn('id="ccx-runtime-config"',out);self.assertIn('"mode":"fixture"',out);self.assertIn("<p>Explorer</p>",out)
 def test_deployment_rejects_unauthorized_production_object(self):
  r=build();r["mode"]="production"
  with self.assertRaisesRegex(ValueError,"not authorized"):inject('<div id="leh-ccx"></div>',r)

if __name__=="__main__":unittest.main()
