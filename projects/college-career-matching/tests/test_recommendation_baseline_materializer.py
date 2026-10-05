#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from recommendation_baseline_materializer import build

def dim(cid,name,value,status="complete"):
 return {"candidate_id":cid,"dimension":name,"dimension_value":value,"dimension_status":status,"dimension_coverage_rate":"1"}
def weights():
 return [{"scenario_id":"baseline","dimension":"transit_access_fit","weight":"0.75"},{"scenario_id":"baseline","dimension":"walkability_fit","weight":"0.25"}]

class BaselineMaterializerTests(unittest.TestCase):
 def test_scores_only_explicit_weighted_dimensions(self):
  rows,ranked,_,sens,summary=build([dim("A","transit_access_fit",".8"),dim("A","walkability_fit",".4"),dim("A","housing_context_fit","0")],weights())
  self.assertAlmostEqual(ranked[0]["baseline_score"],.7);self.assertEqual(summary["weighted_dimension_count"],2);self.assertEqual(set(sens[0]),{"candidate_id","transit_access_fit","walkability_fit"})
 def test_unresolved_weighted_dimension_leaves_candidate_unranked(self):
  rows,ranked,unranked,_,_=build([dim("A","transit_access_fit",".8"),dim("A","walkability_fit","","partial_blocked")],weights())
  self.assertEqual(ranked,[]);self.assertEqual(unranked[0]["ranking_status"],"unranked_unresolved_weighted_dimension");self.assertEqual(unranked[0]["missing_weighted_dimensions"],"walkability_fit")
 def test_missing_weighted_row_is_not_reweighted_away(self):
  _,ranked,unranked,_,_=build([dim("A","transit_access_fit",".8")],weights());self.assertEqual(ranked,[]);self.assertEqual(unranked[0]["missing_weighted_dimensions"],"walkability_fit")
 def test_partial_renormalized_dimension_can_rank_but_is_flagged(self):
  _,ranked,_,_,summary=build([dim("A","transit_access_fit",".8","partial_renormalized"),dim("A","walkability_fit",".4")],weights())
  self.assertEqual(ranked[0]["partial_weighted_dimensions"],"transit_access_fit");self.assertEqual(summary["partial_evidence_ranked_candidate_count"],1)
 def test_exact_ties_share_rank(self):
  dims=[dim("A","transit_access_fit",".8"),dim("A","walkability_fit",".4"),dim("B","transit_access_fit",".8"),dim("B","walkability_fit",".4")]
  _,ranked,_,_,_=build(dims,weights());self.assertEqual([r["rank"] for r in ranked],[1,1])
 def test_no_baseline_means_no_manufactured_ranking(self):
  rows,ranked,unranked,sens,summary=build([dim("A","transit_access_fit",".8")],[])
  self.assertEqual(ranked,[]);self.assertEqual(sens,[]);self.assertEqual(summary["status"],"NO_EXPLICIT_PRIORITIES");self.assertEqual(unranked[0]["ranking_status"],"unranked_no_explicit_priorities")
 def test_out_of_range_dimension_fails(self):
  with self.assertRaises(ValueError):build([dim("A","transit_access_fit","1.2"),dim("A","walkability_fit",".4")],weights())
 def test_negative_weight_fails(self):
  with self.assertRaises(ValueError):build([dim("A","transit_access_fit",".8")],[{"scenario_id":"baseline","dimension":"transit_access_fit","weight":"-1"}])

if __name__=="__main__":unittest.main()
