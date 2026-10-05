#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from ui_question_mapper import map_answers
from match_service_adapter import validate_request
DEFS=json.loads((PROJECT/"ui/question_definitions.v1.json").read_text())
class MapperTests(unittest.TestCase):
 def test_skipped_questions_do_not_become_preferences(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","affordability_priority":3})
  self.assertEqual(len(r["preferences"]),1);self.assertEqual(r["preferences"][0]["dimension"],"affordability");validate_request(r)
 def test_school_location_and_work_market_stay_separate(self):
  r=map_answers(DEFS,{"decision_mode":"career_first","school_states":["NY","NJ"],"work_market_semantics":"national"})
  self.assertEqual(r["geography"]["selected_states"],["NY","NJ"]);self.assertEqual(r["geography"]["intended_work_market"],"national");self.assertEqual(r["constraints"][0]["field"],"state")
 def test_online_no_does_not_create_false_hard_constraint(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"not_required"});self.assertEqual(r["constraints"],[])
 def test_online_required_creates_explicit_constraint(self):
  r=map_answers(DEFS,{"decision_mode":"broad_exploration","online_requirement":"required"});self.assertEqual(r["constraints"][0]["value"],True)
 def test_transfer_question_rejected_outside_transfer_modes(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"career_first","transfer_source":"FIC-1"})
 def test_transfer_source_creates_context_not_guarantee(self):
  r=map_answers(DEFS,{"decision_mode":"transfer","transfer_source":"FIC-1","transfer_priority":4});self.assertEqual(r["transfer_context"]["source_institution_id"],"FIC-1");self.assertFalse(r["transfer_context"]["target_program_required"]);self.assertEqual(r["preferences"][0]["dimension"],"transfer_pathway_fit")
 def test_unknown_question_fails_closed(self):
  with self.assertRaises(ValueError):map_answers(DEFS,{"decision_mode":"broad_exploration","mystery":"x"})
if __name__=="__main__":unittest.main()
