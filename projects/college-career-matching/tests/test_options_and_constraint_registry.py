#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from options_service_adapter import options
from constraint_field_registry import validate_constraint
from match_service_adapter import validate_request
S=[{"UNITID":"1","institution_name":"Alpha","program_id":"P1","program_name":"CS","cip_code":"11.0101","credential_level":"Bachelors","state":"NY"}]
class OptionsConstraintTests(unittest.TestCase):
 def test_options_come_from_active_snapshot(self):
  r=options(S,"D1");self.assertEqual(r["data_version"],"D1");self.assertEqual(r["options"]["programs"][0]["value"],"1:P1")
 def test_labor_market_options_derive_only_from_loaded_governed_evidence(self):
  labor=[{"market_id":"35620","market_type":"OEWS_MSA","market_label":"Metro Example"},{"market_id":"35620","market_type":"OEWS_MSA","market_label":"Metro Example"},{"market_id":"12","market_type":"OEWS_STATE","area_title":"State Example"}]
  markets=options(S,"D1",labor)["options"]["labor_markets"];self.assertEqual(len(markets),2);by={x["value"]:x for x in markets};self.assertEqual(by["OEWS_MSA:35620"]["label"],"Metro Example");self.assertEqual(by["OEWS_STATE:12"]["market_id"],"12")
 def test_career_preference_options_are_advertised_only_when_reviewed_evidence_is_loaded(self):
  self.assertEqual(options(S,"D1")["options"]["career_preference_attributes"],[])
  attrs=[{"occ_code":"15-2051","attribute_id":"onet31:work_activity:4.A.2.a.4:IM"}];o=options(S,"D1",career_attributes=attrs)["options"]["career_preference_attributes"];self.assertEqual(len(o),1);self.assertEqual(o[0]["question_id"],"career_analysis");self.assertEqual(o[0]["scale_min"],1);self.assertEqual(o[0]["scale_max"],5)
 def test_options_publish_constraint_capabilities(self):
  r=options(S,"D1");fields=r["constraint_capabilities"]["fields"];self.assertIn("state",fields);self.assertIn("cip_code",fields);self.assertIn("finance__net_price",fields);self.assertIn("finance__net_price_income_0_30",fields);self.assertIn("campus__locale_category",fields);self.assertIn("campus__housing_available",fields)
 def test_unknown_constraint_field_fails(self):
  with self.assertRaises(ValueError):validate_constraint({"field":"mystery_score","operator":"gte"})
 def test_operator_is_field_specific(self):
  with self.assertRaises(ValueError):validate_constraint({"field":"state","operator":"gte"})
 def test_match_request_rejects_unregistered_field(self):
  req={"schema_version":"1.0","decision_mode":"broad_exploration","preferences":[],"constraints":[{"constraint_id":"x","field":"mystery_score","operator":"gte","value":1,"unknown_policy":"keep_visible"}]}
  with self.assertRaises(ValueError):validate_request(req)
 def test_cip_constraint_is_exact_governed_program_classification(self):
  validate_constraint({"field":"cip_code","operator":"in"});validate_constraint({"field":"cip_code","operator":"eq"})
 def test_net_price_constraint_is_explicit_concept(self):
  validate_constraint({"field":"finance__net_price","operator":"lte"});validate_constraint({"field":"finance__net_price_income_48_75","operator":"lte"})
 def test_setting_housing_and_aid_constraints_are_governed(self):
  validate_constraint({"field":"campus__locale_category","operator":"in"});validate_constraint({"field":"campus__housing_available","operator":"eq"});validate_constraint({"field":"finance__institutional_grant_evidence","operator":"eq"})
if __name__=="__main__":unittest.main()
