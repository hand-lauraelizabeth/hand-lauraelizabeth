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
        assert not errors, errors
        assert not violations, violations
        assert page.evaluate('window.__cspViolation || 0') == 0
        assert all(request.startswith(url.rsplit("/", 1)[0] + "/") for request in requests), requests
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.evaluate("document.documentElement.style.fontSize = '32px'")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), page.evaluate("""() => [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth + 1).slice(0, 8).map(e => ({tag:e.tagName,id:e.id,right:Math.round(e.getBoundingClientRect().right)}))""")
        browser.close()
    print("PASS: 14 HTTP-served Chromium module/CSP/local-only/filter/export/reflow assertions")

if __name__ == "__main__":
    main()
