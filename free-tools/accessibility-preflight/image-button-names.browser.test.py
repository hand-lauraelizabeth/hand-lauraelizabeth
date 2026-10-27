"""FT-10 HTTP-served image-button/name regression, synthetic HTML only."""
import json
import mimetypes
import os
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
POLICY = ("default-src 'none'; script-src 'self'; style-src 'self'; "
          "connect-src 'none'; img-src 'none'; object-src 'none'; base-uri 'none'")
mimetypes.add_type("text/javascript", ".mjs")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Content-Security-Policy", POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, *_args):
        pass


@contextmanager
def served():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    engine = os.environ.get("FT10_BROWSER", "chromium")
    checks = 0
    with served() as origin, sync_playwright() as playwright:
        browser = getattr(playwright, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 700}, accept_downloads=True)
        errors, requests = [], []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.on("request", lambda request: requests.append(request.url))
        try:
            response = page.goto(origin + "/index.html", wait_until="networkidle")
            assert response.status == 200
            checks += 1
            assert response.headers["content-security-policy"] == POLICY
            checks += 1
            cases = [
                ('<input type="image" src="x.png" alt="Search">', set()),
                ('<input type="image" src="x.png" aria-label="Search">', {"image-button-alt"}),
                ('<input type="image" src="x.png" name="search">', {"image-button-alt"}),
                ('<input type="image" src="x.png" alt="">', {"image-button-alt"}),
                ('<input type="image" src="x.png" alt="  ">', {"image-button-alt"}),
                ('<input type="button">', {"input-button-name"}),
                ('<input type="button" value="Save">', set()),
                ('<input type="button" aria-label="Save">', set()),
                ('<input type="text" placeholder="Search">', {"form-name"}),
                ('<input type="text" title="Search input">', set()),
                ('<input type="reset">', set()),
                ('<input type="submit">', set()),
            ]
            for snippet, expected in cases:
                markup = ('<!doctype html><html lang="en"><head><title>Test</title></head>'
                          '<body><h1>Test</h1><form>' + snippet + '</form></body></html>')
                page.locator("#source").fill(markup)
                page.locator("#analyze").click()
                with page.expect_download() as download:
                    page.locator("#download-json").click()
                data = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
                rules = {finding["rule"] for finding in data["findings"]}
                selected = rules & {"image-button-alt", "input-button-name", "form-name"}
                assert selected == expected, (snippet, selected, expected)
                checks += 1
                assert page.locator("#findings li").count() >= 1
                checks += 1
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            ), "Unexpected horizontal overflow at 320 CSS px"
            checks += 1
            assert not errors, errors
            checks += 1
            assert requests and all(url.startswith(origin + "/") for url in requests), requests
            checks += 1
        finally:
            browser.close()
    print(f"PASS: {checks} FT-10 {engine} synthetic HTTP/CSP image-button naming assertions")


if __name__ == "__main__":
    main()
