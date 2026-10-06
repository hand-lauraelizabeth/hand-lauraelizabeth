#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest,json
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from candidate_detail_service import candidate_detail
from compare_service_adapter import compare

def c(uid,pid,name):return {"candidate_id":f"{uid}:{pid}","UNITID":uid,"institution_name":name,"program_id":pid,"program_name":"CS","cip_code":"11.0101","credential_level":"Bachelors","state":"NY","finance__net_price":"12000","finance__net_price__state":"observed","program_outcomes__median_earnings":"70000","program_outcomes__median_earnings__state":"observed","coverage__program_outcomes":"1","coverage__transfer":"0","coverage__career_pathways":"1","career__soc_count":"1","career__soc_codes":"15-1252"}
class DetailCompareTests(unittest.TestCase):
 def test_detail_keeps_institution_and_program_outcomes_separate(self):
  x=candidate_detail(c("1","P1","Alpha"),data_version="D1");self.assertEqual(x["affordability"]["net_price"]["value"],"12000");self.assertEqual(x["program_outcomes"]["median_earnings"]["value"],"70000")
 def test_missing_is_explicit_not_zero(self):
  x=candidate_detail(c("1","P1","Alpha"));self.assertEqual(x["affordability"]["cost_of_attendance"]["evidence_state"],"missing");self.assertIsNone(x["affordability"]["cost_of_attendance"]["value"])
 def test_detail_preserves_field_source_and_vintage(self):
  row=c("1","P1","Alpha");row.update({"finance__net_price__source_id":"ipeds_cost_2024","finance__net_price__source_vintage":"2024","finance__institutional_grant_share":"0.4","finance__institutional_grant_share__state":"observed","finance__institutional_grant_share__source_id":"ipeds_sfa_2023_24","finance__institutional_grant_share__source_vintage":"2023-24"})
  x=candidate_detail(row,data_version="D1")
  self.assertEqual(x["affordability"]["net_price"]["source_id"],"ipeds_cost_2024");self.assertEqual(x["affordability"]["net_price"]["source_vintage"],"2024")
  self.assertEqual(x["aid_context"]["institutional_grant_share"]["source_id"],"ipeds_sfa_2023_24")
 def test_detail_normalizes_csv_list_evidence(self):
  row=c("1","P1","Alpha");row.update({"coverage__transfer":"1","transfer__evidence_levels":"course_equivalency | program_articulation","transfer__source_systems":"system_a | system_b","source_freshness":"[{\"source_family\":\"synthetic\",\"vintage\":\"TEST\"}]"})
  x=candidate_detail(row,data_version="D1")
  self.assertEqual(x["transfer"]["evidence_levels"],["course_equivalency","program_articulation"]);self.assertEqual(x["transfer"]["source_systems"],["system_a","system_b"])
  self.assertEqual(x["freshness"]["source_freshness"][0]["source_family"],"synthetic")
 def test_detail_exposes_structured_related_pathways_without_inventing_representatives(self):
  row=c("1","P1","Alpha");row["career__pathways_json"]=json.dumps([{"soc_code":"15-1252","occupation_title":"Software Developers"}]);x=candidate_detail(row,data_version="D1");self.assertEqual(x["career"]["pathway_count"],1);self.assertEqual(x["career"]["pathways"][0]["occupation_title"],"Software Developers");self.assertEqual(x["career"]["representative_pathways"],[])
 def test_accreditation_absence_remains_coverage_unknown_not_negative(self):
  x=candidate_detail(c("1","P1","Alpha"));self.assertFalse(x["institution"]["accreditation"]["covered"]);self.assertEqual(x["institution"]["accreditation"]["statuses"],[])
 def test_compare_requires_multiple_unique_candidates(self):
  with self.assertRaises(ValueError):compare([c("1","P1","Alpha")])
  with self.assertRaises(ValueError):compare([c("1","P1","Alpha"),c("1","P1","Alpha")])
 def test_compare_does_not_declare_winner(self):
  r=compare([c("1","P1","Alpha"),c("2","P2","Beta")],data_version="D1");self.assertTrue(r["semantic_rules"]["no_automatic_winner"]);self.assertNotIn("winner",r)
 def test_compare_exposes_all_governed_evidence_families(self):
  r=compare([c("1","P1","Alpha"),c("2","P2","Beta")],data_version="D1")
  ids={x["id"] for x in r["comparison_dimensions"]}
  self.assertTrue({"affordability","aid_context","program_outcomes","transfer","career","current_labor","long_term_outlook","accreditation","freshness","unknowns"}.issubset(ids));career=next(x for x in r["comparison_dimensions"] if x["id"]=="career");self.assertEqual(career["fields"],["pathway_count","pathways","representative_pathways"])
  self.assertTrue(r["semantic_rules"]["aid_reporting_is_not_individual_award"]);self.assertTrue(r["semantic_rules"]["accreditation_absence_is_unknown_not_unaccredited"])
 def test_compare_preserves_candidate_order(self):
  r=compare([c("2","P2","Beta"),c("1","P1","Alpha")]);self.assertEqual(r["candidate_ids"],["2:P2","1:P1"])
if __name__=="__main__":unittest.main()
