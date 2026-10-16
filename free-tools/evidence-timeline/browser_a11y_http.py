"""HTTP-served Chromium checks for the Evidence & Timeline Builder review UI.

Requires: pip install playwright; python -m playwright install chromium
The browser checks do not replace manual screen-reader or native zoom testing.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
thread = Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f"http://127.0.0.1:{server.server_port}/index.html"
checks = 0
try:
    with sync_playwright() as pw:
        opts = {"headless": True, "args": ["--no-sandbox"]}
        if os.environ.get("CHROMIUM_PATH"):
            opts["executable_path"] = os.environ["CHROMIUM_PATH"]
        browser = pw.chromium.launch(**opts)
        page = browser.new_page(viewport={"width": 320, "height": 720}, accept_downloads=True)
        errors, external = [], []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("request", lambda request: external.append(request.url) if not request.url.startswith(f"http://127.0.0.1:{server.server_port}/") else None)
        response = page.goto(url)
        assert response.status == 200; checks += 1
        assert page.locator("#entry-form").count() == 1; checks += 1
        page.locator("#entry-form button").click()
        assert page.locator("#error").is_visible(); checks += 1
        assert page.locator("#sourceId").get_attribute("aria-invalid") == "true"; checks += 1
        assert page.locator("#sourceId").get_attribute("aria-describedby") == "error"; checks += 1
        assert page.evaluate("document.activeElement.id") == "error"; checks += 1
        page.locator("#sourceId").fill("  A  ")
        page.locator("#date").fill("2024-02-29")
        page.locator("#claim").fill("Synthetic source record")
        page.locator("#entry-form button").click()
        assert page.locator("#records li").count() == 1; checks += 1
        assert page.locator("#records h3").inner_text().startswith("  A  "); checks += 1
        assert page.locator("#sourceId").get_attribute("aria-invalid") is None; checks += 1
        assert page.locator("#sourceId").get_attribute("aria-describedby") is None; checks += 1
        page.locator("#sourceId").fill("  A  ")
        page.locator("#date").fill("2024-02-29")
        page.locator("#claim").fill("Duplicate synthetic record")
        page.locator("#entry-form button").click()
        assert page.locator("#error").is_visible(); checks += 1
        assert page.locator("#sourceId").get_attribute("aria-describedby") == "error"; checks += 1
        assert page.locator("#records li").count() == 1; checks += 1
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"); checks += 1
        assert not external; checks += 1
        assert not errors, errors; checks += 1
        browser.close()
finally:
    server.shutdown()
    server.server_close()
print(f"PASS: {checks} HTTP-served Chromium form, exact-ID, focus, reflow, and local-only checks")
