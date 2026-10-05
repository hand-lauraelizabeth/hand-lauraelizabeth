#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from affordability_outcomes_product_adapter import normalize,attach_field_to_programs
class AffordabilityTests(unittest.TestCase):
 def test_institution_cost_concepts_remain_separate(self):
  r=normalize([{"UNITID":"1","tuition_in_state":"5000","cost_of_attendance":"20000","net_price":"9000","median_debt":"12000"}],"institution")[0];self.assertEqual(r["tuition_in_state"],"5000");self.assertEqual(r["cost_of_attendance"],"20000");self.assertEqual(r["net_price"],"9000");self.assertEqual(r["median_debt"],"12000")
 def test_income_band_net_prices_remain_distinct(self):
  r=normalize([{"UNITID":"1","net_price_overall":"12000","net_price_income_0_30":"7000","net_price_income_110_plus":"21000"}],"institution")[0];self.assertEqual(r["net_price_overall"],"12000");self.assertEqual(r["net_price_income_0_30"],"7000");self.assertEqual(r["net_price_income_110_plus"],"21000")
 def test_aid_evidence_is_not_collapsed_into_cost(self):
  r=normalize([{"UNITID":"1","institutional_grant_share":"0.45","work_study_share":"","state_local_grant_share":"0.20"}],"institution")[0];self.assertEqual(r["institutional_grant_evidence"],"true");self.assertEqual(r["work_study_evidence"],"");self.assertEqual(r["state_local_grant_evidence"],"true")
 def test_measure_level_provenance_is_preserved(self):
  r=normalize([{"UNITID":"1","net_price_overall":"12000","net_price_overall__source_id":"ipeds_cost_2024","net_price_overall__source_vintage":"2024-25","institutional_grant_share":"0.4","institutional_grant_share__source_id":"ipeds_sfa_2023_24","institutional_grant_share__source_vintage":"2023-24"}],"institution")[0];self.assertEqual(r["net_price_overall__source_id"],"ipeds_cost_2024");self.assertEqual(r["institutional_grant_share__source_id"],"ipeds_sfa_2023_24");self.assertNotEqual(r["net_price_overall__source_vintage"],r["institutional_grant_share__source_vintage"])
 def test_missing_aid_evidence_flag_stays_unknown(self):
  r=normalize([{"UNITID":"1","institutional_grant_share":"","institutional_grant_share__state":"not_published"}],"institution")[0];self.assertEqual(r["institutional_grant_evidence"],"")
 def test_missing_is_not_zero(self):
  r=normalize([{"UNITID":"1","net_price":""}],"institution")[0];self.assertEqual(r["net_price"],"");self.assertEqual(r["net_price__state"],"missing")
 def test_source_suppression_is_preserved(self):
  r=normalize([{"UNITID":"1","net_price":"","net_price__state":"suppressed"}],"institution")[0];self.assertEqual(r["net_price__state"],"suppressed");self.assertEqual(r["net_price"],"")
 def test_blank_without_state_is_not_inferred_suppressed(self):self.assertEqual(normalize([{"UNITID":"1","median_debt":""}],"institution")[0]["median_debt__state"],"missing")
 def test_invalid_evidence_state_fails_closed(self):
  with self.assertRaises(ValueError):normalize([{"UNITID":"1","net_price":"","net_price__state":"secret"}],"institution")
 def test_zero_remains_observed(self):self.assertEqual(normalize([{"UNITID":"1","net_price":"0"}],"institution")[0]["net_price__state"],"observed")
 def test_field_outcomes_require_exact_identity(self):
  fields=normalize([{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors","median_earnings":"80000"}],"field_of_study");programs=[{"UNITID":"1","program_id":"P1","cip_code":"11.0101","credential_level":"Bachelors"},{"UNITID":"1","program_id":"P2","cip_code":"11.0101","credential_level":"Associates"}];r=attach_field_to_programs(programs,fields);self.assertEqual(r[0]["field_outcomes_coverage"],"observed");self.assertEqual(r[1]["field_outcomes_coverage"],"unknown")
 def test_same_title_cannot_override_cip_identity(self):
  fields=normalize([{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors","median_earnings":"80000"}],"field_of_study");programs=[{"UNITID":"1","program_id":"P1","program_name":"Computer Science","cip_code":"52.0201","credential_level":"Bachelors"}];self.assertEqual(attach_field_to_programs(programs,fields)[0]["field_outcomes_coverage"],"unknown")
 def test_duplicate_field_identity_fails(self):
  rows=[{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors"},{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors"}]
  with self.assertRaises(ValueError):normalize(rows,"field_of_study")
 def test_blank_program_id_fails_attachment(self):
  fields=normalize([{"UNITID":"1","cip_code":"11.0101","credential_level":"Bachelors"}],"field_of_study")
  with self.assertRaises(ValueError):attach_field_to_programs([{"UNITID":"1","program_id":"","cip_code":"11.0101","credential_level":"Bachelors"}],fields)
if __name__=="__main__":unittest.main()
