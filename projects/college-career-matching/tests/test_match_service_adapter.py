#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from match_service_adapter import match,validate_request
def request(mode="broad_exploration"):
 return {"schema_version":"1.0","decision_mode":mode,"constraints":[{"constraint_id":"state","field":"state","operator":"eq","value":"NY","unknown_policy":"keep_visible"}],"preferences":[{"preference_id":"cost","dimension":"affordability","importance":3,"priority_explicit":True}],"career_preferences":[],"page":1,"page_size":20}
def candidate(cid,state="NY"):
 return {"candidate_id":cid,"UNITID":"FIC-"+cid,"institution_name":"Fictional College "+cid,"program_id":"P1","program_name":"Synthetic Studies","cip_code":"99.9999","state":state,"dimension__affordability":.8,"coverage__affordability":1,"state__affordability":"complete","pathway_count":2,"source_freshness":[{"source_family":"synthetic","vintage":"TEST"}]}
class MatchServiceTests(unittest.TestCase):
 def test_match_filters_failed_constraint_and_returns_program_grain(self):
  r=match(request(),[candidate("A"),candidate("B","NJ")],"SYN-DATA-1","SYN-MODEL-1");self.assertEqual(r["result_count"],1);self.assertEqual(r["results"][0]["candidate_id"],"A");self.assertEqual(r["results"][0]["program"]["cip_code"],"99.9999")
 def test_keep_visible_unknown_is_not_silently_excluded(self):
  c=candidate("A");c["state"]="";r=match(request(),[c],"D","M");self.assertEqual(r["results"][0]["eligibility"]["status"],"eligible_with_unknown")
 def test_exclude_unknown_removes_candidate(self):
  q=request();q["constraints"][0]["unknown_policy"]="exclude_unknown";c=candidate("A");c["state"]="";self.assertEqual(match(q,[c],"D","M")["result_count"],0)
 def test_boolean_constraint_matches_normalized_csv_text(self):
  q=request();q["constraints"]=[{"constraint_id":"housing","field":"campus__housing_available","operator":"eq","value":True,"unknown_policy":"keep_visible"}];c=candidate("A");c["campus__housing_available"]="true";self.assertEqual(match(q,[c],"D","M")["result_count"],1);c["campus__housing_available"]="false";self.assertEqual(match(q,[c],"D","M")["result_count"],0)
 def test_boolean_false_constraint_matches_normalized_csv_text(self):
  q=request();q["constraints"]=[{"constraint_id":"housing_req","field":"campus__housing_required_all_ftft","operator":"eq","value":False,"unknown_policy":"keep_visible"}];c=candidate("A");c["campus__housing_required_all_ftft"]="false";self.assertEqual(match(q,[c],"D","M")["result_count"],1)
 def test_skipped_preferences_need_no_placeholder(self):q=request();q["preferences"]=[];validate_request(q);self.assertEqual(match(q,[candidate("A")],"D","M")["result_count"],1)
 def test_transfer_mode_does_not_create_transfer_claim(self):
  q=request("transfer");q["transfer_context"]={"source_institution_id":"FIC-SOURCE","source_system":"synthetic","completed_course_ids":[],"target_program_required":False};self.assertIsNone(match(q,[candidate("A")],"D","M")["results"][0]["transfer"])
 def test_only_explicit_preferences_allowed(self):
  q=request();q["preferences"][0]["priority_explicit"]=False
  with self.assertRaises(ValueError):validate_request(q)
 def test_duplicate_candidate_id_fails(self):
  with self.assertRaises(ValueError):match(request(),[candidate("A"),candidate("A")],"D","M")
 def test_selected_work_market_requires_structured_identity(self):
  q=request("career_first");q["geography"]={"work_market_semantics":"selected_market","intended_work_market":None}
  with self.assertRaisesRegex(ValueError,"selected_market requires"):validate_request(q)
 def test_nonselected_work_market_cannot_carry_selected_market_identity(self):
  q=request("career_first");q["geography"]={"work_market_semantics":"national","intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}}
  with self.assertRaisesRegex(ValueError,"only valid with selected_market"):validate_request(q)
 def test_legacy_structured_market_without_semantics_remains_valid(self):
  q=request("career_first");q["geography"]={"intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}};validate_request(q)
 def test_explicit_labor_priorities_emit_context_without_numeric_tradeoffs(self):
  q=request("career_first");q["constraints"]=[];q["preferences"]=[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":1,"priority_explicit":True},{"preference_id":"long_term_outlook_priority","dimension":"long_term_outlook","importance":1,"priority_explicit":True}];q["geography"]={"work_market_semantics":"selected_market","intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}}
  cur=[{"UNITID":"FIC-A","program_id":"P1","soc_code":"15-1252","occupation_title":"Software Developers","market_id":"35620","market_type":"OEWS_MSA","market_label":"Metro Example","employment":"1000","employment_state":"observed","median_wage":"90000","wage_state":"observed","source_vintage":"May 2025"}];proj=[{"UNITID":"FIC-A","program_id":"P1","soc_code":"15-1252","occupation_title":"Software Developers","projection_geography":"national","base_year":"2025","projection_year":"2035","employment_change_pct":"12","annual_openings":"1000","source_vintage":"2025-2035"}]
  ex=match(q,[candidate("A")],"D","M",cur,proj)["results"][0]["explanation"];self.assertEqual({x["code"] for x in ex["context"]},{"CURRENT_LABOR_PRIORITY_EVIDENCE_AVAILABLE","LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_AVAILABLE"});self.assertEqual(ex["tradeoffs"],[]);self.assertEqual(ex["unknowns"],[]);self.assertTrue(all(x["evidence_ids"] for x in ex["context"]))
  current=next(x for x in ex["context"] if x["code"]=="CURRENT_LABOR_PRIORITY_EVIDENCE_AVAILABLE")["supporting_evidence"][0];self.assertEqual(current["soc_code"],"15-1252");self.assertEqual(current["occupation_title"],"Software Developers");self.assertEqual(current["geography"]["market_label"],"Metro Example");self.assertEqual(current["source_vintage"],"May 2025");self.assertEqual(current["measure_states"],{"employment":"observed","median_wage":"observed"});self.assertEqual(current["measures"]["median_wage"],"90000")
  future=next(x for x in ex["context"] if x["code"]=="LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_AVAILABLE")["supporting_evidence"][0];self.assertEqual(future["geography"]["projection_geography"],"national");self.assertEqual(future["source_vintage"],"2025-2035");self.assertEqual(future["measures"]["projection_year"],"2035")
 def test_unavailable_priority_evidence_is_unknown_not_negative_tradeoff(self):
  q=request("career_first");q["constraints"]=[];q["preferences"]=[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":1,"priority_explicit":True},{"preference_id":"long_term_outlook_priority","dimension":"long_term_outlook","importance":1,"priority_explicit":True}];q["geography"]={"work_market_semantics":"selected_market","intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}}
  ex=match(q,[candidate("A")],"D","M",[],[])["results"][0]["explanation"];self.assertEqual({x["code"] for x in ex["unknowns"]},{"CURRENT_LABOR_PRIORITY_EVIDENCE_UNAVAILABLE","LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_UNAVAILABLE"});self.assertEqual(ex["tradeoffs"],[]);self.assertEqual(ex["context"],[])
  current=next(x for x in ex["unknowns"] if x["code"]=="CURRENT_LABOR_PRIORITY_EVIDENCE_UNAVAILABLE")["supporting_evidence"][0];self.assertEqual(current["evidence_state"],"unavailable");self.assertEqual(current["geography"]["market_id"],"35620");self.assertIsNone(current["soc_code"])
  future=next(x for x in ex["unknowns"] if x["code"]=="LONG_TERM_OUTLOOK_PRIORITY_EVIDENCE_UNAVAILABLE")["supporting_evidence"][0];self.assertEqual(future["evidence_state"],"unavailable");self.assertIsNone(future["source_vintage"])
 def test_current_labor_priority_without_selected_market_is_limitation_not_score(self):
  q=request("career_first");q["constraints"]=[];q["preferences"]=[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":1,"priority_explicit":True}];q["geography"]={"work_market_semantics":"national","intended_work_market":None}
  ex=match(q,[candidate("A")],"D","M")["results"][0]["explanation"];self.assertEqual(ex["unknowns"][0]["code"],"CURRENT_LABOR_PRIORITY_MARKET_NOT_EVALUATED");self.assertEqual(ex["tradeoffs"],[]);trace=ex["unknowns"][0]["supporting_evidence"][0];self.assertEqual(trace["evidence_state"],"not_requested");self.assertEqual(trace["geography"]["work_market_semantics"],"national")
 def test_labor_trace_ids_and_order_are_deterministic(self):
  q=request("career_first");q["constraints"]=[];q["preferences"]=[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":1,"priority_explicit":True}];q["geography"]={"work_market_semantics":"selected_market","intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}}
  rows=[{"UNITID":"FIC-A","program_id":"P1","soc_code":"15-2051","occupation_title":"Data Scientists","market_id":"35620","market_type":"OEWS_MSA","employment":"200","employment_state":"observed","median_wage":"95000","wage_state":"observed","source_vintage":"May 2025"},{"UNITID":"FIC-A","program_id":"P1","soc_code":"15-1211","occupation_title":"Computer Systems Analysts","market_id":"35620","market_type":"OEWS_MSA","employment":"300","employment_state":"observed","median_wage":"85000","wage_state":"observed","source_vintage":"May 2025"}]
  a=match(q,[candidate("A")],"D","M",rows,[])["results"][0]["explanation"]["context"][0];b=match(q,[candidate("A")],"D","M",list(reversed(rows)),[])["results"][0]["explanation"]["context"][0]
  ids_a=[x["evidence_id"] for x in a["supporting_evidence"]];ids_b=[x["evidence_id"] for x in b["supporting_evidence"]];self.assertEqual(ids_a,ids_b);self.assertEqual(ids_a,["labor:current_labor_market:soc:15-1211:1","labor:current_labor_market:soc:15-2051:2"]);self.assertTrue(set(ids_a).issubset(set(a["evidence_ids"])))
 def test_nonpositive_labor_priority_does_not_emit_priority_explanation(self):
  q=request("career_first");q["constraints"]=[];q["preferences"]=[{"preference_id":"current_labor_market_priority","dimension":"current_labor_market","importance":0,"priority_explicit":True}];ex=match(q,[candidate("A")],"D","M")["results"][0]["explanation"];self.assertEqual(ex["context"],[]);self.assertEqual(ex["unknowns"],[])
 def test_pagination_is_validated(self):
  for page,size in [(0,20),(1,0),(1,101)]:
   q=request();q["page"]=page;q["page_size"]=size
   with self.assertRaises(ValueError):validate_request(q)
 def test_pagination_metadata(self):
  q=request();q["page_size"]=1;r=match(q,[candidate("A"),candidate("B")],"D","M");self.assertEqual(r["pagination"]["total_pages"],2);self.assertTrue(r["pagination"]["has_next"]);self.assertEqual(len(r["results"]),1)
 def test_pagination_slices_stable_service_order_and_preserves_total_count(self):
  q=request();q["page_size"]=2;q["page"]=2
  rows=[candidate(x) for x in ["E","A","D","B","C"]]
  r=match(q,rows,"D","M")
  self.assertEqual(r["result_count"],5);self.assertEqual(r["pagination"],{"page":2,"page_size":2,"total_pages":3,"has_next":True,"has_previous":True})
  self.assertEqual([x["candidate_id"] for x in r["results"]],["C","D"])
 def test_production_authorization_is_explicit_and_defaults_false(self):
  a=match(request(),[candidate("A")],"D","M");b=match(request(),[candidate("A")],"D","M",production_authorized=True)
  self.assertFalse(a["ordering"]["production_authorized"]);self.assertFalse(a["results"][0]["recommendation"]["production_authorized"])
  self.assertTrue(b["ordering"]["production_authorized"]);self.assertTrue(b["results"][0]["recommendation"]["production_authorized"])
 def test_request_id_is_deterministic_for_same_request_and_versions(self):
  q=request();a=match(q,[candidate("A")],"D","M",generated_at_utc="2026-01-01T00:00:00Z");b=match(q,[candidate("A")],"D","M",generated_at_utc="2026-02-01T00:00:00Z");self.assertEqual(a["request_id"],b["request_id"]);self.assertNotEqual(a["generated_at_utc"],b["generated_at_utc"])
if __name__=="__main__":unittest.main()
