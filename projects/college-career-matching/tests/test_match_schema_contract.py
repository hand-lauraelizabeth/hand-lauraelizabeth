#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from match_service_adapter import match
REQ=json.loads((P/'schemas/match_request.schema.json').read_text());RES=json.loads((P/'schemas/match_response.schema.json').read_text());DETAIL=json.loads((P/'schemas/candidate_detail_response.schema.json').read_text());COMPARE=json.loads((P/'schemas/compare_response.schema.json').read_text())
def q():return {'schema_version':'1.0','decision_mode':'broad_exploration','constraints':[],'preferences':[],'career_preferences':[],'geography':{'school_location_semantics':'no_preference','selected_states':[],'work_market_semantics':'selected_market','intended_work_market':{'market_id':'35620','market_type':'OEWS_MSA'}},'page':1,'page_size':20}
def c():return {'candidate_id':'1:P1','UNITID':'1','institution_name':'Alpha','program_id':'P1','program_name':'CS','cip_code':'11.0101','credential_level':'Bachelors','state':'NY','career__soc_count':'1','career__soc_codes':'15-1252'}
class SchemaContractTests(unittest.TestCase):
 def test_request_schema_has_structured_work_market(self):
  g=REQ['properties']['geography']['properties'];self.assertIn('work_market_semantics',g);self.assertEqual(g['intended_work_market']['type'],['object','null']);self.assertEqual(set(g['intended_work_market']['required']),{'market_id','market_type'})
 def test_request_schema_exposes_campus_context_preference_dimensions(self):
  dims=set(REQ["properties"]["preferences"]["items"]["properties"]["dimension"]["enum"]);self.assertTrue({"transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"}.issubset(dims))
 def test_request_page_size_matches_service_limit(self):self.assertEqual(REQ['properties']['page_size']['maximum'],100)
 def test_response_schema_defines_explicit_production_authorization_boolean(self):
  self.assertIn("ordering",RES["properties"]);ordering=RES["properties"]["ordering"];self.assertEqual(ordering["properties"]["production_authorized"]["type"],"boolean")
  item=RES["properties"]["results"]["items"];self.assertIn("recommendation",item["properties"]);self.assertEqual(item["properties"]["recommendation"]["properties"]["production_authorized"]["type"],"boolean")
 def test_response_requires_pagination_and_labor(self):
  self.assertIn('pagination',RES['required']);self.assertIn('ordering',RES['required']);item=RES['properties']['results']['items'];self.assertIn('labor_market',item['required']);self.assertIn('career_pathways',item['required']);self.assertIn('recommendation',item['required'])
 def test_candidate_detail_schema_keeps_evidence_families_and_provenance_explicit(self):
  self.assertTrue({"affordability","aid_context","program_outcomes","transfer","career","labor_market","freshness","unknowns"}.issubset(DETAIL["required"]))
  evidence=DETAIL["$defs"]["evidence"];self.assertTrue({"value","evidence_state","source_id","source_vintage"}.issubset(evidence["required"]))
  self.assertIn("accreditation",DETAIL["properties"]["institution"]["required"])
 def test_compare_schema_requires_no_winner_and_missing_not_zero_semantics(self):
  self.assertTrue({"candidate_ids","candidates","comparison_dimensions","semantic_rules"}.issubset(COMPARE["required"]))
  rules=COMPARE["properties"]["semantic_rules"];self.assertEqual(rules["properties"]["no_automatic_winner"]["const"],True);self.assertEqual(rules["properties"]["missing_is_not_zero"]["const"],True)
  self.assertIn("aid_reporting_is_not_individual_award",rules["required"]);self.assertIn("accreditation_absence_is_unknown_not_unaccredited",rules["required"])
 def test_service_emits_explicit_unranked_ordering_by_default(self):
  r=match(q(),[c()],"D","M",generated_at_utc="2026-10-05T00:00:00Z");self.assertEqual(r["ordering"]["mode"],"deterministic_unranked");self.assertEqual(r["results"][0]["recommendation"]["status"],"not_ranked");self.assertFalse(r["results"][0]["recommendation"]["production_authorized"])
 def test_service_can_propagate_explicit_authorization_without_changing_default(self):
  r=match(q(),[c()],"D","M",production_authorized=True);self.assertTrue(r["ordering"]["production_authorized"]);self.assertTrue(r["results"][0]["recommendation"]["production_authorized"])
 def test_service_response_has_schema_required_top_level_fields(self):
  r=match(q(),[c()],'D','M',generated_at_utc='2026-10-05T00:00:00Z');self.assertFalse(set(RES['required'])-set(r))
 def test_service_result_has_schema_required_fields(self):
  r=match(q(),[c()],'D','M',generated_at_utc='2026-10-05T00:00:00Z')['results'][0];required=set(RES['properties']['results']['items']['required']);self.assertFalse(required-set(r))
 def test_request_id_matches_schema_pattern_shape(self):
  rid=match(q(),[c()],'D','M',generated_at_utc='2026-10-05T00:00:00Z')['request_id'];self.assertTrue(rid.startswith('req_'));self.assertEqual(len(rid),24);int(rid[4:],16)
if __name__=='__main__':unittest.main()
