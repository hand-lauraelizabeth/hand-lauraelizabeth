#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from campus_context_preference_normalizer import normalize

def ref(uid,transit,walk):
 return {"UNITID":uid,"campus__transit_stop_distance_m":str(transit),"campus__transit_stop_distance_m__state":"observed","campus__walkability_index":str(walk),"campus__walkability_index__state":"observed"}

def cand(cid,transit="",transit_state="missing",walk="",walk_state="missing",housing="unknown",disability="",disability_state="missing"):
 return {"candidate_id":cid,"campus__transit_stop_distance_m":str(transit),"campus__transit_stop_distance_m__state":transit_state,"campus__walkability_index":str(walk),"campus__walkability_index__state":walk_state,"campus__housing_choice_state":housing,"campus__disability_services_evidence_available":disability,"campus__disability_services_registered_share__state":disability_state}

class CampusPreferenceNormalizerTests(unittest.TestCase):
 def setUp(self):
  self.reference=[ref("1",100,5),ref("2",300,10),ref("3",700,15),ref("4",1100,20)]
 def by_feature(self,rows):
  return {r["feature_id"]:r for r in rows}
 def test_transit_and_walkability_use_pinned_reference_percentiles(self):
  rows,_,qa=normalize([cand("A",300,"observed",15,"observed")],self.reference,"REF-1");x=self.by_feature(rows)
  self.assertAlmostEqual(x["campus_transit_nearest_stop_distance"]["normalized_value"],0.625)
  self.assertAlmostEqual(x["campus_walkability_index"]["normalized_value"],0.625)
  self.assertEqual(qa["reference_id"],"REF-1")
 def test_result_set_does_not_change_percentile(self):
  a=normalize([cand("A",300,"observed",15,"observed")],self.reference,"REF-1")[0]
  b=normalize([cand("A",300,"observed",15,"observed"),cand("B",999,"observed",6,"observed")],self.reference,"REF-1")[0]
  av=self.by_feature([r for r in a if r["candidate_id"]=="A"]);bv=self.by_feature([r for r in b if r["candidate_id"]=="A"])
  self.assertEqual(av["campus_transit_nearest_stop_distance"]["normalized_value"],bv["campus_transit_nearest_stop_distance"]["normalized_value"])
 def test_housing_choice_is_exact_target_match(self):
  good=self.by_feature(normalize([cand("A",housing="choice_available")],self.reference,"R")[0])["campus_housing_choice"]
  bad=self.by_feature(normalize([cand("B",housing="required_for_all_ftft")],self.reference,"R")[0])["campus_housing_choice"]
  self.assertEqual(good["normalized_value"],1.0);self.assertEqual(bad["normalized_value"],0.0)
 def test_unknown_housing_is_missing_not_zero(self):
  r=self.by_feature(normalize([cand("A",housing="unknown")],self.reference,"R")[0])["campus_housing_choice"]
  self.assertIsNone(r["normalized_value"]);self.assertEqual(r["evidence_state"],"missing")
 def test_disability_documentation_is_evidence_availability_not_quality(self):
  observed=self.by_feature(normalize([cand("A",disability="true",disability_state="observed")],self.reference,"R")[0])["campus_disability_services_documented"]
  missing=self.by_feature(normalize([cand("B",disability="",disability_state="not_published")],self.reference,"R")[0])["campus_disability_services_documented"]
  self.assertEqual(observed["normalized_value"],1.0);self.assertIsNone(missing["normalized_value"]);self.assertEqual(missing["evidence_state"],"not_published")
 def test_each_dimension_has_one_unit_weight_feature(self):
  _,policy,_=normalize([cand("A")],self.reference,"R")
  self.assertEqual(len(policy),4);self.assertTrue(all(x["within_dimension_weight"]=="1" and x["partial_policy"]=="block" for x in policy));self.assertEqual(len({x["dimension"] for x in policy}),4)
 def test_duplicate_reference_institution_fails(self):
  with self.assertRaises(ValueError):normalize([cand("A")],[ref("1",100,5),ref("1",200,8)],"R")
 def test_too_small_reference_fails(self):
  with self.assertRaises(ValueError):normalize([cand("A")],[ref("1",100,5)],"R")
 def test_observed_nonnumeric_transit_fails(self):
  with self.assertRaises(ValueError):normalize([cand("A","nearby","observed")],self.reference,"R")

if __name__=="__main__":unittest.main()
