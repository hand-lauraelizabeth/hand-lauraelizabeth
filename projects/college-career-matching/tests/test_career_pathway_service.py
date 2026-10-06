#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from career_pathway_service import career_summary,pathway_rows,representative_rows

class CareerPathwayServiceTests(unittest.TestCase):
 def test_structured_pathways_preserve_title_and_soc_identity(self):
  c={"career__soc_count":"2","career__soc_codes":"15-1211 | 15-2051","career__pathways_json":json.dumps([{"soc_code":"15-1211","occupation_title":"Computer Systems Analysts"},{"soc_code":"15-2051","occupation_title":"Data Scientists"}])}
  r=career_summary(c);self.assertEqual(r["pathway_count"],2);self.assertEqual(r["pathways"][0]["occupation_title"],"Computer Systems Analysts");self.assertEqual(r["soc_codes"],["15-1211","15-2051"])
 def test_code_only_fallback_never_invents_title(self):
  r=career_summary({"career__soc_codes":"15-1252"});self.assertEqual(r["pathways"],[{"soc_code":"15-1252","occupation_title":None}]);self.assertEqual(r["representative_pathways"],[])
 def test_structured_and_code_fallback_dedupe_by_soc(self):
  c={"career__pathways_json":json.dumps([{"soc_code":"15-1252","occupation_title":"Software Developers"}]),"career__soc_codes":"15-1252 | 15-2051"}
  r=pathway_rows(c);self.assertEqual([x["soc_code"] for x in r],["15-1252","15-2051"])
 def test_representative_pathways_are_separate(self):
  c={"career__soc_codes":"15-1252 | 15-2051","career__representative_pathways_json":json.dumps([{"soc_code":"15-2051","occupation_title":"Data Scientists"}])}
  self.assertEqual(representative_rows(c),[{"soc_code":"15-2051","occupation_title":"Data Scientists"}])
if __name__=="__main__":unittest.main()
