"""Synthetic, HTTP-served status-edit integrity across browser engines.

Run with FT09_BROWSER=chromium|firefox|webkit. No real records or external requests.
"""
import importlib.util
import json
import os
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ft09_http_fixture", HERE / "http-import-crossengine.test.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)

class RequestStatusEdit(unittest.TestCase):
    def test_status_edit_preserves_exact_records_and_review_flags(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        original = {
            "version": 1,
            "requests": [
                {"id": "REQ-00007", "jurisdiction": "federal", "agency": "Synthetic office",
                 "stage": "draft", "submittedOn": "", "agencyTrackingId": "0000987",
                 "description": "Evidence <svg onload=alert(1)> — é"},
                {"id": "REQ-00008", "jurisdiction": "state", "agency": "Other office",
                 "stage": "unknown", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Second record"}
            ],
            "events": [
                {"id": "EV-00009", "requestId": "REQ-00007", "date": "2026-10-01",
                 "kind": "note", "sourceId": "SRC-00002", "description": "Original evidence"}
            ]
        }
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    page = browser.new_page(accept_downloads=True, viewport={"width": 320, "height": 800})
                    try:
                        requests = []
                        page.on("request", lambda req: requests.append(req.url))
                        self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                        page.locator("#open-json").set_input_files({
                            "name": "synthetic.json", "mimeType": "application/json",
                            "buffer": json.dumps(original, ensure_ascii=False).encode("utf-8")
                        })
                        page.locator("#status").get_by_text("Imported 2 requests and 1 events", exact=False).wait_for()
                        def exported():
                            with page.expect_download() as download:
                                page.locator("#save-json").click()
                            return json.loads(download.value.path().read_text(encoding="utf-8"))
                        self.assertEqual(exported(), original)
                        card = page.locator("#requests .card").first
                        self.assertEqual(card.locator("select").input_value(), "draft")
                        self.assertEqual(page.locator("svg").count(), 0)
                        card.locator("select").select_option("responded")
                        card.locator("button").click()
                        self.assertIn("Updated tracking status", page.locator("#status").inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.getAttribute('aria-label')"),
                                         "Save request changes for request REQ-00007")
                        updated = exported()
                        self.assertEqual(updated["requests"][0]["stage"], "responded")
                        self.assertEqual({k:v for k,v in updated["requests"][0].items() if k != "stage"},
                                         {k:v for k,v in original["requests"][0].items() if k != "stage"})
                        self.assertEqual(updated["requests"][1], original["requests"][1])
                        self.assertEqual(updated["events"], original["events"])
                        self.assertIn("Response event not recorded", page.locator("#flags").inner_text())
                        self.assertEqual(page.locator("#request-select option").last.get_attribute("value"), "REQ-00008")
                        card = page.locator("#requests .card").first
                        card.locator("button").click()
                        self.assertIn("No status change", page.locator("#status").inner_text())
                        self.assertEqual(exported(), updated)
                        card.locator("select").select_option("draft")
                        card.locator("button").click()
                        self.assertEqual(exported(), original)
                        self.assertNotIn("Response event not recorded", page.locator("#flags").inner_text())
                        page.evaluate("document.documentElement.style.fontSize='64px'")
                        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"),
                                             page.evaluate("innerWidth"), "400% root-text scaling reflow")
                        self.assertTrue(all(u.startswith(url.rsplit("/", 1)[0]) for u in requests))
                    finally:
                        page.close()
            finally:
                browser.close()

if __name__ == "__main__":
    unittest.main()
