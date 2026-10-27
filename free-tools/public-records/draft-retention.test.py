"""Browser-local synthetic regression: unsaved event edits survive unrelated rerenders.

No personal records, external requests, or legal deadline calculations.
Run with FT09_BROWSER=chromium|firefox|webkit.
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


class EventDraftRetention(unittest.TestCase):
    def test_multiple_drafts_preserved_until_explicit_save_or_cancel(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser")
        original = {
            "version": 1,
            "requests": [
                {"id": "REQ-0001", "jurisdiction": "federal", "agency": "Synthetic office",
                 "stage": "draft", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Synthetic records request"},
                {"id": "REQ-0002", "jurisdiction": "local", "agency": "Other synthetic office",
                 "stage": "draft", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Unrelated request"}
            ],
            "events": [
                {"id": "EV-0001", "requestId": "REQ-0001", "date": "2026-10-12",
                 "kind": "note", "sourceId": "SRC-0001", "description": "First original"},
                {"id": "EV-0002", "requestId": "REQ-0002", "date": "2026-10-15",
                 "kind": "note", "sourceId": "SRC-0002", "description": "Second original"}
            ]
        }
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    page = browser.new_page(accept_downloads=True, viewport={"width": 320, "height": 800})
                    outbound = []
                    page.on("request", lambda req: outbound.append(req.url))
                    try:
                        self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                        page.locator("#open-json").set_input_files({
                            "name": "synthetic.json", "mimeType": "application/json",
                            "buffer": json.dumps(original, ensure_ascii=False).encode("utf-8")
                        })
                        page.locator("#status").get_by_text("Imported 2 requests and 2 events", exact=False).wait_for()

                        def editor(event_id):
                            return page.locator(f'#events li[data-event-id="{event_id}"]')

                        def export():
                            with page.expect_download() as saved:
                                page.locator("#save-json").click()
                            return json.loads(saved.value.path().read_text(encoding="utf-8"))

                        first, second = editor("EV-0001"), editor("EV-0002")
                        first.locator("summary").click()
                        first.locator("input").nth(0).fill("2026-10-02")
                        first.locator("input").nth(1).fill(" SRC-0001-漢字 ")
                        first.locator("textarea").fill("Pending correction <img src=x onerror=alert(1)>")
                        second.locator("summary").click()
                        second.locator("textarea").fill("Second pending — é")
                        self.assertEqual(export(), original, "Unsaved edits must not enter evidence exports")

                        request = page.locator("#requests .card").first
                        request.locator("select").select_option("submitted")
                        request.locator("button").click()
                        first, second = editor("EV-0001"), editor("EV-0002")
                        self.assertTrue(first.locator("details").get_attribute("open") is not None)
                        self.assertTrue(second.locator("details").get_attribute("open") is not None)
                        self.assertEqual(first.locator("input").nth(0).input_value(), "2026-10-02")
                        self.assertEqual(first.locator("input").nth(1).input_value(), " SRC-0001-漢字 ")
                        self.assertIn("onerror", first.locator("textarea").input_value())
                        self.assertEqual(second.locator("textarea").input_value(), "Second pending — é")
                        self.assertEqual(page.locator("img").count(), 0)
                        after_request = export()
                        self.assertEqual(after_request["events"], original["events"])
                        self.assertEqual(after_request["requests"][0]["stage"], "submitted")

                        first.get_by_role("button", name="Save event correction").click()
                        first, second = editor("EV-0001"), editor("EV-0002")
                        self.assertIsNone(first.locator("details").get_attribute("open"))
                        self.assertEqual(page.evaluate("document.activeElement.textContent"), "Correct event EV-0001")
                        self.assertIsNotNone(second.locator("details").get_attribute("open"))
                        self.assertEqual(second.locator("textarea").input_value(), "Second pending — é")
                        after_first = export()
                        self.assertEqual(after_first["events"][0]["sourceId"], " SRC-0001-漢字 ")
                        self.assertEqual(after_first["events"][0]["date"], "2026-10-02")
                        self.assertEqual(after_first["events"][1], original["events"][1])

                        second.get_by_role("button", name="Cancel event correction").click()
                        second = editor("EV-0002")
                        self.assertIsNone(second.locator("details").get_attribute("open"))
                        self.assertEqual(export(), after_first)

                        first = editor("EV-0001")
                        first.locator("summary").click()
                        first.locator("input").nth(0).fill("2026-02-30")
                        first.get_by_role("button", name="Save event correction").click()
                        self.assertEqual(first.locator("input").nth(0).get_attribute("aria-invalid"), "true")
                        self.assertIn("real calendar date", first.locator('[role="alert"]').inner_text())
                        page.locator("#requests .card").nth(1).locator("select").select_option("submitted")
                        page.locator("#requests .card").nth(1).locator("button").click()
                        first = editor("EV-0001")
                        self.assertIsNotNone(first.locator("details").get_attribute("open"))
                        self.assertEqual(first.locator("input").nth(0).input_value(), "2026-02-30")
                        self.assertEqual(first.locator("input").nth(0).get_attribute("aria-invalid"), "true")
                        self.assertIn("real calendar date", first.locator('[role="alert"]').inner_text())
                        first.get_by_role("button", name="Cancel event correction").click()
                        self.assertEqual(export()["events"], after_first["events"])
                        page.evaluate("document.documentElement.style.fontSize='64px'")
                        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"),
                                             page.evaluate("innerWidth"), "400% root text reflow")
                        self.assertTrue(all(u.startswith(url.rsplit("/", 1)[0]) for u in outbound))
                    finally:
                        page.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
