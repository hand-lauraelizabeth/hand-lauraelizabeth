#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest,hashlib,json,tempfile,csv
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from product_snapshot_release_profile import profile
from product_snapshot_activation_bundle import build

def row(cid,uid,state="NY",cov="true"):
 return {"candidate_id":cid,"UNITID":uid,"institution_name":"School "+uid,"program_id":"P"+cid,"program_name":"Program "+cid,"cip_code":"11.0101","cip_title":"Computer Science","credential_level":"Bachelors","state":state,"coverage__career":cov}
def digest(rows):
 with tempfile.NamedTemporaryFile("w+",newline="",encoding="utf-8",delete=False) as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);name=f.name
 h=hashlib.sha256(Path(name).read_bytes()).hexdigest();Path(name).unlink();return h

class SnapshotReleaseReadinessTests(unittest.TestCase):
 def setUp(self):
  self.rows=[row("A","1"),row("B","2",cov="false")];self.hash=digest(self.rows)
  self.manifest={"data_version":"D1","candidate_count":2,"output_sha256":self.hash,"input_sha256":{"x":"a"*64},"source_vintages":{"ipeds":"2025"}}
  self.decision={"decision":"ELIGIBLE_FOR_ACTIVATION_REVIEW","checks":[{"status":"PASS"},{"status":"WARN"}]}
 def test_profile_reports_observations_without_authorization(self):
  p=profile(self.rows,self.manifest,self.hash);self.assertEqual(p["candidate_count"],2);self.assertEqual(p["coverage_rates"]["coverage__career"],.5);self.assertTrue(p["policy_observation_only"]);self.assertFalse(p["production_authorized"])
 def test_activation_bundle_pins_identity_and_stays_nonproduction(self):
  b=build(self.rows,self.manifest,self.decision,self.hash,"M1");self.assertEqual(b["activation_status"],"READY_FOR_HUMAN_ACTIVATION_REVIEW");self.assertEqual(b["snapshot_sha256"],self.hash);self.assertFalse(b["production_authorized"]);self.assertEqual(b["required_next_action"],"human_activation_review")
 def test_blocked_gate_fails_closed(self):
  d={"decision":"BLOCKED","checks":[{"status":"FAIL"}]}
  with self.assertRaises(ValueError):build(self.rows,self.manifest,d,self.hash,"M1")
 def test_hash_mismatch_fails_closed(self):
  m=dict(self.manifest);m["output_sha256"]="b"*64
  with self.assertRaises(ValueError):build(self.rows,m,self.decision,self.hash,"M1")
 def test_model_version_required(self):
  with self.assertRaises(ValueError):build(self.rows,self.manifest,self.decision,self.hash,"")

if __name__=="__main__":unittest.main()
