#!/usr/bin/env python3
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from wordpress_explorer_embed import build,root_fragment

SOURCE=(P/"public-explorer.html").read_text(encoding="utf-8")
CLIENT=(P/"prototype/service-client.js").read_text(encoding="utf-8")
FIXTURES=json.loads((P/"prototype/contract-fixtures.json").read_text(encoding="utf-8"))

class WordPressExplorerEmbedTests(unittest.TestCase):
 def test_embed_is_single_initializer_fixture_mode(self):
  out=build(SOURCE,CLIENT,FIXTURES)
  self.assertEqual(out.count("(async function(){"),1);self.assertEqual(out.count("class MatchingServiceClient"),1);self.assertEqual(out.count("const INLINE_FIXTURES="),1)
  self.assertNotIn('<script type="module">',out);self.assertNotIn("import {MatchingServiceClient",out)
  self.assertIn('"mode":"fixture"',out);self.assertIn('"production_authorized":false',out)
 def test_dollar_number_literals_do_not_duplicate_module_body(self):
  self.assertRegex(SOURCE,r"\$[0-9]")
  out=build(SOURCE,CLIENT,FIXTURES)
  self.assertEqual(out.count("serviceStatus='request-error'"),1)
  self.assertEqual(out.count("function setInteractive(enabled)"),1)
 def test_root_fragment_is_self_contained(self):
  root=root_fragment(build(SOURCE,CLIENT,FIXTURES))
  self.assertTrue(root.startswith('<div id="leh-ccx">'));self.assertIn("structuredClone(INLINE_FIXTURES)",root);self.assertEqual(root.count("(async function(){"),1)

if __name__=="__main__":unittest.main()
