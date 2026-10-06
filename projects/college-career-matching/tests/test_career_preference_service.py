#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from career_preference_service import build,validate_preferences

ATTRS=[
 {"occ_code":"15-2051","attribute_id":"onet31:work_activity:4.A.2.a.4:IM","attribute_value":"5","evidence_state":"observed","element_id":"4.A.2.a.4","element_name":"Analyzing Data or Information","scale_id":"IM","source_release":"31.0"},
 {"occ_code":"15-2051","attribute_id":"onet31:work_activity:4.A.2.b.1:IM","attribute_value":"3","evidence_state":"observed","element_id":"4.A.2.b.1","element_name":"Making Decisions and Solving Problems","scale_id":"IM","source_release":"31.0"},
 {"occ_code":"15-2051","attribute_id":"onet31:work_activity:4.A.2.b.2:IM","attribute_value":"","evidence_state":"suppressed","element_id":"4.A.2.b.2","element_name":"Thinking Creatively","scale_id":"IM","source_release":"31.0"},
 {"occ_code":"15-1252","attribute_id":"onet31:work_activity:4.A.2.a.4:IM","attribute_value":"3","evidence_state":"observed","element_id":"4.A.2.a.4","element_name":"Analyzing Data or Information","scale_id":"IM","source_release":"31.0"},
 {"occ_code":"15-1252","attribute_id":"onet31:work_activity:4.A.2.b.1:IM","attribute_value":"5","evidence_state":"observed","element_id":"4.A.2.b.1","element_name":"Making Decisions and Solving Problems","scale_id":"IM","source_release":"31.0"},
 {"occ_code":"15-1252","attribute_id":"onet31:work_activity:4.A.2.b.2:IM","attribute_value":"5","evidence_state":"observed","element_id":"4.A.2.b.2","element_name":"Thinking Creatively","scale_id":"IM","source_release":"31.0"}
]
def pref(pid,aid,importance=1):return {"preference_id":pid,"attribute_id":aid,"operator":"higher_preferred","importance":importance,"priority_explicit":True,"scale_min":1,"scale_max":5}
C={"career__soc_codes":"15-2051 | 15-1252","career__soc_count":"2"}

class CareerPreferenceServiceTests(unittest.TestCase):
 def test_pathway_alignment_and_coverage_stay_separate(self):
  prefs=[pref("analysis","onet31:work_activity:4.A.2.a.4:IM"),pref("creative","onet31:work_activity:4.A.2.b.2:IM")]
  r=build(C,prefs,ATTRS);self.assertEqual(r["status"],"observed");self.assertEqual(r["pathway_count"],2);self.assertEqual(r["observed_pathway_count"],2)
  by={x["soc_code"]:x for x in r["pathways"]};self.assertAlmostEqual(by["15-2051"]["alignment_score"],1.0);self.assertAlmostEqual(by["15-2051"]["coverage_rate"],.5);self.assertAlmostEqual(by["15-1252"]["alignment_score"],.75);self.assertAlmostEqual(by["15-1252"]["coverage_rate"],1)
  self.assertAlmostEqual(r["score_summary"]["median"],.875)
 def test_missing_or_suppressed_attribute_never_becomes_zero_alignment(self):
  r=build(C,[pref("creative","onet31:work_activity:4.A.2.b.2:IM")],ATTRS);by={x["soc_code"]:x for x in r["pathways"]};self.assertIsNone(by["15-2051"]["alignment_score"]);self.assertEqual(by["15-2051"]["coverage_rate"],0);self.assertEqual(by["15-2051"]["preferences"][0]["evidence_state"],"suppressed")
 def test_no_explicit_preferences_is_not_a_default_profile(self):
  r=build(C,[],ATTRS);self.assertEqual(r["status"],"no_explicit_preferences");self.assertIsNone(r["score_summary"]["median"])
 def test_unapproved_attribute_operator_or_scale_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"not in the approved"):validate_preferences([pref("x","invented")],ATTRS)
  p=pref("x","onet31:work_activity:4.A.2.a.4:IM");p["operator"]="lower_preferred"
  with self.assertRaisesRegex(ValueError,"operator"):validate_preferences([p],ATTRS)
  p=pref("x","onet31:work_activity:4.A.2.a.4:IM");p["scale_max"]=100
  with self.assertRaisesRegex(ValueError,"scale"):validate_preferences([p],ATTRS)
 def test_approved_but_unloaded_attribute_fails_closed(self):
  p=pref("creative","onet31:work_activity:4.A.2.b.2:IM")
  with self.assertRaisesRegex(ValueError,"not loaded"):validate_preferences([p],[x for x in ATTRS if x["attribute_id"]!=p["attribute_id"]])
if __name__=="__main__":unittest.main()
