"""HTTP-served Chromium smoke test for actual module loading and CSP."""
import json
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

@contextmanager
def serve():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)

def main():
    with serve() as url, sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 700}, accept_downloads=True)
        errors = []
        violations = []
        requests = []
        page.add_init_script("document.addEventListener('securitypolicyviolation', e => window.__cspViolation = (window.__cspViolation || 0) + 1)")
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda msg: violations.append(msg.text) if "Content Security Policy" in msg.text else None)
        page.on("request", lambda request: requests.append(request.url))
        response = page.goto(url, wait_until="networkidle")
        assert response.status == 200
        assert page.locator("#sourceId").is_visible()
        page.locator("#sourceId").fill("000123")
        page.locator("#date").fill("2026-10-17")
        page.locator("#claim").fill("Synthetic browser-local record")
        page.get_by_role("button", name="Add record").click()
        assert page.locator("#records li").count() == 1
        page.locator("#review-filter").select_option("disputed")
        assert page.locator("#records li").count() == 0
        page.locator("#review-filter").select_option("all")
        assert page.locator("#records li").count() == 1
        with page.expect_download() as download:
            page.locator("#json").click()
        assert download.value.suggested_filename.endswith(".json")
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert len(exported["records"]) == 1
        assert exported["records"][0]["sourceId"] == "000123"
        assert page.locator("#csv").is_enabled(), "benign source permits CSV"
        page.locator("#sourceId").fill("=1+1")
        page.locator("#date").fill("2026-10-23")
        page.locator("#claim").fill("Synthetic formula-prefix source ID")
        page.get_by_role("button", name="Add record").click()
        assert page.locator("#records li").count() == 2, "unsafe input retained locally"
        assert page.locator("#csv").is_disabled(), "CSV blocked for unsafe source"
        assert "sourceId" in page.locator("#csv-warning").inner_text(), "accessible field warning"
        assert page.locator("#csv-warning").get_attribute("role") == "status"
        assert page.locator("#json").is_enabled(), "lossless JSON remains available"
        with page.expect_download() as download:
            page.locator("#json").click()
        preserved = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert any(r["sourceId"] == "=1+1" for r in preserved["records"]), "exact unsafe source ID preserved in JSON"
        # Removing the risky source must restore safe export without losing the benign record.
        page.get_by_role("button", name="Remove record =1+1").click()
        assert page.locator("#records li").count() == 1
        assert page.locator("#csv").is_enabled(), "CSV recovers after unsafe record removal"
        assert page.locator("#csv-warning").inner_text() == "", "stale security warning cleared"
        assert page.evaluate("document.activeElement.id") == "count", "focus returns to result count"
        with page.expect_download() as download:
            page.locator("#csv").click()
        safe_csv = Path(download.value.path()).read_text(encoding="utf-8-sig")
        assert "000123" in safe_csv, "zero-padded source identifier preserved in recovered CSV"
        assert "=1+1" not in safe_csv, "removed risky record excluded from export"
        assert not errors, errors
        assert not violations, violations
        assert page.evaluate('window.__cspViolation || 0') == 0
        assert all(request.startswith(url.rsplit("/", 1)[0] + "/") for request in requests), requests
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.evaluate("document.documentElement.style.fontSize = '32px'")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => ({tag:e.tagName,id:e.id,right:Math.round(e.getBoundingClientRect().right)}))""")
        browser.close()
    print("PASS: HTTP-served Chromium module/CSP/local-only/filter/fail-closed CSV/JSON/reflow assertions")

if __name__ == "__main__":
    main()
