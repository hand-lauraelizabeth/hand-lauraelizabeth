#!/usr/bin/env python3
from __future__ import annotations
import csv,hashlib,json,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from service_host import ServiceState

def write_fixture(root):
 rows=[{"candidate_id":"1:P1","UNITID":"1","institution_name":"Alpha","program_id":"P1","program_name":"CS","cip_code":"11.0101","cip_title":"Computer Science","credential_level":"Bachelors","state":"NY","career__soc_count":"0"}]
 snap=root/"snapshot.csv"
 with snap.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 h=hashlib.sha256(snap.read_bytes()).hexdigest();manifest={"data_version":"D1","output_sha256":h,"candidate_count":1,"institution_count":1,"source_vintages":{}}
 mp=root/"manifest.json";mp.write_text(json.dumps(manifest),encoding="utf-8");return snap,mp,h

class ServiceHostTests(unittest.TestCase):
 def test_nonproduction_host_is_fail_closed_and_serves_core_adapters(self):
  with tempfile.TemporaryDirectory() as d:
   snap,mp,h=write_fixture(Path(d));s=ServiceState(snap,mp,"M1",allowed_origins=["https://example.org"])
   self.assertFalse(s.production_authorized);self.assertEqual(s.health()["candidate_count"],1);self.assertEqual(s.metadata()["snapshot"]["output_sha256"],h)
   self.assertEqual(s.options()["options"]["counts"]["institution_programs"],1);self.assertEqual(s.candidate("1:P1")["candidate_id"],"1:P1")
 def test_snapshot_hash_mismatch_fails_startup(self):
  with tempfile.TemporaryDirectory() as d:
   snap,mp,_=write_fixture(Path(d));m=json.loads(mp.read_text());m["output_sha256"]="a"*64;mp.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,"SHA-256"):ServiceState(snap,mp,"M1")
 def test_duplicate_candidate_id_fails_startup(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap,mp,_=write_fixture(root);rows=list(csv.DictReader(snap.open()));rows.append(dict(rows[0]))
   with snap.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
   m=json.loads(mp.read_text());m["output_sha256"]=hashlib.sha256(snap.read_bytes()).hexdigest();m["candidate_count"]=2;mp.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,"unique"):ServiceState(snap,mp,"M1")
 def test_production_forbids_wildcard_cors(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);snap,mp,h=write_fixture(root)
   act={"schema_version":"1.0","activation_state":"PRODUCTION_SERVICE_AUTHORIZED","production_authorized":True,"data_version":"D1","model_version":"M1","snapshot_sha256":h,"activation_bundle_sha256":"b"*64,"approved_by":"Human Reviewer","approved_at_utc":"2026-10-05T19:00:00Z","decision_reference":"review-1","recorded_at_utc":"2026-10-05T19:01:00Z","rules":[]}
   ap=root/"activation.json";ap.write_text(json.dumps(act))
   with self.assertRaisesRegex(ValueError,"wildcard"):ServiceState(snap,mp,"M1",activation_record_path=ap,allowed_origins=["*"])
 def test_compare_missing_candidate_fails(self):
  with tempfile.TemporaryDirectory() as d:
   snap,mp,_=write_fixture(Path(d));s=ServiceState(snap,mp,"M1")
   with self.assertRaises(KeyError):s.compare({"candidate_ids":["1:P1","2:P2"]})

if __name__=="__main__":unittest.main()
