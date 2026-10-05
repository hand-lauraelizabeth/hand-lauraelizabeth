#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from match_service_adapter import match,validate_request

def request(mode="broad_exploration"):
 return {"schema_version":"1.0","decision_mode":mode,"constraints":[{"constraint_id":"state","field":"state","operator":"eq","value":"NY","unknown_policy":"keep_visible"}],"preferences":[{"preference_id":"cost","dimension":"affordability","importance":3,"priority_explicit":True}],"career_preferences":[],"page":1,"page_size":20}
def candidate(cid,state="NY"):
 return {"candidate_id":cid,"UNITID":"FIC-"+cid,"institution_name":"Fictional College "+cid,"program_id":"P1","program_name":"Synthetic Studies","cip_code":"99.9999","state":state,"dimension__affordability":.8,"coverage__affordability":1,"state__affordability":"complete","pathway_count":2,"source_freshness":[{"source_family":"synthetic","vintage":"TEST"}]}
class MatchServiceTests(unittest.TestCase):
 def test_match_filters_failed_constraint_and_returns_program_grain(self):
  r=match(request(),[candidate("A"),candidate("B","NJ")],"SYN-DATA-1","SYN-MODEL-1")
  self.assertEqual(r["result_count"],1);self.assertEqual(r["results"][0]["candidate_id"],"A");self.assertEqual(r["results"][0]["program"]["cip_code"],"99.9999");self.assertEqual(r["results"][0]["dimensions"][0]["dimension"],"affordability")
 def test_keep_visible_unknown_is_not_silently_excluded(self):
  c=candidate("A");c["state"]=""
  r=match(request(),[c],"SYN-DATA-1","SYN-MODEL-1");self.assertEqual(r["results"][0]["eligibility"]["status"],"eligible_with_unknown");self.assertTrue(r["results"][0]["explanation"]["unknowns"])
 def test_exclude_unknown_removes_candidate(self):
  q=request();q["constraints"][0]["unknown_policy"]="exclude_unknown";c=candidate("A");c["state"]=""
  self.assertEqual(match(q,[c],"D","M")["result_count"],0)
 def test_skipped_preferences_need_no_placeholder(self):
  q=request();q["preferences"]=[];validate_request(q);self.assertEqual(match(q,[candidate("A")],"D","M")["result_count"],1)
 def test_transfer_mode_does_not_create_transfer_claim(self):
  q=request("transfer");q["transfer_context"]={"source_institution_id":"FIC-SOURCE","source_system":"synthetic","completed_course_ids":[],"target_program_required":False}
  r=match(q,[candidate("A")],"D","M");self.assertIsNone(r["results"][0]["transfer"])
 def test_only_explicit_preferences_allowed(self):
  q=request();q["preferences"][0]["priority_explicit"]=False
  with self.assertRaises(ValueError):validate_request(q)
if __name__=="__main__":unittest.main()
