#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from match_service_adapter import match
from ranking_binding_contract import ranking_context_id,candidate_universe_sha256

def req(page=1,size=20,importance=3):
 return {"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[],"preferences":[{"preference_id":"p","dimension":"affordability","importance":importance,"priority_explicit":True}],"career_preferences":[],"geography":{"school_location_semantics":"no_preference","selected_states":[],"work_market_semantics":"unspecified","intended_work_market":None},"page":page,"page_size":size}
def cand(cid,name):
 return {"candidate_id":cid,"UNITID":"U"+cid,"institution_name":name,"program_id":"P1","program_name":"Synthetic","cip_code":"99.9999","state":"NY","dimension__affordability":.8,"coverage__affordability":1,"state__affordability":"complete"}
def bundle(request,cids=("A","B","C")):
 rankings=[
  {"candidate_id":"C","rank":1,"baseline_score":.9,"review_eligibility":"eligible_for_review"},
  {"candidate_id":"A","rank":2,"baseline_score":.7,"review_eligibility":"eligible_for_review"},
 ]
 return {"schema_version":"1.0","review_eligible":True,"production_authorized":False,"binding":{"ranking_context_id":ranking_context_id(request,"D","M"),"data_version":"D","model_version":"M","eligible_candidate_universe_sha256":candidate_universe_sha256(list(cids)),"eligible_candidate_count":len(cids),"ranked_candidate_count":2},"rankings":rankings}

CANDS=[cand("A","Zulu College"),cand("B","Alpha College"),cand("C","Middle College")]

class RankedMatchServiceTests(unittest.TestCase):
 def test_valid_bundle_orders_ranked_before_unranked(self):
  q=req();r=match(q,CANDS,"D","M",ranking_bundle=bundle(q));self.assertEqual([x["candidate_id"] for x in r["results"]],["C","A","B"]);self.assertEqual(r["ordering"]["mode"],"review_eligible_ranking");self.assertEqual(r["ordering"]["review_eligible_ranked_count"],2);self.assertEqual(r["ordering"]["unranked_eligible_count"],1);self.assertFalse(r["ordering"]["production_authorized"])
 def test_result_recommendation_metadata_is_explicit(self):
  q=req();r=match(q,CANDS,"D","M",ranking_bundle=bundle(q));by={x["candidate_id"]:x["recommendation"] for x in r["results"]};self.assertEqual(by["C"]["rank"],1);self.assertEqual(by["C"]["status"],"review_eligible_ranked");self.assertEqual(by["B"]["status"],"eligible_unranked");self.assertIsNone(by["B"]["rank"]);self.assertFalse(by["C"]["production_authorized"])
 def test_pagination_occurs_after_rank_order(self):
  q=req(page=1,size=1);b=bundle(q);p1=match(q,CANDS,"D","M",ranking_bundle=b);q2=req(page=2,size=1);p2=match(q2,CANDS,"D","M",ranking_bundle=b);self.assertEqual(p1["results"][0]["candidate_id"],"C");self.assertEqual(p2["results"][0]["candidate_id"],"A");self.assertEqual(p1["ordering"]["ranking_context_id"],p2["ordering"]["ranking_context_id"]);self.assertNotEqual(p1["request_id"],p2["request_id"])
 def test_changed_preference_invalidates_bundle(self):
  q=req();b=bundle(q)
  with self.assertRaisesRegex(ValueError,"context"):match(req(importance=4),CANDS,"D","M",ranking_bundle=b)
 def test_changed_data_version_invalidates_bundle(self):
  q=req();b=bundle(q)
  with self.assertRaises(ValueError):match(q,CANDS,"D2","M",ranking_bundle=b)
 def test_changed_candidate_universe_invalidates_bundle(self):
  q=req();b=bundle(q)
  with self.assertRaisesRegex(ValueError,"candidate universe"):match(q,CANDS[:2],"D","M",ranking_bundle=b)
 def test_ungated_service_stays_deterministic_and_unranked(self):
  q=req();r=match(q,CANDS,"D","M");self.assertEqual([x["candidate_id"] for x in r["results"]],["B","C","A"]);self.assertEqual(r["ordering"]["mode"],"deterministic_unranked");self.assertTrue(all(x["recommendation"]["status"]=="not_ranked" for x in r["results"]))

if __name__=="__main__":unittest.main()
