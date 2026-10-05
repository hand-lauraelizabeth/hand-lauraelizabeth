#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from campus_context_product_adapter import normalize,income_band_field

class CampusContextTests(unittest.TestCase):
 def test_locale_preserves_detail_and_derives_setting(self):
  r=normalize([{"UNITID":"1","locale_code":"11"}])[0]
  self.assertEqual(r["locale_code"],"11");self.assertEqual(r["setting_group"],"City")
 def test_missing_locale_stays_unknown(self):
  r=normalize([{"UNITID":"1","locale_code":""}])[0]
  self.assertEqual(r["setting_group"],"");self.assertEqual(r["setting_group__state"],"missing")
 def test_invalid_locale_fails_closed(self):
  with self.assertRaises(ValueError):normalize([{"UNITID":"1","locale_code":"99"}])
 def test_false_housing_is_observed_not_missing(self):
  r=normalize([{"UNITID":"1","housing_available":"false"}])[0]
  self.assertEqual(r["housing_available"],"false");self.assertEqual(r["housing_available__state"],"observed");self.assertEqual(r["housing_choice_state"],"no_institutional_housing")
 def test_housing_choice_requires_distinct_requirement_field(self):
  r=normalize([{"UNITID":"1","housing_available":"true","housing_required_all_ftft":"false"}])[0]
  self.assertEqual(r["housing_choice_state"],"choice_available")
 def test_income_band_net_prices_remain_distinct(self):
  r=normalize([{"UNITID":"1","net_price_income_0_30k":"7000","net_price_income_110k_plus":"21000"}])[0]
  self.assertEqual(r[income_band_field("0_30k")],"7000");self.assertEqual(r[income_band_field("110k_plus")],"21000")
 def test_provenance_is_preserved_per_field(self):
  r=normalize([{"UNITID":"1","walkability_index":"12.4","walkability_index__source_id":"epa_sld_v3","walkability_index__source_vintage":"2021"}])[0]
  self.assertEqual(r["walkability_index__source_id"],"epa_sld_v3");self.assertEqual(r["walkability_index__source_vintage"],"2021")
 def test_documented_evidence_flag_is_not_quality_score(self):
  r=normalize([{"UNITID":"1","disability_services_registered_share":"0.08"}])[0]
  self.assertEqual(r["disability_services_evidence_available"],"true")
 def test_source_missing_state_does_not_become_observed(self):
  r=normalize([{"UNITID":"1","transit_stop_distance_m":"","transit_stop_distance_m__state":"not_published"}])[0]
  self.assertEqual(r["transit_stop_distance_m__state"],"not_published")
 def test_duplicate_unitid_fails(self):
  with self.assertRaises(ValueError):normalize([{"UNITID":"1"},{"UNITID":"1"}])

if __name__=="__main__":unittest.main()
