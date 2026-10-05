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
 def test_cross_document_keyness_and_similarity_are_explicit(self):
  for token in ['id="keyMin"',"function signedLogLikelihood(","function keynessAgainstRemainder(","Document-to-document lexical similarity","Distinctive terms by document","signed log-likelihood G²","document_similarity","document_keyness","corpus_analysis:publicCorpusComparison()"]:
   self.assertIn(token,HTML)
 def test_document_focus_visualization_and_document_kwic_are_present(self):
  for token in ['id="focusDoc"','id="vizMetric"',"function syncCorpusSelectors(","function renderMetricBars(","function kwicTarget()","similarity-meter","focus_document:","document_chart:"]:
   self.assertIn(token,HTML)
 def test_corpus_document_management_and_reference_keyness_are_present(self):
  for token in ['id="keyRef"','id="docManager"',"let docSeq=0","function manageDocument(","function renderDocumentManager(","function keynessAgainstReference(","reference_document:reference","keyness_reference:","version:\"3.5\""]:
   self.assertIn(token,HTML)
 def test_corpus_refreshes_before_document_scoped_concordance(self):
  self.assertIn("lastCompare=two;renderCorpus();renderKwic();",HTML)
 def test_custom_reference_sets_and_source_free_setup_are_present(self):
  for token in ['value="custom"',"const customRefIds=new Set()","function customReference(","reference_id:'custom'",'id="saveCorpusSetup"','id="loadCorpusSetup"',"function buildCorpusSetup()","contains_source_text:false","function containsSourcePayload(","Corpus setup must not contain source text","version:\"3.5\""]:
   self.assertIn(token,HTML)
 def test_setup_restore_is_metadata_only_and_pending_safe(self):
  for token in ["name:doc.name","size:Number(doc.size||0)","last_modified:Number(doc.lastModified||0)","pendingCorpusConfig?applyCorpusSetup","Saved corpus setup without source text."]:
   self.assertIn(token,HTML)
 def test_corpus_organization_and_keyness_presentation_are_structured(self):
  for token in ['id="refAll"','id="refClear"','id="refSummary"',"corpus-group-head","role-badge focus","role-badge reference",'class="keyness-table"',"Target document","Reference mode: remainder"]:
   self.assertIn(token,HTML)
 def test_exports_do_not_include_source_text(self):
  self.assertIn("Source text itself is not included in the file.",HTML)
  self.assertIn("text-lens-tables.csv",HTML)
  m=re.search(r"function docDescriptor\(doc,source,order\)\{return\{([^}]*)\}\}",HTML)
  self.assertIsNotNone(m);self.assertNotIn("text",m.group(1).lower());self.assertIn("name:doc.name",m.group(1));self.assertIn("size:Number(doc.size||0)",m.group(1))
  self.assertIn("contains_source_text:false",HTML);self.assertIn("Corpus setup must not contain source text or content fields",HTML)
 def test_javascript_syntax(self):
  node=shutil.which("node");self.assertIsNotNone(node,"Node.js is required for Text Lens syntax validation")
  parts=re.findall(r"<script>(.*?)</script>",HTML,re.S);self.assertEqual(len(parts),1)
  with tempfile.NamedTemporaryFile("w",suffix=".js",encoding="utf-8") as f:
   f.write(parts[0]);f.flush();p=subprocess.run([node,"--check",f.name],text=True,capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":unittest.main()
