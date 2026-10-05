#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from match_service_adapter import validate_request
F=json.loads((P/'prototype/contract-fixtures.json').read_text())
class PrototypeContractTests(unittest.TestCase):
 def test_fixture_is_explicitly_synthetic(self):self.assertEqual(F['fixture_status'],'SYNTHETIC_NOT_PRODUCTION_DATA')
 def test_core_responses_are_v1(self):
  for k in ['metadata','options','match','compare']:self.assertEqual(F[k]['schema_version'],'1.0')
 def test_metadata_options_and_match_share_data_version(self):self.assertEqual(F['metadata']['data_version'],F['options']['data_version']);self.assertEqual(F['options']['data_version'],F['match']['data_version'])
 def test_metadata_does_not_claim_production_authorization(self):self.assertFalse(F['metadata']['production_authorized']);self.assertTrue(F['metadata']['semantic_rules']['review_eligibility_is_not_production_authorization'])
 def test_match_results_have_unique_candidate_ids(self):
  ids=[x['candidate_id'] for x in F['match']['results']];self.assertEqual(len(ids),len(set(ids)))
 def test_match_fixture_has_current_service_response_shape(self):
  m=F["match"];self.assertTrue(m["request_id"].startswith("req_"));self.assertEqual(len(m["request_id"]),24);int(m["request_id"][4:],16)
  self.assertIn("pagination",m);self.assertEqual(m["pagination"]["page"],1);self.assertEqual(m["pagination"]["page_size"],100)
  self.assertTrue(all(isinstance(w,dict) and {"code","message"}.issubset(w) for w in m["warnings"]))
  for x in m["results"]:
   for key in ["dimensions","explanation","transfer","source_freshness","recommendation"]:self.assertIn(key,x)
   self.assertEqual(set(x["explanation"]),{"why_it_matches","tradeoffs","unknowns"})
 def test_match_fixture_is_explicitly_unranked_and_not_production_authorized(self):
  self.assertEqual(F["match"]["ordering"]["mode"],"deterministic_unranked");self.assertFalse(F["match"]["ordering"]["production_authorized"])
  for x in F["match"]["results"]:self.assertEqual(x["recommendation"]["status"],"not_ranked");self.assertFalse(x["recommendation"]["production_authorized"])
 def test_current_and_long_term_labor_are_separate(self):
  for x in F['match']['results']:
   self.assertIn('selected_work_market',x['labor_market']);self.assertIn('long_term_outlook',x['labor_market'])
 def test_compare_has_no_winner_semantics(self):self.assertTrue(F['compare']['semantic_rules']['no_automatic_winner']);self.assertNotIn('winner',F['compare'])
 def test_prototype_request_shape_is_service_valid(self):
  r={'schema_version':'1.0','decision_mode':'broad_exploration','constraints':[{'constraint_id':'school_states','field':'state','operator':'in','value':['NY'],'unknown_policy':'keep_visible'}],'preferences':[{'preference_id':'affordability_priority','dimension':'affordability','importance':3,'priority_explicit':True}],'career_preferences':[],'geography':{'school_location_semantics':'selected_places','selected_states':['NY'],'work_market_semantics':'unspecified','intended_work_market':None},'page':1,'page_size':20};validate_request(r)
if __name__=='__main__':unittest.main()
