#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from affordability_outcomes_product_adapter import normalize,attach_field_to_programs
class AffordabilityTests(unittest.TestCase):
 def test_institution_cost_concepts_remain_separate(self):
  r=normalize([{"UNITID":"1","tuition_in_state":"5000","cost_of_attendance":"20000","net_price":"9000","median_debt":"12000"}],"institution")[0];self.assertEqual(r["tuition_in_state"],"5000");self.assertEqual(r["cost_of_attendance"],"20000");self.assertEqual(r["net_price"],"9000");self.assertEqual(r["median_debt"],"12000")
 def test_missing_is_not_zero(self):
  r=normalize([{"UNITID":"1","net_price":""}],"institution")[0];self.assertEqual(r["net_price"],"");self.assertEqual(r["net_price__state"],"missing")
 def test_field_outcomes_require_exact_identity(self):
  fields=normalize([{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors","median_earnings":"80000"}],"field_of_study");programs=[{"UNITID":"1","program_id":"P1","cip_code":"11.0101","credential_level":"Bachelors"},{"UNITID":"1","program_id":"P2","cip_code":"11.0101","credential_level":"Associates"}];r=attach_field_to_programs(programs,fields);self.assertEqual(r[0]["field_outcomes_coverage"],"observed");self.assertEqual(r[1]["field_outcomes_coverage"],"unknown")
 def test_same_title_cannot_override_cip_identity(self):
  fields=normalize([{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors","median_earnings":"80000"}],"field_of_study");programs=[{"UNITID":"1","program_id":"P1","program_name":"Computer Science","cip_code":"52.0201","credential_level":"Bachelors"}];self.assertEqual(attach_field_to_programs(programs,fields)[0]["field_outcomes_coverage"],"unknown")
 def test_duplicate_field_identity_fails(self):
  rows=[{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors"},{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors"}]
  with self.assertRaises(ValueError):normalize(rows,"field_of_study")
if __name__=="__main__":unittest.main()
