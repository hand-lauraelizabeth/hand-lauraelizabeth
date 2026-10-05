#!/usr/bin/env python3
from __future__ import annotations
import re,shutil,subprocess,tempfile,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]
HTML=(P/"text-lens.html").read_text(encoding="utf-8")

class TextLensContractTests(unittest.TestCase):
 def test_privacy_and_local_file_ingestion_are_explicit(self):
  self.assertIn("analysis stays in your browser",HTML)
  self.assertIn('id="fileA"',HTML);self.assertIn('id="fileB"',HTML)
  self.assertIn("files stay in this browser",HTML)
  self.assertIn("source_files",HTML)
 def test_corpus_concordance_and_collocations_are_present(self):
  for token in ['id="kwic"',"function kwic(","function collocations(","Collocations by PMI","PMI can over-emphasize rare pairs","collocation_minimum"]:
   self.assertIn(token,HTML)
 def test_length_aware_lexical_diversity_is_present(self):
  for token in ["function mattr(","MATTR-50","function herdan(","Herdan's C","mattr_50","herdan_c"]:
   self.assertIn(token,HTML)
 def test_document_aware_corpus_mode_preserves_file_identity(self):
  for token in ["const sourceDocs=",'id="corpusres"',"function renderCorpus(","document_profiles:{","document_summary","Manual edits detected · file identity cleared"]:
   self.assertIn(token,HTML)
 def test_exports_do_not_include_source_text(self):
  self.assertIn("Source text itself is not included in the file.",HTML)
  self.assertIn("text-lens-tables.csv",HTML)
  self.assertNotIn("source_text:",HTML)
 def test_javascript_syntax(self):
  node=shutil.which("node");self.assertIsNotNone(node,"Node.js is required for Text Lens syntax validation")
  parts=re.findall(r"<script>(.*?)</script>",HTML,re.S);self.assertEqual(len(parts),1)
  with tempfile.NamedTemporaryFile("w",suffix=".js",encoding="utf-8") as f:
   f.write(parts[0]);f.flush();p=subprocess.run([node,"--check",f.name],text=True,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":unittest.main()
