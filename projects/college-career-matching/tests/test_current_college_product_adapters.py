#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from current_college_backbone_adapter import build as backbone
from accreditation_product_adapter import build as accreditation
from product_snapshot_builder import build as product
class CurrentCollegeTests(unittest.TestCase):
 def test_exact_unitid_program_join(self):
  inst=[{"UNITID":"100","institution_name":"Alpha","state":"NY","city":"A"}];prog=[{"UNITID":"100","program_id":"P1","program_name":"Biology","cip_code":"26.0101","credential_level":"Bachelors"}]
  rows,unresolved=backbone(inst,prog);self.assertEqual(len(rows),1);self.assertEqual(unresolved,[]);self.assertEqual(rows[0]["cip_code"],"26.0101")
 def test_unmatched_program_is_review_not_fuzzy_join(self):
  inst=[{"UNITID":"100","institution_name":"Alpha","state":"NY"}];prog=[{"UNITID":"999","program_id":"P1","program_name":"Alpha Biology","cip_code":"26.0101","credential_level":"Bachelors"}]
  rows,unresolved=backbone(inst,prog);self.assertEqual(rows,[]);self.assertEqual(unresolved[0]["reason"],"program_unitid_not_in_institution_universe")
 def test_accreditation_preserves_multiple_evidence_records(self):
  rows=accreditation([{"UNITID":"100","agency_name":"Agency A","accreditation_status":"Accredited","source_record_id":"1"},{"UNITID":"100","agency_name":"Agency B","accreditation_status":"Accredited","source_record_id":"2"}]);self.assertEqual(rows[0]["record_count"],"2");self.assertIn("Agency A",rows[0]["agency_names"]);self.assertIn("Agency B",rows[0]["agency_names"])
 def test_accreditation_absence_remains_product_coverage_gap(self):
  base=[{"UNITID":"100","institution_name":"Alpha","program_id":"P1","program_name":"Biology","cip_code":"26.0101","credential_level":"Bachelors","state":"NY"}];r=product(base,accreditation=[])[0];self.assertEqual(r["coverage__accreditation"],"0");self.assertFalse(any(k.startswith("accreditation__") for k in r))
if __name__=="__main__":unittest.main()
