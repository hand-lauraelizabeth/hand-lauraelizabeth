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
 def test_options_publish_constraint_capabilities(self):
  r=options(S,"D1");self.assertIn("state",r["constraint_capabilities"]["fields"]);self.assertIn("finance__net_price",r["constraint_capabilities"]["fields"])
 def test_unknown_constraint_field_fails(self):
  with self.assertRaises(ValueError):validate_constraint({"field":"mystery_score","operator":"gte"})
 def test_operator_is_field_specific(self):
  with self.assertRaises(ValueError):validate_constraint({"field":"state","operator":"gte"})
 def test_match_request_rejects_unregistered_field(self):
  req={"schema_version":"1.0","decision_mode":"broad_exploration","preferences":[],"constraints":[{"constraint_id":"x","field":"mystery_score","operator":"gte","value":1,"unknown_policy":"keep_visible"}]}
  with self.assertRaises(ValueError):validate_request(req)
 def test_net_price_constraint_is_explicit_concept(self):
  validate_constraint({"field":"finance__net_price","operator":"lte"})
if __name__=="__main__":unittest.main()
