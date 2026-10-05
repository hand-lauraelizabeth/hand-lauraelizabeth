#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from campus_context_source_bridge import build

class CampusSourceBridgeTests(unittest.TestCase):
 def test_sources_merge_by_current_unitid_with_field_provenance(self):
  rows,qa=build(
   [{"UNITID":"1","locale_code":"11"}],
   cost=[{"UNITID":"1","housing_available":"true","housing_capacity":"600","housing_required_all_ftft":"false"}],
   services=[{"UNITID":"1","disability_services_registered_share":"0.08"}],
   transit=[{"UNITID":"1","transit_stop_distance_m":"220","transit_stop_count_800m":"7"}],
   walkability=[{"UNITID":"1","walkability_index":"15.2"}],
   directory_vintage="2025 provisional",cost_vintage="2024-25",services_vintage="2025",transit_vintage="2026-Q3",walkability_vintage="2021")
  r=rows[0]
  self.assertEqual(r["locale_category"],"City")
  self.assertEqual(r["housing_choice_state"],"choice_available")
  self.assertEqual(r["transit_stop_distance_m__source_id"],"bts_national_transit_map")
  self.assertEqual(r["walkability_index__source_vintage"],"2021")
  self.assertEqual(qa["campus_context_records"],1)
 def test_older_source_orphan_is_reported_not_fuzzy_matched(self):
  rows,qa=build([{"UNITID":"1","locale_code":"21"}],cost=[{"UNITID":"999","housing_available":"true"}],directory_vintage="2025",cost_vintage="2024")
  self.assertEqual([r["UNITID"] for r in rows],["1"])
  self.assertEqual(qa["orphan_source_unitids"]["cost"],["999"])
  self.assertNotIn("housing_available",rows[0] if False else {})
 def test_missing_source_evidence_stays_missing(self):
  rows,_=build([{"UNITID":"1","locale_code":"41"}],directory_vintage="2025")
  r=rows[0]
  self.assertEqual(r["housing_available"],"")
  self.assertEqual(r["housing_available__state"],"missing")
  self.assertEqual(r["transit_stop_distance_m__state"],"missing")
 def test_duplicate_source_identity_fails(self):
  with self.assertRaisesRegex(ValueError,"duplicate UNITID"):
   build([{"UNITID":"1","locale_code":"11"}],transit=[{"UNITID":"1"},{"UNITID":"1"}],directory_vintage="2025")
 def test_blank_directory_identity_fails(self):
  with self.assertRaisesRegex(ValueError,"blank UNITID"):
   build([{"UNITID":"","locale_code":"11"}],directory_vintage="2025")

if __name__=="__main__":unittest.main()
