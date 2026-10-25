"""Exercise the real HTML preflight page over HTTP with enforced CSP.

Synthetic documents only. The browser reads and exports data locally.
"""
import json
import mimetypes
import os
import re
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent
POLICY = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'"
)
mimetypes.add_type("text/javascript", ".mjs")


class LocalOnlyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_args):
        pass


@contextmanager
def served_page():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalOnlyHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def download_text(page, selector):
    with page.expect_download(timeout=5000) as download_info:
        page.locator(selector).click()
    return Path(download_info.value.path()).read_text(encoding="utf-8")


def assert_no_download(page, selector):
    try:
        with page.expect_download(timeout=650):
            page.locator(selector).click()
    except PlaywrightTimeoutError:
        return
    raise AssertionError("Exported findings after the source had changed")


def main():
    engine = os.environ.get("FT10_BROWSER", "chromium")
    checks = 0
    with served_page() as origin, sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 700}, accept_downloads=True)
        page_errors = []
        requests = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        try:
            response = page.goto(origin + "/index.html", wait_until="networkidle")
            assert response.status == 200
            checks += 1
            assert response.headers["content-security-policy"] == POLICY
            checks += 1
            assert page.locator("script[type=module][src='app.mjs']").count() == 1
            checks += 1
            assert page.evaluate("""async () => {
                try { await fetch('/index.html'); return 'allowed'; }
                catch (_error) { return 'blocked'; }
            }""") == "blocked"
            checks += 1

            first = ('<!doctype html><html lang="en"><head><title>First</title></head>'
                     '<body><h1>First</h1><img id="first-unsafe" src="first.png"></body></html>')
            second = ('<!doctype html><html lang="en"><head><title>Second</title></head>'
                      '<body><h1>Second</h1><img id="second-unsafe" src="second.png"></body></html>')
            third = ('<!doctype html><html lang="en"><head><title>Third</title></head>'
                     '<body><h1>Third</h1><img id="third-unsafe" src="third.png"></body></html>')

            page.locator("#source").fill(first)
            page.locator("#analyze").click()
            assert page.locator("#findings li").count() > 0
            checks += 1
            first_json = json.loads(download_text(page, "#download-json"))
            assert any(f["location"] == "img#first-unsafe" for f in first_json["findings"])
            checks += 1

            page.locator("#source").fill(second)
            assert page.locator("#findings li").count() == 0
            checks += 1
            assert "Previous findings cleared" in page.locator("#summary").inner_text()
            checks += 1
            assert_no_download(page, "#download-json")
            checks += 1
            assert_no_download(page, "#download-csv")
            checks += 1
            assert "Analyze HTML first" in page.locator("#status").inner_text()
            checks += 1

            page.locator("#analyze").click()
            second_csv = download_text(page, "#download-csv")
            assert "img#second-unsafe" in second_csv
            checks += 1
            assert "img#first-unsafe" not in second_csv
            checks += 1

            page.locator("#html-file").set_input_files({
                "name": "third.html", "mimeType": "text/html",
                "buffer": third.encode("utf-8")
            })
            expect(page.locator('#source')).to_have_value(re.compile('third-unsafe'), timeout=5000)
            assert page.locator("#findings li").count() == 0
            checks += 1
            assert_no_download(page, "#download-json")
            checks += 1
            page.locator("#analyze").click()
            third_json = json.loads(download_text(page, "#download-json"))
            assert any(f["location"] == "img#third-unsafe" for f in third_json["findings"])
            checks += 1
            assert not any(f["location"] == "img#second-unsafe" for f in third_json["findings"])
            checks += 1

            # Simulate an inconsistent browser File read: the actual ArrayBuffer is
            # shorter than the File.size metadata. This must fail closed.
            page.evaluate("""() => {
                window.__ft10OriginalRead = File.prototype.arrayBuffer;
                File.prototype.arrayBuffer = function() {
                    const original = window.__ft10OriginalRead.call(this);
                    return this.name === 'mismatch.html'
                        ? original.then(buffer => buffer.slice(0, -1)) : original;
                };
            }""")
            try:
                page.locator("#html-file").set_input_files({
                    "name": "mismatch.html", "mimeType": "text/html",
                    "buffer": third.encode("utf-8")
                })
                expect(page.locator("#status")).to_contain_text(
                    "File byte count does not match its declared size.", timeout=5000
                )
                checks += 1
                assert page.locator("#source").input_value() == third
                checks += 1
                assert page.evaluate("document.activeElement.id") == "status"
                checks += 1
                assert page.locator("#findings li").count() == 0
                checks += 1
                assert_no_download(page, "#download-json")
                checks += 1
            finally:
                page.evaluate("""() => {
                    File.prototype.arrayBuffer = window.__ft10OriginalRead;
                    delete window.__ft10OriginalRead;
                }""")

            # NUL can be silently replaced by the HTML parser; empty decoded
            # content (including BOM-only input) must not replace existing HTML.
            for name, payload, expected_error in [
                ("nul.html", b"<h1>\x00</h1>", "NUL character"),
                ("bom-only.html", bytes([0xef, 0xbb, 0xbf]), "no text to analyze"),
                ("whitespace.html", b" \r\n\t ", "no text to analyze"),
            ]:
                page.locator("#html-file").set_input_files({
                    "name": name, "mimeType": "text/html", "buffer": payload
                })
                expect(page.locator("#status")).to_contain_text(expected_error, timeout=5000)
                checks += 1
                assert page.locator("#source").input_value() == third
                checks += 1
                assert page.evaluate("document.activeElement.id") == "status"
                checks += 1
                assert_no_download(page, "#download-json")
                checks += 1

            # A subsequent valid file must recover without stale errors.
            page.locator("#html-file").set_input_files({
                "name": "recovered.html", "mimeType": "text/html",
                "buffer": second.encode("utf-8")
            })
            expect(page.locator("#source")).to_have_value(re.compile("second-unsafe"))
            checks += 1
            assert "HTML loaded locally" in page.locator("#status").inner_text()
            checks += 1
            page.locator("#analyze").click()
            recovered_json = json.loads(download_text(page, "#download-json"))
            assert any(f["location"] == "img#second-unsafe" for f in recovered_json["findings"])
            checks += 1

            # A bidi control in a user-supplied element ID must not enter CSV.
            unsafe = ('<!doctype html><html lang="en"><body>'
                      '<img id="reversed\u202e-name" src="x.png"></body></html>')
            page.locator("#source").fill(unsafe)
            page.locator("#analyze").click()
            unsafe_json = json.loads(download_text(page, "#download-json"))
            assert any("\u202e" in f["location"] for f in unsafe_json["findings"])
            checks += 1
            assert_no_download(page, "#download-csv")
            checks += 1
            assert "CSV export blocked" in page.locator("#status").inner_text()
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1
            # Editing away the unsafe value and reanalyzing restores CSV export.
            page.locator("#source").fill(third)
            page.locator("#analyze").click()
            recovered_csv = download_text(page, "#download-csv")
            assert "img#third-unsafe" in recovered_csv
            checks += 1
            assert "\u202e" not in recovered_csv
            checks += 1

            page.locator("#source").fill(" ")
            page.locator("#analyze").click()
            assert "Cannot analyze" in page.locator("#status").inner_text()
            checks += 1
            assert page.locator("#findings li").count() == 0
            checks += 1
            assert_no_download(page, "#download-json")
            checks += 1
            assert not page_errors, page_errors
            checks += 1
            assert requests and all(url.startswith(origin + "/") for url in requests), requests
            checks += 1
        finally:
            browser.close()
    print(f"PASS: {checks} FT-10 {engine} served HTTP/CSP/module/local-export/stale-source assertions")


if __name__ == "__main__":
    main()
