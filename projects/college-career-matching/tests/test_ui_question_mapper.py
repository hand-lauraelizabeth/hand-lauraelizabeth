#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from ui_question_mapper import map_answers,validate_definitions
from match_service_adapter import validate_request
DEFS=json.loads((PROJECT/"ui/question_definitions.v1.json").read_text())
OPTIONS={"data_version":"D1","options":{"states":[{"value":"NY","label":"NY"}],"credential_levels":[{"value":"Bachelors","label":"Bachelors"}]}}
class MapperTests(unittest.TestCase):
 def test_definitions_are_constraint_registry_valid(self):self.assertTrue(validate_definitions(DEFS))
 def test_skipped_questions_do_not_become_preferences(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","affordability_priority":3});self.assertEqual(len(r["preferences"]),1);validate_request(r)
 def test_school_location_and_work_market_stay_separate(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","school_states":["NY"],"work_market_semantics":"national"},OPTIONS);self.assertEqual(r["geography"]["selected_states"],["NY"]);self.assertEqual(r["geography"]["work_market_semantics"],"national");self.assertIsNone(r["geography"]["intended_work_market"])
 def test_selected_market_is_structured(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","work_market_semantics":"selected_market","work_market":{"market_id":"35620","market_type":"OEWS_MSA"}});self.assertEqual(r["geography"]["intended_work_market"]["market_id"],"35620")
 def test_hidden_selected_market_rejected(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"career_first","work_market_semantics":"national","work_market":{"market_id":"35620","market_type":"OEWS_MSA"}})
 def test_online_no_does_not_create_false_hard_constraint(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"not_required"})["constraints"],[])
 def test_online_required_creates_explicit_constraint(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"required"})["constraints"][0]["value"],True)
 def test_net_price_replaces_ambiguous_cost_placeholder(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","net_price_ceiling":20000});self.assertEqual(r["constraints"][0]["field"],"finance__net_price");validate_request(r)
 def test_active_options_reject_stale_state(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","school_states":["ZZ"]},OPTIONS)
 def test_options_version_propagates(self):self.assertEqual(map_answers(DEFS,{"decision_mode":"broad_exploration"},OPTIONS)["data_version"],"D1")
 def test_transfer_question_rejected_outside_transfer_modes(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"career_first","transfer_source":"FIC-1"})
 def test_transfer_source_creates_context_not_guarantee(self):
  r=map_answers(DEFS,{"decision_mode":"transfer","transfer_source":"FIC-1","transfer_priority":4});self.assertFalse(r["transfer_context"]["target_program_required"])
 def test_unknown_question_fails_closed(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","mystery":"x"})
if __name__=="__main__":unittest.main()
