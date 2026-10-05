#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from labor_evidence_service_adapter import build_for_candidate
from match_service_adapter import match
C={"candidate_id":"1:P1","UNITID":"1","institution_name":"Alpha","program_id":"P1","program_name":"CS","cip_code":"11.0101","credential_level":"Bachelors","state":"NY","career__soc_count":"1","career__soc_codes":"15-1252"}
CUR=[{"UNITID":"1","program_id":"P1","soc_code":"15-1252","market_id":"35620","market_type":"OEWS_MSA","employment":"1000","employment_state":"observed","median_wage":"90000","wage_state":"observed","source_vintage":"May 2025"}]
PROJ=[{"UNITID":"1","program_id":"P1","soc_code":"15-1252","projection_geography":"national","base_year":"2025","projection_year":"2035","employment_change_pct":"15","annual_openings":"10000","source_vintage":"2025-2035"}]
class LaborServiceTests(unittest.TestCase):
 def test_selected_market_filters_current_evidence(self):
  x=build_for_candidate(C,CUR,PROJ,{"market_id":"35620","market_type":"OEWS_MSA"});self.assertEqual(x["selected_work_market"]["evidence_state"],"observed");self.assertEqual(x["selected_work_market"]["soc_evidence"][0]["median_wage"],"90000")
 def test_wrong_market_does_not_fallback(self):
  x=build_for_candidate(C,CUR,PROJ,{"market_id":"99999","market_type":"OEWS_MSA"});self.assertEqual(x["selected_work_market"]["evidence_state"],"unavailable");self.assertEqual(x["selected_work_market"]["soc_evidence"],[]);self.assertEqual(x["long_term_outlook"]["evidence_state"],"observed")
 def test_match_response_keeps_current_and_projection_separate(self):
  req={"schema_version":"1.0","decision_mode":"career_first","constraints":[],"preferences":[],"geography":{"intended_work_market":{"market_id":"35620","market_type":"OEWS_MSA"}}};r=match(req,[C],"D1","M1",CUR,PROJ)["results"][0];self.assertEqual(r["labor_market"]["selected_work_market"]["market_id"],"35620");self.assertEqual(r["labor_market"]["long_term_outlook"]["soc_evidence"][0]["projection_year"],"2035")
 def test_career_soc_pathways_surface_in_result(self):
  req={"schema_version":"1.0","decision_mode":"career_first","constraints":[],"preferences":[]};r=match(req,[C],"D1","M1")["results"][0];self.assertEqual(r["career_pathways"]["soc_codes"],["15-1252"])
if __name__=="__main__":unittest.main()
