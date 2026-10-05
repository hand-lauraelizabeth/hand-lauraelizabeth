#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from product_enrichment_registry import load_registry,validate_family
from transfer_career_product_bridge import summarize
from product_snapshot_builder import build
class GovernanceTests(unittest.TestCase):
 def test_unregistered_family_fails(self):
  with self.assertRaises(ValueError):validate_family("mystery",[{"UNITID":"1"}])
 def test_registry_enforces_family_grain(self):
  with self.assertRaises(ValueError):validate_family("career_pathways",[{"UNITID":"1"}])
 def test_transfer_bridge_summarizes_without_guarantee(self):
  r=summarize([{"UNITID":"1","program_id":"P1","evidence_level":"course_equivalency","source_system":"CUNY"},{"UNITID":"1","program_id":"P1","evidence_level":"program_articulation","source_system":"CUNY"}],"transfer")[0];self.assertEqual(r["evidence_record_count"],"2");self.assertNotIn("guaranteed",r)
 def test_career_bridge_preserves_many_to_many_soc(self):
  r=summarize([{"UNITID":"1","program_id":"P1","soc_code":"15-1252"},{"UNITID":"1","program_id":"P1","soc_code":"15-1211"}],"career")[0];self.assertEqual(r["soc_count"],"2");self.assertIn("15-1252",r["soc_codes"])
 def test_bridged_evidence_enters_registered_namespaces(self):
  base=[{"UNITID":"1","institution_name":"Alpha","program_id":"P1","program_name":"CS","cip_code":"11.0101","credential_level":"Bachelors","state":"NY"}];tr=summarize([{"UNITID":"1","program_id":"P1","evidence_level":"course_equivalency","source_system":"CUNY"}],"transfer");car=summarize([{"UNITID":"1","program_id":"P1","soc_code":"15-1252"}],"career");r=build(base,transfer=tr,career=car)[0];self.assertEqual(r["coverage__transfer"],"1");self.assertEqual(r["coverage__career_pathways"],"1");self.assertEqual(r["career__soc_count"],"1")
if __name__=="__main__":unittest.main()
