"""Browser tests for private NYC 311 preview; synthetic fixtures only."""
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright

class ViewerTests(unittest.TestCase):
    def test_private_preview(self):
        html = Path(__file__).with_name("private-review.html").read_text(encoding="utf-8")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width":390,"height":800})
            page.set_content(html)
            self.assertTrue(page.locator("#borough").is_disabled())
            fixture = {
                "dataset_id":"erm2-nwe9","publication_authorized":False,
                "source_sha256":"a"*64,"rules":{"display_minimum_cell_count":10},
                "aggregates":[{"month":"2026-09","borough":"QUEENS","agency":"DOT",
                "problem":"Pothole","requests":25,"closed_with_valid_interval":12,
                "closure_count_suppressed":False}]
            }
            page.locator("#file").set_input_files({"name":"test.json",
                "mimeType":"application/json","buffer":json.dumps(fixture).encode()})
            self.assertEqual(page.locator("tbody tr").count(),1)
            fixture["aggregates"][0]["closed_with_valid_interval"]=24
            page.locator("#file").set_input_files({"name":"unsafe.json",
                "mimeType":"application/json","buffer":json.dumps(fixture).encode()})
            self.assertEqual(page.locator("tbody tr").count(),0)
            self.assertIn("File rejected",page.locator("#status").inner_text())
            browser.close()

if __name__ == "__main__":unittest.main()
