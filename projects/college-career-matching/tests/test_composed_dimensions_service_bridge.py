#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from composed_dimensions_service_bridge import build

def candidate(cid):
 return {"candidate_id":cid,"UNITID":"U"+cid,"institution_name":"Fictional "+cid,"program_id":"P1","program_name":"Synthetic","cip_code":"99.9999"}

class DimensionServiceBridgeTests(unittest.TestCase):
 def test_dimension_fields_materialize_without_score(self):
  rows,qa=build([candidate("A")],[{"candidate_id":"A","dimension":"transit_access_fit","dimension_value":"0.75","dimension_coverage_rate":"1","dimension_status":"complete"}]);r=rows[0]
  self.assertEqual(r["dimension__transit_access_fit"],0.75);self.assertEqual(r["coverage__transit_access_fit"],1.0);self.assertEqual(r["state__transit_access_fit"],"complete");self.assertFalse(any("score" in k or "rank" in k for k in r));self.assertEqual(qa["candidate_count"],1)
 def test_missing_dimension_value_stays_blank(self):
  rows,_=build([candidate("A")],[{"candidate_id":"A","dimension":"accessibility_evidence_fit","dimension_value":"","dimension_coverage_rate":"0","dimension_status":"partial_blocked"}]);self.assertEqual(rows[0]["dimension__accessibility_evidence_fit"],"");self.assertEqual(rows[0]["coverage__accessibility_evidence_fit"],0.0)
 def test_orphan_dimension_fails(self):
  with self.assertRaises(ValueError):build([candidate("A")],[{"candidate_id":"B","dimension":"walkability_fit","dimension_value":".5","dimension_coverage_rate":"1","dimension_status":"complete"}])
 def test_duplicate_candidate_dimension_fails(self):
  d={"candidate_id":"A","dimension":"walkability_fit","dimension_value":".5","dimension_coverage_rate":"1","dimension_status":"complete"}
  with self.assertRaises(ValueError):build([candidate("A")],[d,d])
 def test_out_of_range_value_fails(self):
  with self.assertRaises(ValueError):build([candidate("A")],[{"candidate_id":"A","dimension":"walkability_fit","dimension_value":"1.2","dimension_coverage_rate":"1","dimension_status":"complete"}])

if __name__=="__main__":unittest.main()
