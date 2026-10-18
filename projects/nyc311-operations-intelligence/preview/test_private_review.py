"""Contract tests for the private review viewer's fail-closed browser gate."""
import pathlib, re, unittest
HTML=pathlib.Path(__file__).with_name("private-review.html").read_text(encoding="utf-8")
class PrivateViewerContract(unittest.TestCase):
 def test_no_remote_upload_or_script(self):
  self.assertNotRegex(HTML,r'<script[^>]+src=')
  self.assertNotIn('fetch(',HTML)
  self.assertNotIn('XMLHttpRequest',HTML)
 def test_no_publication_or_live_claim(self):
  self.assertIn('Not published',HTML)
  self.assertIn('Demonstration data only',HTML)
  self.assertIn('publication_authorized!==false',HTML)
 def test_complementary_suppression(self):
  self.assertIn('r.requests-c<10',HTML)
  self.assertIn('r.closure_count_suppressed===true',HTML)
  self.assertIn('c===null',HTML)
 def test_accessible_text_only(self):
  self.assertIn('aria-live="polite"',HTML)
  self.assertIn('td.textContent=value',HTML)
  self.assertIn('scope="col"',HTML)
 def test_source_and_period_gate(self):
  self.assertIn('source_sha256',HTML)
  self.assertIn('2026-09',HTML)
  self.assertIn('display_minimum_cell_count<10',HTML)
if __name__=="__main__":unittest.main()
