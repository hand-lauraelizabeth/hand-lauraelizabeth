#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from onet_career_attribute_registry import load_registry,by_question
from onet_work_activity_preference_adapter import normalize

class OnetCareerGovernanceTests(unittest.TestCase):
 def test_reviewed_registry_uses_three_distinct_work_activities(self):
  r=load_registry();self.assertEqual(r["source"]["release"],"31.0");self.assertEqual(r["source"]["scale_id"],"IM");self.assertEqual((r["source"]["scale_min"],r["source"]["scale_max"]),(1,5))
  q=by_question();self.assertEqual(q["career_analysis"]["element_id"],"4.A.2.a.4");self.assertEqual(q["career_problem_solving"]["element_id"],"4.A.2.b.1");self.assertEqual(q["career_creativity"]["element_id"],"4.A.2.b.2")
  self.assertTrue(all(x["operator"]=="higher_preferred" and x["review_status"]=="approved" for x in r["attributes"]))
 def test_adapter_keeps_only_base_soc_reviewed_importance_rows(self):
  rows=[
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.a.4","scale_id":"IM","scale_name":"Importance","data_value":"4.5","date_updated":"2026-08-01"},
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.a.4","scale_id":"LV","scale_name":"Level","data_value":"6"},
   {"onetsoc_code":"15-2051.01","element_id":"4.A.2.a.4","scale_id":"IM","scale_name":"Importance","data_value":"5"},
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.b.1","scale_id":"IM","scale_name":"Importance","data_value":"4.2"},
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.b.2","scale_id":"IM","scale_name":"Importance","data_value":"3.8"},
   {"onetsoc_code":"15-2051.00","element_id":"1.A.1.b.2","scale_id":"IM","scale_name":"Importance","data_value":"4.9"}
  ]
  out=normalize(rows);self.assertEqual(len(out),3);self.assertEqual({x["occ_code"] for x in out},{"15-2051"});self.assertEqual({x["element_id"] for x in out},{"4.A.2.a.4","4.A.2.b.1","4.A.2.b.2"});self.assertTrue(all(x["scale_id"]=="IM" for x in out))
 def test_suppressed_and_not_relevant_do_not_become_numeric_mismatch(self):
  rows=[
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.a.4","scale_id":"IM","data_value":"4.5","recommend_suppress":"Y"},
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.b.1","scale_id":"IM","data_value":"4.2","not_relevant":"Y"},
   {"onetsoc_code":"15-2051.00","element_id":"4.A.2.b.2","scale_id":"IM","data_value":""}
  ]
  out=normalize(rows);self.assertEqual({x["evidence_state"] for x in out},{"suppressed","not_relevant","missing"});self.assertTrue(all(x["attribute_value"]=="" for x in out))
 def test_out_of_scale_value_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"outside governed scale"):normalize([{"onetsoc_code":"15-2051.00","element_id":"4.A.2.a.4","scale_id":"IM","data_value":"5.1"}])
 def test_duplicate_base_soc_attribute_fails_closed(self):
  row={"onetsoc_code":"15-2051.00","element_id":"4.A.2.a.4","scale_id":"IM","data_value":"4"}
  with self.assertRaisesRegex(ValueError,"duplicate base-SOC"):normalize([row,row])
if __name__=="__main__":unittest.main()
