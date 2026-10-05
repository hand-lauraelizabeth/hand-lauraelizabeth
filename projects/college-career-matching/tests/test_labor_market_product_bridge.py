#!/usr/bin/env python3
from __future__ import annotations
import sys,unittest
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(PROJECT))
from labor_market_product_bridge import current_local,long_term
P=[{"UNITID":"1","program_id":"P1","soc_code":"15-1252"}]
class LaborBridgeTests(unittest.TestCase):
 def test_current_market_identity_is_preserved(self):
  r=current_local(P,[{"soc_code":"15-1252","market_id":"35620","market_type":"OEWS_MSA","employment":"1000","median_wage":"90000"}])[0];self.assertEqual(r["market_id"],"35620");self.assertEqual(r["market_type"],"OEWS_MSA")
 def test_missing_current_measure_is_not_zero(self):
  r=current_local(P,[{"soc_code":"15-1252","market_id":"35620","market_type":"OEWS_MSA","employment":"","median_wage":""}])[0];self.assertEqual(r["employment"],"");self.assertEqual(r["employment_state"],"missing");self.assertEqual(r["wage_state"],"missing")
 def test_projection_horizon_stays_distinct(self):
  r=long_term(P,[{"soc_code":"15-1252","base_year":"2025","projection_year":"2035","employment_change_pct":"15","annual_openings":"10000"}])[0];self.assertEqual(r["base_year"],"2025");self.assertEqual(r["projection_year"],"2035");self.assertEqual(r["projection_geography"],"national");self.assertNotIn("market_id",r)
 def test_many_to_many_pathways_are_not_averaged(self):
  p=P+[{"UNITID":"1","program_id":"P1","soc_code":"15-1211"}];rows=long_term(p,[{"soc_code":"15-1252","base_year":"2025","projection_year":"2035"},{"soc_code":"15-1211","base_year":"2025","projection_year":"2035"}]);self.assertEqual(len(rows),2);self.assertEqual({r["soc_code"] for r in rows},{"15-1252","15-1211"})
 def test_current_labor_requires_explicit_geography(self):
  with self.assertRaises(ValueError):current_local(P,[{"soc_code":"15-1252","employment":"1000"}])
if __name__=="__main__":unittest.main()
