"""Synthetic browser regression for editable request metadata and lossless evidence.

Run with FT09_BROWSER=chromium|firefox|webkit. Never uses personal records.
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

class RequestMetadataEdit(unittest.TestCase):
    def test_submission_date_tracking_id_validation_and_evidence(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        original = {
            "version": 1,
            "requests": [
                {"id": "REQ-0007", "jurisdiction": "federal", "agency": "Synthetic agency",
                 "stage": "submitted", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Evidence <img src=x onerror=alert(1)> — 漢字"},
                {"id": "REQ-0008", "jurisdiction": "local", "agency": "Other agency",
                 "stage": "draft", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Untouched record"}
            ],
            "events": [
                {"id": "EV-0002", "requestId": "REQ-0007", "date": "2026-10-11",
                 "kind": "note", "sourceId": " SRC-0003 ", "description": "Original evidence"}
            ]
        }
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    page = browser.new_page(accept_downloads=True, viewport={"width": 320, "height": 800})
                    requests = []
                    page.on("request", lambda req: requests.append(req.url))
                    try:
                        self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                        page.locator("#open-json").set_input_files({
                            "name": "synthetic.json", "mimeType": "application/json",
                            "buffer": json.dumps(original, ensure_ascii=False).encode("utf-8")
                        })
                        page.locator("#status").get_by_text("Imported 2 requests", exact=False).wait_for()
                        def exported():
                            with page.expect_download() as download:
                                page.locator("#save-json").click()
                            return json.loads(download.value.path().read_text(encoding="utf-8"))
                        self.assertEqual(exported(), original)
                        self.assertIn("Submission date not recorded", page.locator("#flags").inner_text())
                        self.assertIn("Agency tracking ID not recorded", page.locator("#flags").inner_text())
                        self.assertEqual(page.locator("img").count(), 0)
                        card = page.locator("#requests .card").first
                        card.locator("input").nth(0).fill("2026-10-12")
                        card.locator("input").nth(1).fill(" 0000-é ")
                        card.locator("button").click()
                        self.assertIn("Updated tracking status or request details", page.locator("#status").inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.getAttribute('aria-label')"),
                                         "Save request changes for request REQ-0007")
                        updated = exported()
                        self.assertEqual(updated["requests"][0]["submittedOn"], "2026-10-12")
                        self.assertEqual(updated["requests"][0]["agencyTrackingId"], " 0000-é ")
                        self.assertEqual(updated["requests"][0]["stage"], "submitted")
                        self.assertEqual(updated["requests"][1], original["requests"][1])
                        self.assertEqual(updated["events"], original["events"])
                        self.assertNotIn("Submission date not recorded", page.locator("#flags").inner_text())
                        self.assertNotIn("Agency tracking ID not recorded", page.locator("#flags").inner_text())
                        card = page.locator("#requests .card").first
                        card.locator("input").nth(0).fill("2026-02-30")
                        card.locator("button").click()
                        self.assertEqual(exported(), updated, "invalid calendar date must not modify evidence")
                        self.assertEqual(card.locator("input").nth(0).get_attribute("aria-invalid"), "true")
                        self.assertIn("real calendar date", card.locator('[role="alert"]').inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.getAttribute('role')"), "alert")
                        card.locator("input").nth(0).fill("")
                        card.locator("input").nth(1).fill("")
                        card.locator("button").click()
                        self.assertEqual(exported(), original)
                        self.assertIn("Submission date not recorded", page.locator("#flags").inner_text())
                        self.assertIn("Agency tracking ID not recorded", page.locator("#flags").inner_text())
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
