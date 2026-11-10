"""Synthetic HTTP browser regression: a superseded JSON file read cannot alter newer work.

Run with FT09_BROWSER=chromium|firefox|webkit. All records are fictional.
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

def workspace(request_id):
    return json.dumps({
        "version": 1,
        "requests": [{
            "id": request_id, "jurisdiction": "federal",
            "agency": "Example agency", "stage": "draft",
            "submittedOn": "", "agencyTrackingId": "000007",
            "description": "Synthetic record"
        }],
        "events": []
    }).encode("utf-8")

class ImportRaceReview(unittest.TestCase):
    def test_superseded_valid_and_invalid_reads_never_replace_newer_import(self):
        engine = os.environ.get("FT09_BROWSER", "chromium")
        if engine not in ("chromium", "firefox", "webkit"):
            raise ValueError("Unsupported browser engine")
        with sync_playwright() as pw:
            browser = getattr(pw, engine).launch(headless=True)
            try:
                with fixture.serve() as url:
                    for first_bytes in (
                        workspace("REQ-OLD-0001"),
                        b'{"version":1,"requests":[],"events":[],"\\u0076ersion":1}'
                    ):
                        page = browser.new_page(viewport={"width": 320, "height": 800})
                        try:
                            page.add_init_script("""(() => {
                                const original = File.prototype.arrayBuffer;
                                let release;
                                const gate = new Promise(resolve => { release = resolve; });
                                window.__slowStarted = false;
                                window.__slowFinished = false;
                                window.__releaseSlow = () => release();
                                File.prototype.arrayBuffer = async function() {
                                    if (this.name === 'slow.json') {
                                        window.__slowStarted = true;
                                        await gate;
                                        const result = await original.call(this);
                                        window.__slowFinished = true;
                                        return result;
                                    }
                                    return original.call(this);
                                };
                            })();""")
                            self.assertEqual(page.goto(url, wait_until="networkidle").status, 200)
                            upload = page.locator("#open-json")
                            upload.set_input_files({
                                "name": "slow.json", "mimeType": "application/json",
                                "buffer": first_bytes
                            })
                            page.wait_for_function("window.__slowStarted === true")
                            upload.set_input_files({
                                "name": "fast.json", "mimeType": "application/json",
                                "buffer": workspace("REQ-NEW-0002")
                            })
                            page.locator("#status").get_by_text(
                                "Imported 1 requests", exact=False).wait_for()
                            self.assertIn("REQ-NEW-0002", page.locator("#requests").inner_text())
                            self.assertIsNone(upload.get_attribute("aria-invalid"))
                            page.evaluate("window.__releaseSlow()")
                            page.wait_for_function("window.__slowFinished === true")
                            page.evaluate("() => new Promise(resolve => setTimeout(resolve, 25))")
                            self.assertIn("REQ-NEW-0002", page.locator("#requests").inner_text())
                            self.assertNotIn("REQ-OLD-0001", page.locator("#requests").inner_text())
                            self.assertIn("Imported 1 requests", page.locator("#status").inner_text())
                            self.assertIsNone(upload.get_attribute("aria-invalid"))
                            self.assertEqual(upload.get_attribute("aria-describedby"), "import-help")
                        finally:
                            page.close()
            finally:
                browser.close()

if __name__ == "__main__":
    unittest.main()
