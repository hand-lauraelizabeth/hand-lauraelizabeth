#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from ranked_service_binding import build
from ranking_binding_contract import ranking_context_id

def req(page=1):
 return {"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[{"constraint_id":"state","field":"state","operator":"eq","value":"NY","unknown_policy":"keep_visible"}],"preferences":[{"preference_id":"p","dimension":"affordability","importance":3,"priority_explicit":True}],"career_preferences":[],"page":page,"page_size":20}
def c(cid,state="NY"):return {"candidate_id":cid,"state":state}
R=[{"candidate_id":"A","rank":"1","baseline_score":"0.8","review_eligibility":"eligible_for_review"}]
S={"status":"RANKED_RESULTS_ELIGIBLE_FOR_REVIEW","review_eligible_ranked_count":1,"production_authorized":False}

class RankedServiceBindingTests(unittest.TestCase):
 def test_builder_binds_only_eligible_candidate_universe(self):
  b=build(req(),[c("A"),c("B"),c("C","NJ")],R,S,"D","M");self.assertEqual(b["binding"]["eligible_candidate_count"],2);self.assertEqual(b["binding"]["ranked_candidate_count"],1);self.assertEqual(b["binding"]["ranking_context_id"],ranking_context_id(req(),"D","M"))
 def test_excluded_candidate_cannot_appear_in_ranking(self):
  bad=[{"candidate_id":"C","rank":"1","baseline_score":".8","review_eligibility":"eligible_for_review"}]
  with self.assertRaises(ValueError):build(req(),[c("A"),c("C","NJ")],bad,S,"D","M")
 def test_blocked_review_summary_cannot_bind(self):
  s=dict(S);s["status"]="RANKED_RESULTS_BLOCKED_FROM_REVIEW"
  with self.assertRaises(ValueError):build(req(),[c("A")],R,s,"D","M")
 def test_page_two_keeps_same_binding_context(self):
  a=build(req(1),[c("A")],R,S,"D","M");b=build(req(2),[c("A")],R,S,"D","M");self.assertEqual(a["binding"]["ranking_context_id"],b["binding"]["ranking_context_id"])

if __name__=="__main__":unittest.main()
