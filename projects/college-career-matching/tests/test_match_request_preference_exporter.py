#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from match_request_preference_exporter import export_preferences

def req():
 return {"schema_version":"1.0","decision_mode":"broad_exploration","constraints":[],"preferences":[{"preference_id":"transit","dimension":"transit_access_fit","importance":4,"priority_explicit":True,"source_question_id":"transit_access_priority"},{"preference_id":"walk","dimension":"walkability_fit","importance":2,"priority_explicit":True,"source_question_id":"walkability_priority"}],"career_preferences":[],"page":1,"page_size":20}

class RequestPreferenceExporterTests(unittest.TestCase):
 def test_explicit_dimensions_export_without_reweighting(self):
  dims,career,qa=export_preferences(req());self.assertEqual([x["importance"] for x in dims],[4,2]);self.assertEqual({x["dimension"] for x in dims},{"transit_access_fit","walkability_fit"});self.assertEqual(career,[]);self.assertEqual(qa["dimension_preference_count"],2)
 def test_no_preferences_stays_empty(self):
  r=req();r["preferences"]=[];dims,career,_=export_preferences(r);self.assertEqual(dims,[]);self.assertEqual(career,[])
 def test_invalid_request_fails_before_export(self):
  r=req();r["preferences"][0]["priority_explicit"]=False
  with self.assertRaises(ValueError):export_preferences(r)
 def test_constraints_are_not_exported_as_preferences(self):
  r=req();r["constraints"]=[{"constraint_id":"state","field":"state","operator":"eq","value":"NY","unknown_policy":"keep_visible"}];dims,_,_=export_preferences(r);self.assertEqual(len(dims),2)

if __name__=="__main__":unittest.main()
