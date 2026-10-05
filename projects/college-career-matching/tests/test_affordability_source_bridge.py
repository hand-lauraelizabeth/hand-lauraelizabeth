#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from affordability_source_bridge import build

class AffordabilitySourceBridgeTests(unittest.TestCase):
 def test_cost_precedes_scorecard_with_measure_provenance(self):
  rows,qa=build(
   [{"UNITID":"1"}],
   cost=[{"UNITID":"1","cost_of_attendance":"30000","net_price_overall":"12000","net_price_income_0_30":"7000"}],
   aid=[{"UNITID":"1","institutional_grant_share":"0.50","work_study_share":"0.10","state_local_grant_share":"0.20"}],
   scorecard=[{"UNITID":"1","cost_of_attendance":"31000","net_price_overall":"13000","net_price_income_48_75":"15000"}],
   directory_vintage="2025",cost_vintage="2024-25",aid_vintage="2023-24",scorecard_vintage="2026-06-10")
  r=rows[0]
  self.assertEqual(r["cost_of_attendance"],"30000")
  self.assertEqual(r["cost_of_attendance__source_id"],"ipeds_cost_2024")
  self.assertEqual(r["net_price_income_48_75"],"15000")
  self.assertEqual(r["net_price_income_48_75__source_id"],"college_scorecard")
  self.assertEqual(r["institutional_grant_share__source_id"],"ipeds_sfa_2023_24")
  self.assertEqual(qa["scorecard_fallback_counts"]["net_price_income_48_75"],1)
 def test_overall_net_price_compatibility_alias_preserves_provenance(self):
  rows,_=build([{"UNITID":"1"}],cost=[{"UNITID":"1","net_price_overall":"11000"}],directory_vintage="2025",cost_vintage="2024-25")
  r=rows[0];self.assertEqual(r["net_price"],"11000");self.assertEqual(r["net_price__source_id"],"ipeds_cost_2024")
 def test_income_bands_stay_separate(self):
  rows,_=build([{"UNITID":"1"}],cost=[{"UNITID":"1","net_price_income_0_30":"6000","net_price_income_110_plus":"22000"}],directory_vintage="2025",cost_vintage="2024-25")
  r=rows[0];self.assertEqual(r["net_price_income_0_30"],"6000");self.assertEqual(r["net_price_income_110_plus"],"22000")
 def test_older_source_orphans_are_reported_not_attached(self):
  rows,qa=build([{"UNITID":"1"}],aid=[{"UNITID":"999","institutional_grant_share":"0.9"}],directory_vintage="2025",aid_vintage="2023-24")
  self.assertEqual(rows,[]);self.assertEqual(qa["orphan_source_unitids"]["aid"],["999"])
 def test_missing_aid_is_not_false_or_zero(self):
  rows,_=build([{"UNITID":"1"}],cost=[{"UNITID":"1","net_price_overall":"10000"}],directory_vintage="2025",cost_vintage="2024-25")
  r=rows[0];self.assertEqual(r["institutional_grant_share"],"");self.assertEqual(r["institutional_grant_share__state"],"missing");self.assertEqual(r["institutional_grant_evidence"],"")
 def test_duplicate_identity_fails(self):
  with self.assertRaisesRegex(ValueError,"duplicate UNITID"):
   build([{"UNITID":"1"}],scorecard=[{"UNITID":"1"},{"UNITID":"1"}],directory_vintage="2025")

if __name__=="__main__":unittest.main()
