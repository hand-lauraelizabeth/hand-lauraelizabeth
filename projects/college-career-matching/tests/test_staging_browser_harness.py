#!/usr/bin/env python3
from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from staging_browser_harness import build_harness

class StagingBrowserHarnessTests(unittest.TestCase):
 def test_harness_uses_real_explorer_and_stays_nonproduction(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"staging-browser.html";r=build_harness(out,18865);html=out.read_text(encoding="utf-8")
   self.assertEqual(r["runtime"]["mode"],"staging");self.assertFalse(r["runtime"]["production_authorized"])
   self.assertIn("Synthetic Staging Harness",html);self.assertIn('name="robots" content="noindex,nofollow"',html)
   self.assertIn('"mode":"staging"',html);self.assertIn("MatchingServiceClient",html);self.assertIn("client.match(request,{signal})",html)
   self.assertIn("Synthetic staging mode:",html);self.assertIn("production authorized",html.lower())
 def test_harness_pins_generated_snapshot_hash(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"staging-browser.html";r=build_harness(out,18865)
   manifest=json.loads(Path(r["manifest"]).read_text(encoding="utf-8"))
   self.assertEqual(r["runtime"]["expected_identity"]["snapshot_sha256"],manifest["output_sha256"])
   self.assertEqual(r["runtime"]["expected_identity"]["data_version"],manifest["data_version"])

 def test_harness_can_build_large_pagination_snapshot(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/"staging-browser.html";r=build_harness(out,18865,candidate_count=27)
   manifest=json.loads(Path(r["manifest"]).read_text(encoding="utf-8"))
   self.assertEqual(manifest["candidate_count"],27);self.assertEqual(manifest["institution_count"],27)
   self.assertIn('"mode":"staging"',out.read_text(encoding="utf-8"))

if __name__=="__main__":unittest.main()
