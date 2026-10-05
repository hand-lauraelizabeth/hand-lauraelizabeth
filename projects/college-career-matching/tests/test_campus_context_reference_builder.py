#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from campus_context_reference_builder import build

def row(uid,pid,transit="300",tstate="observed",walk="12",wstate="observed"):
 return {"UNITID":uid,"program_id":pid,"campus__transit_stop_distance_m":transit,"campus__transit_stop_distance_m__state":tstate,"campus__transit_stop_distance_m__source_id":"bts_national_transit_map","campus__transit_stop_distance_m__source_vintage":"2026-Q3","campus__walkability_index":walk,"campus__walkability_index__state":wstate,"campus__walkability_index__source_id":"epa_walkability_2021","campus__walkability_index__source_vintage":"2021"}

class CampusReferenceBuilderTests(unittest.TestCase):
 def test_program_rows_collapse_to_one_institution_reference_row(self):
  out,qa=build([row("1","P1"),row("1","P2"),row("2","P1","700","observed","8","observed")],"D1")
  self.assertEqual(len(out),2);self.assertEqual(qa["snapshot_candidate_rows"],3);self.assertEqual(qa["reference_institution_rows"],2)
 def test_program_count_does_not_weight_reference_population(self):
  out,_=build([row("1","P1"),row("1","P2"),row("1","P3"),row("2","P1")],"D1")
  self.assertEqual([r["UNITID"] for r in out],["1","2"])
 def test_inconsistent_institution_context_fails_closed(self):
  with self.assertRaisesRegex(ValueError,"inconsistent institution-level campus context"):
   build([row("1","P1",transit="300"),row("1","P2",transit="900")],"D1")
 def test_missing_evidence_is_retained_not_dropped(self):
  out,qa=build([row("1","P1",transit="",tstate="not_published",walk="",wstate="missing")],"D1")
  self.assertEqual(len(out),1);self.assertEqual(out[0]["campus__transit_stop_distance_m__state"],"not_published");self.assertEqual(qa["transit_observed_institutions"],0)
 def test_blank_data_version_fails(self):
  with self.assertRaises(ValueError):build([row("1","P1")],"")
 def test_blank_unitid_fails(self):
  with self.assertRaises(ValueError):build([row("","P1")],"D1")

if __name__=="__main__":unittest.main()
