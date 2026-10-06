#!/usr/bin/env python3
from __future__ import annotations
import base64,json,re,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];sys.path.insert(0,str(P))
from wordpress_explorer_embed import build,root_fragment

SOURCE=(P/"public-explorer.html").read_text(encoding="utf-8")
CLIENT=(P/"prototype/service-client.js").read_text(encoding="utf-8")
FIXTURES=json.loads((P/"prototype/contract-fixtures.json").read_text(encoding="utf-8"))

def decoded_app(out):
 m=re.search(r"atob\('([A-Za-z0-9+/=]+)'\)",out)
 if not m:raise AssertionError("WordPress embed base64 application payload missing")
 return base64.b64decode(m.group(1)).decode("utf-8")

class WordPressExplorerEmbedTests(unittest.TestCase):
 def test_embed_is_single_bootstrap_fixture_mode(self):
  out=build(SOURCE,CLIENT,FIXTURES);app=decoded_app(out)
  self.assertEqual(out.count('data-ccx-bootstrap="1"'),1);self.assertEqual(out.count("(async function(){"),0);self.assertEqual(out.count("class MatchingServiceClient"),0)
  self.assertEqual(app.count("(async function(){"),1);self.assertEqual(app.count("class MatchingServiceClient"),1);self.assertEqual(app.count("const INLINE_FIXTURES="),1)
  self.assertNotIn('<script type="module">',out);self.assertNotIn("import {MatchingServiceClient",app)
  self.assertIn('"mode":"fixture"',out);self.assertIn('"production_authorized":false',out)
 def test_dollar_number_literals_do_not_duplicate_module_body(self):
  self.assertRegex(SOURCE,r"\$[0-9]")
  app=decoded_app(build(SOURCE,CLIENT,FIXTURES))
  self.assertEqual(app.count("serviceStatus='request-error'"),1)
  self.assertEqual(app.count("function setInteractive(enabled)"),1)
 def test_root_fragment_is_self_contained_and_divi_whitespace_safe(self):
  root=root_fragment(build(SOURCE,CLIENT,FIXTURES));app=decoded_app(root)
  self.assertTrue(root.startswith('<div id="leh-ccx">'));self.assertIn('data-ccx-bootstrap="1"',root)
  self.assertNotIn("structuredClone(INLINE_FIXTURES)",root);self.assertIn("structuredClone(INLINE_FIXTURES)",app);self.assertEqual(app.count("(async function(){"),1)
  bootstrap=re.search(r'<script data-ccx-bootstrap="1">([\s\S]*?)</script>',root).group(1)
  self.assertNotIn("\n",bootstrap);self.assertIn("TextDecoder",bootstrap);self.assertIn("document.currentScript.after(s);",bootstrap)

if __name__=="__main__":unittest.main()
