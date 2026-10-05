#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from ranking_binding_contract import ranking_context_id,candidate_universe_sha256,validate_bundle

def request(page=1):
 return {"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[],"preferences":[{"preference_id":"p","dimension":"affordability","importance":3,"priority_explicit":True}],"career_preferences":[],"geography":{"school_location_semantics":"no_preference","selected_states":[],"work_market_semantics":"unspecified","intended_work_market":None},"page":page,"page_size":20}
def bundle(req=None):
 req=req or request()
 return {"schema_version":"1.0","review_eligible":True,"production_authorized":False,"binding":{"ranking_context_id":ranking_context_id(req,"D","M"),"data_version":"D","model_version":"M","eligible_candidate_universe_sha256":candidate_universe_sha256(["A","B"]),"eligible_candidate_count":2,"ranked_candidate_count":2},"rankings":[{"candidate_id":"A","rank":1,"baseline_score":.8,"review_eligibility":"eligible_for_review"},{"candidate_id":"B","rank":2,"baseline_score":.6,"review_eligibility":"eligible_for_review"}]}

class RankingBindingContractTests(unittest.TestCase):
 def test_pagination_does_not_change_ranking_context(self):
  self.assertEqual(ranking_context_id(request(1),"D","M"),ranking_context_id(request(2),"D","M"))
 def test_preference_change_invalidates_context(self):
  a=request();b=request();b["preferences"][0]["importance"]=4;self.assertNotEqual(ranking_context_id(a,"D","M"),ranking_context_id(b,"D","M"))
 def test_candidate_digest_is_order_independent(self):
  self.assertEqual(candidate_universe_sha256(["A","B"]),candidate_universe_sha256(["B","A"]))
 def test_exact_binding_validates(self):
  by=validate_bundle(bundle(),request(),"D","M",["B","A"]);self.assertEqual(set(by),{"A","B"})
 def test_data_version_mismatch_fails(self):
  with self.assertRaises(ValueError):validate_bundle(bundle(),request(),"D2","M",["A","B"])
 def test_candidate_universe_mismatch_fails(self):
  with self.assertRaises(ValueError):validate_bundle(bundle(),request(),"D","M",["A","C"])
 def test_tampered_rank_fails(self):
  b=bundle();b["rankings"][0]["rank"]=2
  with self.assertRaises(ValueError):validate_bundle(b,request(),"D","M",["A","B"])
 def test_production_authorization_claim_fails(self):
  b=bundle();b["production_authorized"]=True
  with self.assertRaises(ValueError):validate_bundle(b,request(),"D","M",["A","B"])

if __name__=="__main__":unittest.main()
