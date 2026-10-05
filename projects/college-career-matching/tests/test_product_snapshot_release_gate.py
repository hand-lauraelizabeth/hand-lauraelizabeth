#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from product_snapshot_release_gate import evaluate

def row(uid="U1",pid="P1",career="1"):
 return {"candidate_id":f"{uid}:{pid}","UNITID":uid,"institution_name":"Fictional "+uid,"program_id":pid,"program_name":"Synthetic Studies","cip_code":"99.9999","credential_level":"Bachelors","state":"NY","coverage__career_pathways":career}
def manifest(count=1):return {"data_version":"SYN-1","candidate_count":count,"input_sha256":{"base":"a"*64},"source_vintages":{"IPEDS":"TEST"}}
def status(checks,cid):return next(x["status"] for x in checks if x["check_id"]==cid)
class GateTests(unittest.TestCase):
 def test_clean_snapshot_passes_configured_checks(self):
  c=evaluate([row()],manifest(),{"min_candidate_count":1,"min_institution_count":1,"min_coverage_rate":{"career_pathways":1},"required_source_vintages":["IPEDS"]});self.assertFalse(any(x["status"]=="FAIL" for x in c));self.assertEqual(status(c,"interface_options_build"),"PASS")
 def test_duplicate_identity_blocks(self):
  c=evaluate([row(),row()],manifest(2),{});self.assertEqual(status(c,"candidate_identity_unique"),"FAIL")
 def test_candidate_regression_floor_blocks(self):
  c=evaluate([row()],manifest(),{"previous_candidate_count":10,"min_candidate_retention_ratio":.9});self.assertEqual(status(c,"candidate_retention"),"FAIL")
 def test_coverage_threshold_is_configured_not_invented(self):
  c=evaluate([row(career="0")],manifest(),{"min_coverage_rate":{"career_pathways":.8}});self.assertEqual(status(c,"coverage_career_pathways"),"FAIL");self.assertFalse(any(x["check_id"].startswith("coverage_transfer") for x in c))
 def test_missing_required_vintage_blocks(self):
  m=manifest();m["source_vintages"]={};c=evaluate([row()],m,{"required_source_vintages":["IPEDS"]});self.assertEqual(status(c,"vintage_IPEDS"),"FAIL")
 def test_manifest_count_mismatch_blocks(self):
  self.assertEqual(status(evaluate([row()],manifest(99),{}),"manifest_candidate_count"),"FAIL")
if __name__=="__main__":unittest.main()
