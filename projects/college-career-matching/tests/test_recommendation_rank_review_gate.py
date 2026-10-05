#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from recommendation_rank_review_gate import build

RANKED=[{"candidate_id":"A","ranking_status":"ranked_pending_validation","baseline_score":".8","rank":"1","missing_weighted_dimensions":"","partial_weighted_dimensions":"","weighted_dimension_count":"2"}]
READY={"status":"RANKING_READY_FOR_VALIDATION"}

class RankReviewGateTests(unittest.TestCase):
 def test_release_gate_must_pass_before_review_eligibility(self):
  rows,summary=build(RANKED,READY,{"release_decision":"ELIGIBLE_FOR_REVIEW"});self.assertEqual(len(rows),1);self.assertEqual(rows[0]["review_eligibility"],"eligible_for_review");self.assertFalse(summary["production_authorized"])
 def test_blocked_release_exposes_no_review_eligible_ranking(self):
  rows,summary=build(RANKED,READY,{"release_decision":"BLOCKED"});self.assertEqual(rows,[]);self.assertEqual(summary["status"],"RANKED_RESULTS_BLOCKED_FROM_REVIEW")
 def test_missing_release_decision_fails_closed(self):
  rows,summary=build(RANKED,READY,{});self.assertEqual(rows,[]);self.assertEqual(summary["recommendation_release_decision"],"MISSING")
 def test_ranking_not_ready_remains_blocked_even_if_gate_passes(self):
  rows,_=build(RANKED,{"status":"NO_RANKABLE_CANDIDATES"},{"release_decision":"ELIGIBLE_FOR_REVIEW"});self.assertEqual(rows,[])

if __name__=="__main__":unittest.main()
