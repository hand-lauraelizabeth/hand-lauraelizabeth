"""Synthetic HTTP-served form validation and keyboard recovery for the public-records workspace.

FT09_BROWSER=chromium|firefox|webkit. No personal data or off-origin requests.
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


class FormErrorRecovery(unittest.TestCase):
    def test_duplicate_records_preserve_evidence_and_focus_error(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    page = browser.new_page(accept_downloads=True, viewport={"width": 320, "height": 800})
                    try:
                        requests = []
                        page.on("request", lambda request: requests.append(request.url))
                        self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                        def download():
                            with page.expect_download() as event:
                                page.locator("#save-json").click()
                            return json.loads(event.value.path().read_text(encoding="utf-8"))

                        request_form = page.locator("#request-form")
                        request_id = request_form.locator('input[name="id"]')
                        agency = request_form.locator('input[name="agency"]')
                        description = request_form.locator('textarea[name="description"]')
                        request_id.fill("REQ-00007")
                        agency.fill("Fictional agency")
                        description.fill("Synthetic résumé record")
                        request_form.locator('button[type="submit"]').click()
                        self.assertIn("REQ-00007", page.locator("#requests").inner_text())
                        before = download()

                        request_id.fill("REQ-00007")
                        agency.fill("Fictional agency")
                        description.fill("Second synthetic record")
                        request_form.locator('button[type="submit"]').click()
                        error = page.locator("#request-error")
                        self.assertTrue(error.is_visible())
                        self.assertEqual(error.get_attribute("role"), "alert")
                        self.assertIn("Duplicate request ID", error.inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.id"), "request-error")
                        self.assertEqual(request_id.input_value(), "REQ-00007")
                        self.assertEqual(description.input_value(), "Second synthetic record")
                        self.assertEqual(download(), before, "Rejected request must not alter exact JSON")

                        request_id.fill("REQ-00008")
                        request_form.locator('button[type="submit"]').click()
                        self.assertTrue(error.is_hidden())
                        self.assertIn("REQ-00008", page.locator("#requests").inner_text())

                        event_form = page.locator("#event-form")
                        event_id = event_form.locator('input[name="id"]')
                        event_id.fill("EV-00009")
                        event_form.locator('select[name="requestId"]').select_option("REQ-00007")
                        event_form.locator('input[name="date"]').fill("2026-10-01")
                        event_form.locator('textarea[name="description"]').fill("Synthetic evidence")
                        event_form.locator('button[type="submit"]').click()
                        event_before = download()
                        event_id.fill("EV-00009")
                        event_form.locator('select[name="requestId"]').select_option("REQ-00007")
                        event_form.locator('input[name="date"]').fill("2026-10-02")
                        event_form.locator('textarea[name="description"]').fill("Duplicate synthetic evidence")
                        event_form.locator('button[type="submit"]').click()
                        event_error = page.locator("#event-error")
                        self.assertTrue(event_error.is_visible())
                        self.assertEqual(event_error.get_attribute("role"), "alert")
                        self.assertIn("Duplicate event ID", event_error.inner_text())
                        self.assertEqual(page.evaluate("document.activeElement.id"), "event-error")
                        self.assertEqual(event_id.input_value(), "EV-00009")
                        self.assertEqual(download(), event_before, "Rejected event must not alter exact JSON")
                        event_id.fill("EV-00010")
                        event_form.locator('button[type="submit"]').click()
                        self.assertTrue(event_error.is_hidden())
                        final = download()
                        self.assertEqual([r["id"] for r in final["requests"]], ["REQ-00007", "REQ-00008"])
                        self.assertEqual([e["id"] for e in final["events"]], ["EV-00009", "EV-00010"])
                        self.assertEqual(final["requests"][0]["description"], "Synthetic résumé record")
                        self.assertTrue(all(item.startswith(url.rsplit("/", 1)[0]) for item in requests))
                        page.evaluate("document.documentElement.style.fontSize='64px'")
                        self.assertLessEqual(
                            page.evaluate("document.documentElement.scrollWidth"),
                            page.evaluate("innerWidth"),
                            "320px reflow at 400% root-text scaling")
                    finally:
                        page.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
