"""Synthetic HTTP-served event correction: chronology, exact evidence, error focus, cancellation.

FT09_BROWSER=chromium|firefox|webkit. No real records or external requests.
"""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import unittest
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ft09_http_fixture", HERE / "http-import-crossengine.test.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class EventCorrection(unittest.TestCase):
    def test_correct_event_preserves_ids_evidence_and_focus(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        original = {
            "version": 1,
            "requests": [
                {"id": "REQ-0007", "jurisdiction": "federal", "agency": "Synthetic agency",
                 "stage": "responded", "submittedOn": "2026-10-02",
                 "agencyTrackingId": " 000087 ", "description": "Synthetic request"},
                {"id": "REQ-0008", "jurisdiction": "local", "agency": "Other office",
                 "stage": "draft", "submittedOn": "", "agencyTrackingId": "",
                 "description": "Unrelated request"}
            ],
            "events": [
                {"id": "EV-0002", "requestId": "REQ-0007", "date": "2026-10-20",
                 "kind": "note", "sourceId": " SRC-0003 ", "description": "Original note"},
                {"id": "EV-0001", "requestId": "REQ-0008", "date": "2026-10-10",
                 "kind": "note", "sourceId": "SRC-0001", "description": "Other event"}
            ]
        }
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    page = browser.new_page(accept_downloads=True, viewport={"width": 320, "height": 800})
                    requests = []
                    page.on("request", lambda request: requests.append(request.url))
                    try:
                        self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                        page.locator("#open-json").set_input_files({
                            "name": "synthetic.json", "mimeType": "application/json",
                            "buffer": json.dumps(original, ensure_ascii=False).encode("utf-8")
                        })
                        page.locator("#status").get_by_text("Imported 2 requests and 2 events", exact=False).wait_for()
                        self.assertIn("Response event not recorded", page.locator("#flags").inner_text())
                        self.assertEqual(page.locator("#events li").first.locator("summary").inner_text(),
                                         "Correct event EV-0001")
                        def editor():
                            return page.locator("#events li").filter(
                                has=page.locator("summary", has_text="Correct event EV-0002"))
                        def exported():
                            with page.expect_download() as saved:
                                page.locator("#save-json").click()
                            return json.loads(saved.value.path().read_text(encoding="utf-8"))
                        self.assertEqual(exported(), original)
                        editor().locator("summary").click()
                        editor().locator("input").nth(0).fill("2026-10-01")
                        editor().locator("select").select_option("response")
                        editor().locator("input").nth(1).fill(" SRC-0003-漢字 ")
                        editor().locator("textarea").fill("Corrected <img src=x onerror=alert(1)> — é")
                        editor().get_by_role("button", name="Save event correction").click()
                        self.assertIn("Corrected event EV-0002", page.locator("#status").inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.textContent"),
                                         "Correct event EV-0002")
                        self.assertEqual(page.locator("#events li").first.locator("summary").inner_text(),
                                         "Correct event EV-0002")
                        self.assertNotIn("Response event not recorded", page.locator("#flags").inner_text())
                        self.assertEqual(page.locator("img").count(), 0)
                        updated = exported()
                        self.assertEqual(updated["events"][0]["id"], "EV-0002")
                        self.assertEqual(updated["events"][0]["requestId"], "REQ-0007")
                        self.assertEqual(updated["events"][0]["date"], "2026-10-01")
                        self.assertEqual(updated["events"][0]["kind"], "response")
                        self.assertEqual(updated["events"][0]["sourceId"], " SRC-0003-漢字 ")
                        self.assertEqual(updated["events"][0]["description"],
                                         "Corrected <img src=x onerror=alert(1)> — é")
                        self.assertEqual(updated["events"][1], original["events"][1])
                        self.assertEqual(updated["requests"], original["requests"])
                        editor().locator("summary").click()
                        editor().locator("input").nth(0).fill("2026-02-30")
                        editor().get_by_role("button", name="Save event correction").click()
                        self.assertEqual(page.evaluate("document.activeElement.getAttribute('role')"), "alert")
                        self.assertEqual(editor().locator("input").nth(0).get_attribute("aria-invalid"), "true")
                        self.assertIn("real calendar date", editor().locator('[role="alert"]').inner_text())
                        self.assertEqual(exported(), updated)
                        editor().get_by_role("button", name="Cancel event correction").click()
                        self.assertEqual(page.evaluate("document.activeElement.textContent"),
                                         "Correct event EV-0002")
                        self.assertEqual(exported(), updated)
                        editor().locator("summary").click()
                        editor().locator("textarea").fill("")
                        editor().get_by_role("button", name="Save event correction").click()
                        self.assertEqual(editor().locator("textarea").get_attribute("aria-invalid"), "true")
                        self.assertIn("required", editor().locator('[role="alert"]').inner_text())
                        self.assertEqual(exported(), updated)
                        editor().get_by_role("button", name="Cancel event correction").click()
                        with page.expect_download() as saved:
                            page.locator("#save-csv").click()
                        rows = list(csv.DictReader(io.StringIO(
                            saved.value.path().read_text(encoding="utf-8"), newline=""), strict=True))
                        self.assertEqual([row["eventId"] for row in rows if row["recordType"] == "event"],
                                         ["EV-0002", "EV-0001"])
                        self.assertEqual(next(row for row in rows if row["eventId"] == "EV-0002")["sourceId"],
                                         " SRC-0003-漢字 ")
                        page.evaluate("document.documentElement.style.fontSize='64px'")
                        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"),
                                             page.evaluate("innerWidth"), "400% text reflow")
                        self.assertTrue(all(request.startswith(url.rsplit("/", 1)[0])
                                            for request in requests))
                    finally:
                        page.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
