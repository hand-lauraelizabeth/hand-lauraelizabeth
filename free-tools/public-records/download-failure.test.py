"""FT-09 synthetic HTTP-served download-failure recovery across three browser engines."""
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


class DownloadFailureRecovery(unittest.TestCase):
    def test_blocked_json_csv_and_click_cleanup_then_retry(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        self.assertIn(engine, ("chromium", "firefox", "webkit"))
        synthetic = {
            "version": 1,
            "requests": [{"id": "REQ-0001", "jurisdiction": "federal",
                          "agency": "Synthetic office", "stage": "draft",
                          "submittedOn": "", "agencyTrackingId": "",
                          "description": "Synthetic 漢字 evidence"}],
            "events": []
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
                            "buffer": json.dumps(synthetic, ensure_ascii=False).encode("utf-8")
                        })
                        page.locator("#status").get_by_text("Imported 1 requests", exact=False).wait_for()

                        # A synthetic browser failure must be announced, not thrown.
                        page.evaluate("""() => {
                            window.__ft09Create = URL.createObjectURL;
                            URL.createObjectURL = () => { throw Error('PRIVATE synthetic failure'); };
                        }""")
                        page.locator("#save-json").click()
                        self.assertIn("JSON download could not start", page.locator("#status").inner_text())
                        self.assertNotIn("PRIVATE", page.locator("#status").inner_text())
                        page.locator("#save-csv").click()
                        self.assertIn("CSV download could not start", page.locator("#status").inner_text())
                        page.evaluate("() => { URL.createObjectURL = window.__ft09Create; }")

                        # If a link click fails after URL creation, cleanup is still required.
                        page.evaluate("""() => {
                            window.__ft09Click = HTMLAnchorElement.prototype.click;
                            window.__ft09Revoke = URL.revokeObjectURL;
                            window.__ft09Revoked = [];
                            HTMLAnchorElement.prototype.click = () => { throw Error('PRIVATE synthetic click'); };
                            URL.revokeObjectURL = url => {
                                window.__ft09Revoked.push(url);
                                return window.__ft09Revoke.call(URL, url);
                            };
                        }""")
                        page.locator("#save-json").click()
                        self.assertIn("JSON download could not start", page.locator("#status").inner_text())
                        self.assertEqual(page.locator("a[download]").count(), 0)
                        page.wait_for_timeout(1250)
                        self.assertEqual(page.evaluate("() => window.__ft09Revoked.length"), 1)
                        page.evaluate("""() => {
                            HTMLAnchorElement.prototype.click = window.__ft09Click;
                            URL.revokeObjectURL = window.__ft09Revoke;
                        }""")

                        # DOM creation can fail after a Blob URL exists; revoke immediately.
                        page.evaluate("""() => {
                            window.__ft09CreateElement = document.createElement.bind(document);
                            window.__ft09Revoked = [];
                            window.__ft09Revoke = URL.revokeObjectURL;
                            document.createElement = function(tag, ...args) {
                                if (tag === 'a') throw Error('PRIVATE synthetic DOM failure');
                                return window.__ft09CreateElement(tag, ...args);
                            };
                            URL.revokeObjectURL = url => {
                                window.__ft09Revoked.push(url);
                                return window.__ft09Revoke.call(URL, url);
                            };
                        }""")
                        page.locator("#save-json").click()
                        self.assertIn("JSON download could not start", page.locator("#status").inner_text())
                        self.assertEqual(page.locator("a[download]").count(), 0)
                        self.assertEqual(page.evaluate("() => window.__ft09Revoked.length"), 1)
                        page.evaluate("""() => {
                            document.createElement = window.__ft09CreateElement;
                            URL.revokeObjectURL = window.__ft09Revoke;
                        }""")

                        # A later successful download must contain exact saved evidence.
                        with page.expect_download() as download:
                            page.locator("#save-json").click()
                        recovered = json.loads(download.value.path().read_text(encoding="utf-8"))
                        self.assertEqual(recovered, synthetic)
                        self.assertIn("JSON download started; confirm the file was saved", page.locator("#status").inner_text())
                        self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"),
                                             page.evaluate("innerWidth"))
                        self.assertTrue(all(u.startswith(url.rsplit("/", 1)[0]) for u in outbound))
                    finally:
                        page.close()
            finally:
                browser.close()


if __name__ == "__main__":
    unittest.main()
