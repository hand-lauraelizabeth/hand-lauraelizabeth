"""HTTP-served pending-import status and stale-read isolation; synthetic files only.

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

def workspace(identifier):
    return json.dumps({
        "version": 1,
        "requests": [{"id": identifier, "jurisdiction": "federal",
                      "agency": "Example agency", "stage": "draft",
                      "submittedOn": "", "agencyTrackingId": "000007",
                      "description": "Fictional record"}],
        "events": []
    }).encode("utf-8")

BAD = b'{"version":1,"requests":[],"events":[],"\\u0076ersion":1}'

class PendingImportReview(unittest.TestCase):
    def test_stale_completion_cannot_clear_newer_pending_status(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    for old_data, new_data in (
                        (workspace("REQ-OLD-0001"), workspace("REQ-NEW-0002")),
                        (BAD, workspace("REQ-NEW-0002")),
                        (workspace("REQ-OLD-0001"), BAD),
                    ):
                        with self.subTest(old_invalid=old_data == BAD, new_invalid=new_data == BAD):
                            page = browser.new_page(viewport={"width": 320, "height": 800})
                            try:
                                page.add_init_script("""(() => {
                                  const read = File.prototype.arrayBuffer;
                                  window.__started = {};
                                  window.__finished = {};
                                  window.__release = {};
                                  File.prototype.arrayBuffer = async function() {
                                    const key = this.name;
                                    if (key === 'first.json' || key === 'second.json') {
                                      const gate = new Promise(resolve => { window.__release[key] = resolve; });
                                      window.__started[key] = true;
                                      await gate;
                                      const data = await read.call(this);
                                      window.__finished[key] = true;
                                      return data;
                                    }
                                    return read.call(this);
                                  };
                                })();""")
                                self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                                upload = page.locator("#open-json")
                                status = page.locator("#status")
                                upload.set_input_files({"name": "first.json",
                                    "mimeType": "application/json", "buffer": old_data})
                                page.wait_for_function("window.__started['first.json'] === true")
                                self.assertEqual(upload.get_attribute("aria-busy"), "true")
                                self.assertIn("Reading saved workspace locally", status.inner_text())
                                upload.set_input_files({"name": "second.json",
                                    "mimeType": "application/json", "buffer": new_data})
                                page.wait_for_function("window.__started['second.json'] === true")
                                page.evaluate("window.__release['first.json']()")
                                page.wait_for_function("window.__finished['first.json'] === true")
                                page.wait_for_timeout(75)
                                self.assertEqual(upload.get_attribute("aria-busy"), "true")
                                self.assertIn("Reading saved workspace locally", status.inner_text())
                                self.assertIn("No requests yet", page.locator("#requests").inner_text())
                                self.assertIsNone(upload.get_attribute("aria-invalid"))
                                page.evaluate("window.__release['second.json']()")
                                page.wait_for_function("window.__finished['second.json'] === true")
                                if new_data == BAD:
                                    status.get_by_text("Import rejected", exact=False).wait_for()
                                    self.assertEqual(upload.get_attribute("aria-invalid"), "true")
                                    self.assertEqual(page.evaluate("document.activeElement.id"), "open-json")
                                    self.assertIn("No requests yet", page.locator("#requests").inner_text())
                                else:
                                    status.get_by_text("Imported 1 requests", exact=False).wait_for()
                                    self.assertIn("REQ-NEW-0002", page.locator("#requests").inner_text())
                                    self.assertNotIn("REQ-OLD-0001", page.locator("#requests").inner_text())
                                    self.assertIsNone(upload.get_attribute("aria-invalid"))
                                self.assertEqual(upload.get_attribute("aria-busy"), "false")
                            finally:
                                page.close()
            finally:
                browser.close()

if __name__ == "__main__":
    unittest.main()
