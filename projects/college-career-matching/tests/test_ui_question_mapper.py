#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from ui_question_mapper import map_answers,validate_definitions
from match_service_adapter import validate_request
DEFS=json.loads((PROJECT/"ui/question_definitions.v1.json").read_text())
OPTIONS={"data_version":"D1","options":{"states":[{"value":"NY","label":"NY"}],"credential_levels":[{"value":"Bachelors","label":"Bachelors"}],"campus_settings":[{"value":"City","label":"City"},{"value":"Rural","label":"Rural"}],"cip_fields":[{"value":"11.0101","label":"Computer and Information Sciences, General"},{"value":"26.0101","label":"Biology/Biological Sciences, General"}]}}
class MapperTests(unittest.TestCase):
 def test_definitions_are_constraint_registry_valid(self):self.assertTrue(validate_definitions(DEFS))
 def test_skipped_questions_do_not_become_preferences(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","affordability_priority":3});self.assertEqual(len(r["preferences"]),1);validate_request(r)
 def test_academic_field_comes_from_active_cip_options(self):
  r=map_answers(DEFS,{"decision_mode":"college_program_first","academic_fields":["11.0101"]},OPTIONS);self.assertEqual(r["constraints"][0]["field"],"cip_code");self.assertEqual(r["constraints"][0]["value"],["11.0101"])
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"college_program_first","academic_fields":["99.9999"]},OPTIONS)
 def test_school_location_and_work_market_stay_separate(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","school_states":["NY"],"work_market_semantics":"national"},OPTIONS);self.assertEqual(r["geography"]["selected_states"],["NY"]);self.assertEqual(r["geography"]["work_market_semantics"],"national");self.assertIsNone(r["geography"]["intended_work_market"])
 def test_selected_market_is_structured(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","work_market_semantics":"selected_market","work_market":{"market_id":"35620","market_type":"OEWS_MSA"}});self.assertEqual(r["geography"]["intended_work_market"]["market_id"],"35620")
 def test_hidden_selected_market_rejected(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"career_first","work_market_semantics":"national","work_market":{"market_id":"35620","market_type":"OEWS_MSA"}})
 def test_online_no_does_not_create_false_hard_constraint(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"not_required"})["constraints"],[])
 def test_online_required_creates_explicit_constraint(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"required"})["constraints"][0]["value"],True)
 def test_net_price_defaults_to_explicit_overall_average(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","net_price_ceiling":20000});self.assertEqual(r["constraints"][0]["field"],"finance__net_price_overall");validate_request(r)
 def test_income_band_selects_matching_net_price_field(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","net_price_income_band":"48_75","net_price_ceiling":18000});self.assertEqual(r["constraints"][0]["field"],"finance__net_price_income_48_75");self.assertEqual(r["constraints"][0]["value"],18000)
 def test_income_band_selector_alone_is_not_a_constraint(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","net_price_income_band":"0_30"});self.assertEqual(r["constraints"],[])
 def test_invalid_income_band_fails_closed(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","net_price_income_band":"made_up","net_price_ceiling":10000})
 def test_campus_setting_comes_from_active_options(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","campus_settings":["City"]},OPTIONS);self.assertEqual(r["constraints"][0]["field"],"campus__locale_category")
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","campus_settings":["RemoteMoon"]},OPTIONS)
 def test_housing_choice_expands_into_two_explicit_constraints(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","housing_requirement":"choice"});self.assertEqual(len(r["constraints"]),2);self.assertEqual({x["field"] for x in r["constraints"]},{"campus__housing_available","campus__housing_required_all_ftft"});self.assertEqual({x["value"] for x in r["constraints"]},{True,False})
 def test_aid_and_disability_requirements_are_evidence_filters(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","institutional_aid_required":"required","work_study_required":"required","state_local_aid_required":"required","disability_services_evidence_required":"required"});self.assertEqual({x["field"] for x in r["constraints"]},{"finance__institutional_grant_evidence","finance__work_study_evidence","finance__state_local_grant_evidence","campus__disability_services_evidence_available"})
 def test_campus_context_soft_priorities_remain_independent(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","transit_access_priority":4,"walkability_priority":3,"housing_choice_priority":2,"disability_services_priority":5});dims={x["dimension"] for x in r["preferences"]};self.assertEqual(dims,{"transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"});self.assertTrue(all(x["priority_explicit"] for x in r["preferences"]));validate_request(r)
 def test_active_options_reject_stale_state(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","school_states":["ZZ"]},OPTIONS)
 def test_options_version_propagates(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration"},OPTIONS)["data_version"],"D1")
 def test_unreviewed_career_attribute_mapping_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"career attribute mapping review is still required"):map_answers(DEFS,{"decision_mode":"career_first","career_analysis":4})
 def test_skipped_unreviewed_career_questions_do_not_block_career_first(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","work_market_semantics":"national"});self.assertEqual(r["career_preferences"],[]);self.assertEqual(r["geography"]["work_market_semantics"],"national")
 def test_transfer_question_rejected_outside_transfer_modes(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"career_first","transfer_source":"FIC-1"})
 def test_transfer_source_creates_context_not_guarantee(self):
  r=map_answers(DEFS,{"decision_mode":"transfer","transfer_source":"FIC-1","transfer_priority":4});self.assertFalse(r["transfer_context"]["target_program_required"])
 def test_unknown_question_fails_closed(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","mystery":"x"})
if __name__=="__main__":unittest.main()
