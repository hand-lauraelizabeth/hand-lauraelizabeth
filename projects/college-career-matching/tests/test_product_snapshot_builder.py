#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from product_snapshot_builder import build
from interface_options_builder import build as build_options

def base(uid,pid,name="Synthetic Studies"):
 return {"UNITID":uid,"institution_name":"Fictional "+uid,"program_id":pid,"program_name":name,"cip_code":"99.9999","credential_level":"Bachelors","state":"NY"}
class SnapshotTests(unittest.TestCase):
 def test_enrichment_does_not_change_candidate_universe(self):
  b=[base("U1","P1"),base("U2","P2")];acc=[{"UNITID":"U1","status":"accredited"}];career=[{"UNITID":"U1","program_id":"P1","pathway_count":"3"}]
  r=build(b,accreditation=acc,career=career);self.assertEqual(len(r),2);self.assertEqual({x["candidate_id"] for x in r},{"U1:P1","U2:P2"})
 def test_missing_enrichment_is_coverage_not_negative_fact(self):
  r=build([base("U1","P1")])[0];self.assertEqual(r["coverage__transfer"],"0");self.assertFalse(any(k.startswith("transfer__") for k in r))
 def test_namespaces_prevent_enrichment_overwrite(self):
  r=build([base("U1","P1")],finance=[{"UNITID":"U1","institution_name":"SHOULD NOT REPLACE","net_price":"10000"}])[0];self.assertEqual(r["institution_name"],"Fictional U1");self.assertEqual(r["finance__institution_name"],"SHOULD NOT REPLACE");self.assertEqual(r["finance__net_price"],"10000")
 def test_duplicate_base_identity_fails(self):
  with self.assertRaises(ValueError):build([base("U1","P1"),base("U1","P1")])
 def test_duplicate_enrichment_identity_fails(self):
  with self.assertRaises(ValueError):build([base("U1","P1")],career=[{"UNITID":"U1","program_id":"P1"},{"UNITID":"U1","program_id":"P1"}])
 def test_snapshot_directly_feeds_interface_options(self):
  r=build([base("U1","P1","Alpha"),base("U2","P2","Beta")]);o=build_options(r,"SYN-1");self.assertEqual(o["counts"]["institution_programs"],2);self.assertEqual({p["value"] for p in o["programs"]},{"U1:P1","U2:P2"})
if __name__=="__main__":unittest.main()
