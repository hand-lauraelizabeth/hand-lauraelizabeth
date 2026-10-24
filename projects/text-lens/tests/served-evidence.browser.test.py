"""Real HTTP/CSP and local evidence-export regression for Text Lens.

Uses only synthetic prose. No external resources, account, or real transcripts.
"""
import base64
import csv
import hashlib
import io
import json
import os
import re
import threading
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "text-lens.html").read_text(encoding="utf-8")
SCRIPTS = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", HTML, re.I | re.S)
assert len(SCRIPTS) == 4, "Review the CSP hash list if inline scripts change"
HASHES = " ".join(
    "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
    for script in SCRIPTS
)
POLICY = (
    "default-src 'none'; script-src 'self' " + HASHES +
    "; style-src 'unsafe-inline'; connect-src 'none'; img-src 'self' data:; "
    "font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
SYNTHETIC = "The library was wonderful. The staff were helpful and kind."


class LocalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_args):
        pass


@contextmanager
def serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def download_bytes(page, selector):
    with page.expect_download(timeout=8000) as info:
        page.locator(selector).click()
    return Path(info.value.path()).read_bytes()


def no_download(page, selector):
    try:
        with page.expect_download(timeout=700):
            page.locator(selector).click()
    except PlaywrightTimeoutError:
        return
    raise AssertionError("Unsafe evidence unexpectedly exported as CSV")


def main():
    engine = os.environ.get("FT11_BROWSER", "chromium")
    checks = 0
    with serve() as origin, sync_playwright() as pw:
        browser = getattr(pw, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 375, "height": 812}, accept_downloads=True)
        requests, errors = [], []
        page.on("request", lambda req: requests.append(req.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            response = page.goto(origin + "/text-lens.html", wait_until="domcontentloaded")
            assert response.status == 200
            checks += 1
            assert response.headers["content-security-policy"] == POLICY
            checks += 1
            expect(page.locator("#status")).to_contain_text("Paste text", timeout=10000)
            checks += 1
            assert page.evaluate("""async () => {
                try { await fetch('/text-lens.html'); return false; }
                catch (_) { return true; }
            }""")
            checks += 1
            expect(page.locator("#cueCsv")).to_be_disabled()
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "=1+1.txt", "mimeType": "text/plain",
                "buffer": SYNTHETIC.encode("utf-8")
            })
            expect(page.locator("#cueCsv")).to_be_enabled(timeout=10000)
            checks += 1
            expect(page.locator("#fileMetaA")).to_contain_text("=1+1.txt")
            checks += 1
            no_download(page, "#cueCsv")
            checks += 1
            expect(page.locator("#status")).to_contain_text("CSV export blocked")
            checks += 1
            assert page.evaluate("document.activeElement.id") == "status"
            checks += 1

            unsafe_json = json.loads(download_bytes(page, "#cueJson").decode("utf-8"))
            assert unsafe_json["export_type"] == "filtered-evidence"
            checks += 1
            assert unsafe_json["rows"] and all(row["source"] == "=1+1.txt" for row in unsafe_json["rows"])
            checks += 1
            assert all(row["passage"] in SYNTHETIC for row in unsafe_json["rows"])
            checks += 1

            page.locator("#fileA").set_input_files({
                "name": "archive.txt", "mimeType": "text/plain",
                "buffer": SYNTHETIC.encode("utf-8")
            })
            expect(page.locator("#fileMetaA")).to_contain_text("archive.txt")
            checks += 1
            expect(page.locator("#cueCsv")).to_be_enabled(timeout=10000)
            checks += 1
            safe_csv = download_bytes(page, "#cueCsv").decode("utf-8-sig")
            table = list(csv.reader(io.StringIO(safe_csv)))
            assert len(table) > 1 and table[0][1] == "source_file"
            checks += 1
            assert all(row[1] == "archive.txt" for row in table[1:])
            checks += 1
            assert all("=1+1.txt" not in row for row in table[1:])
            checks += 1

            page.locator("#a").fill("An unrelated sentence with no evaluative cue.")
            expect(page.locator("#cueCsv")).to_be_disabled(timeout=10000)
            checks += 1
            assert "Manual edits detected" in page.locator("#fileMetaA").inner_text()
            checks += 1
            cleared = json.loads(download_bytes(page, "#cueJson").decode("utf-8"))
            assert cleared["rows"] == []
            checks += 1

            assert not errors, errors
            checks += 1
            assert requests and all(url.startswith(origin + "/") for url in requests), requests
            checks += 1
        finally:
            browser.close()
    print(f"PASS: {checks} FT-11 {engine} HTTP/CSP/unsafe-CSV/exact-JSON/focus/recovery/stale-source checks")


if __name__ == "__main__":
    main()
