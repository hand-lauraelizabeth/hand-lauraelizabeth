#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from candidate_detail_service import candidate_detail
from compare_service_adapter import compare

def c(uid,pid,name):return {"candidate_id":f"{uid}:{pid}","UNITID":uid,"institution_name":name,"program_id":pid,"program_name":"CS","cip_code":"11.0101","credential_level":"Bachelors","state":"NY","finance__net_price":"12000","finance__net_price__state":"observed","program_outcomes__median_earnings":"70000","program_outcomes__median_earnings__state":"observed","coverage__program_outcomes":"1","coverage__transfer":"0","coverage__career_pathways":"1","career__soc_count":"1","career__soc_codes":"15-1252"}
class DetailCompareTests(unittest.TestCase):
 def test_detail_keeps_institution_and_program_outcomes_separate(self):
  x=candidate_detail(c("1","P1","Alpha"),data_version="D1");self.assertEqual(x["affordability"]["net_price"]["value"],"12000");self.assertEqual(x["program_outcomes"]["median_earnings"]["value"],"70000")
 def test_missing_is_explicit_not_zero(self):
  x=candidate_detail(c("1","P1","Alpha"));self.assertEqual(x["affordability"]["cost_of_attendance"]["evidence_state"],"missing");self.assertIsNone(x["affordability"]["cost_of_attendance"]["value"])
 def test_compare_requires_multiple_unique_candidates(self):
  with self.assertRaises(ValueError):compare([c("1","P1","Alpha")])
  with self.assertRaises(ValueError):compare([c("1","P1","Alpha"),c("1","P1","Alpha")])
 def test_compare_does_not_declare_winner(self):
  r=compare([c("1","P1","Alpha"),c("2","P2","Beta")],data_version="D1");self.assertTrue(r["semantic_rules"]["no_automatic_winner"]);self.assertNotIn("winner",r)
 def test_compare_preserves_candidate_order(self):
  r=compare([c("2","P2","Beta"),c("1","P1","Alpha")]);self.assertEqual(r["candidate_ids"],["2:P2","1:P1"])
if __name__=="__main__":unittest.main()
