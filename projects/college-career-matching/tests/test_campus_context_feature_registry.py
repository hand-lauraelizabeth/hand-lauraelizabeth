#!/usr/bin/env python3
from __future__ import annotations
import csv,subprocess,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
REG=P/"config/campus_context_feature_registry.v1.csv"

def read(path):
 with Path(path).open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def write(path,rows):
 cols=list(rows[0])
 with Path(path).open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)

class CampusFeatureRegistryTests(unittest.TestCase):
 def test_registry_has_one_comparison_feature_per_soft_dimension(self):
  rows=read(REG);comparison=[r for r in rows if r["role"]=="comparison"]
  expected={"transit_access_fit","walkability_fit","housing_context_fit","accessibility_evidence_fit"}
  self.assertEqual({r["dimension"] for r in comparison},expected)
  self.assertTrue(all(sum(x["dimension"]==d and x["role"]=="comparison" for x in rows)==1 for d in expected))
 def test_context_fields_are_not_scoring_signals(self):
  rows=read(REG);by={r["feature_id"]:r for r in rows}
  self.assertEqual(by["campus_transit_stop_count_800m"]["role"],"context");self.assertEqual(by["campus_transit_stop_count_800m"]["direction"],"none")
  self.assertEqual(by["campus_housing_capacity"]["role"],"context");self.assertEqual(by["campus_housing_capacity"]["direction"],"none")
 def test_registry_passes_real_feature_registry_validator(self):
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);features=[{"candidate_id":"A","campus__transit_stop_distance_m":"100","campus__transit_stop_count_800m":"4","campus__walkability_index":"12","campus__housing_choice_state":"choice_available","campus__housing_capacity":"500","campus__disability_services_evidence_available":"true"}]
   write(d/"features.csv",features)
   p=subprocess.run([sys.executable,str(P/"recommendation_feature_registry.py"),"--features",str(d/"features.csv"),"--registry",str(REG),"--out-dir",str(d/"out")],text=True,capture_output=True)
   self.assertEqual(p.returncode,0,p.stderr)
   lineage=read(d/"out/recommendation_feature_lineage.csv");self.assertEqual(len(lineage),6)

if __name__=="__main__":unittest.main()
