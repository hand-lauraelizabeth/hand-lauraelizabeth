#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from interface_options_builder import build

def row(unitid,pid,name,state="NY",cip="11.0101",cred="Bachelors",online="",setting="",housing="",required=""):
 return {"UNITID":unitid,"institution_name":"Fictional "+unitid,"program_id":pid,"program_name":name,"cip_code":cip,"cip_title":"Synthetic Field "+cip,"credential_level":cred,"state":state,"city":"Test City","online_available":online,"campus__locale_category":setting,"campus__housing_available":housing,"campus__housing_required_all_ftft":required}
class OptionsTests(unittest.TestCase):
 def test_options_derive_from_snapshot(self):
  x=build([row("U1","P1","Computing",online="true"),row("U2","P1","Computing",state="NJ",cred="Associates")],"SYN-1")
  self.assertEqual(x["counts"]["institutions"],2);self.assertEqual(x["counts"]["institution_programs"],2);self.assertEqual({z["value"] for z in x["states"]},{"NY","NJ"});self.assertEqual(len(x["programs"]),2)
 def test_cip_fields_derive_from_active_snapshot_titles(self):
  x=build([row("U1","P1","Computing",cip="11.0101"),row("U2","P2","Biology",cip="26.0101")],"SYN-1");by={z["value"]:z["label"] for z in x["cip_fields"]};self.assertEqual(by["11.0101"],"Synthetic Field 11.0101");self.assertEqual(by["26.0101"],"Synthetic Field 26.0101")
 def test_same_program_id_at_different_institutions_stays_distinct(self):
  x=build([row("U1","P1","Biology"),row("U2","P1","Biology")],"SYN-1");self.assertEqual({p["value"] for p in x["programs"]},{"U1:P1","U2:P1"})
 def test_duplicate_identity_fails(self):
  with self.assertRaises(ValueError):build([row("U1","P1","A"),row("U1","P1","B")],"SYN-1")
 def test_missing_optional_online_evidence_not_negative(self):
  x=build([row("U1","P1","A",online="")],"SYN-1");self.assertEqual(x["modalities"],[])
 def test_campus_and_affordability_options_are_additive(self):
  x=build([row("U1","P1","A",setting="city",housing="1",required="0"),row("U2","P2","B",setting="rural",housing="0",required="0")],"SYN-1");self.assertEqual({z["value"] for z in x["campus_settings"]},{"city","rural"});self.assertTrue(any(z["value"]=="choice" and z["available"] for z in x["housing"]));self.assertEqual([z["value"] for z in x["affordability"]["income_bands"]],["overall","0_30","30_48","48_75","75_110","110_plus"])
 def test_data_version_propagates(self):
  self.assertEqual(build([row("U1","P1","A")],"IPEDS-TEST")["data_version"],"IPEDS-TEST")
if __name__=="__main__":unittest.main()
