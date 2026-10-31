"""HTTP-served FT-10 ambiguity regression. Synthetic markup only, no uploads."""
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
    assert engine in ("chromium", "firefox", "webkit")
    checks = 0
    cases = [
        ('<span id="hint">First</span><span id="hint">Second</span><input aria-describedby="hint">',
         {"ambiguous-id-reference"}),
        ('<span id="name">First</span><span id="name">Second</span><button aria-labelledby="name">Action</button>',
         {"ambiguous-id-reference"}),
        ('<span id="hint">First</span><span id="Hint">Second</span><input aria-describedby="hint">',
         set()),
        ('<span id="unused">A</span><span id="unused">B</span><input aria-describedby="hint">',
         {"unresolved-id-reference"}),
        ('<input id="field"><input id="field"><label for="field">Name</label>',
         {"ambiguous-label-target"}),
        ('<input id="field"><label for="field">Name</label>',
         set()),
        ('<table><tr><th id="head">A</th><th id="head">B</th></tr>'
         '<tr><td headers="head">Cell</td></tr></table>',
         {"ambiguous-table-header"}),
        ('<table><tr><th id="head">A</th></tr><tr><td headers="head">Cell</td></tr></table>',
         set()),
        ('<span id="x">One</span><span id="x">Two</span><input aria-labelledby="x x">',
         {"ambiguous-id-reference"}),
        # U+00A0/U+202F are valid characters inside a single exact ID token.
        ('<span id="claim\u00a001">A</span><input aria-describedby="claim\u00a001">',
         set()),
        ('<span id="claim\u00a001">A</span><span id="claim\u00a001">B</span>'
         '<input aria-describedby="claim\u00a001">', {"ambiguous-id-reference"}),
        ('<span id="claim\u202f01">A</span><input aria-labelledby="claim\u202f01">',
         set()),
        ('<table><tr><th id="head\u00a001">A</th><th id="head\u00a001">B</th></tr>'
         '<tr><td headers="head\u00a001">Cell</td></tr></table>',
         {"ambiguous-table-header"}),
        ('<span id="one">A</span><span id="two">B</span>'
         '<input aria-describedby="one\ttwo">', set()),

        # WAI-ARIA 1.2 single-target cardinality and alternate reading order.
        ('<span id="a">A</span><span id="b">B</span>'
         '<input aria-details="a b">', {"single-id-reference"}),
        ('<span id="a">A</span><span id="b">B</span>'
         '<input aria-invalid="true" aria-errormessage="a b">', {"single-id-reference"}),
        ('<span id="a">A</span><span id="b">B</span>'
         '<input aria-describedby="a b">', set()),
        ('<span id="a">A</span><span id="b">B</span>'
         '<input aria-flowto="a b">', set()),
        ('<span id="a">A</span><input aria-flowto="a missing">',
         {"unresolved-id-reference"}),
        ('<span id="a">A</span><span id="a">B</span>'
         '<input aria-flowto="a">', {"ambiguous-id-reference"}),
        ('<span id="a\u00a0b">A</span><input aria-details="a\u00a0b">', set()),
        ('<span id="a\u00a0b">A</span><input aria-flowto="a\u00a0b">', set()),
        # Only one explicit aria-owns owner; do not confuse a repeated token
        # with a second owner or a duplicate target ID.
        ('<span id="target">T</span><div id="a" aria-owns="target"></div>'
         '<div id="b" aria-owns="target"></div>', {"multiple-explicit-owners"}),
        ('<span id="target">T</span><div id="a" aria-owns="target"></div>', set()),
        ('<div id="owner" aria-owns="owner"></div>', {"self-owned-element"}),
        ('<div id="owner" aria-labelledby="owner"></div>', set()),
    ]
    with served() as origin, sync_playwright() as pw:
        browser = getattr(pw, engine).launch(headless=True)
        page = browser.new_page(viewport={"width": 320, "height": 700})
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        try:
            response = page.goto(origin + "/index.html", wait_until="networkidle")
            assert response.status == 200
            assert response.headers["content-security-policy"] == POLICY
            checks += 2
            for markup, expected in cases:
                html = ('<!doctype html><html lang="en"><head><title>Fixture</title></head>'
                        '<body><h1>Fixture</h1>' + markup + '</body></html>')
                page.locator("#source").fill(html)
                page.locator("#analyze").click()
                headings = page.locator("#findings li strong").all_text_contents()
                rules = {heading.split(": ", 1)[1].split(" (", 1)[0]
                         for heading in headings if ": " in heading}
                selected = rules & {"ambiguous-id-reference", "unresolved-id-reference",
                                    "ambiguous-label-target", "ambiguous-table-header",
                                    "single-id-reference", "multiple-explicit-owners",
                                    "self-owned-element"}
                assert selected == expected, (markup, selected, expected)
                assert "preliminary checks" in page.locator("#summary").inner_text()
                checks += 2
            # 320 CSS px is the WCAG 1.4.10 reflow-equivalent viewport.
            # Separately exercise 400% root text scaling at a 1280px viewport;
            # combining both would impose an unintended 16x stress case.
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "320px reflow"
            checks += 1
            page.set_viewport_size({"width": 1280, "height": 800})
            page.evaluate("document.documentElement.style.fontSize='64px'")
            overflow = page.evaluate("""() => ({
                viewport: innerWidth,
                scroll: document.documentElement.scrollWidth,
                elements: [...document.querySelectorAll('body *')]
                    .filter(el => el.getBoundingClientRect().right > innerWidth + 1 ||
                                  el.scrollWidth > el.clientWidth + 1)
                    .slice(0, 10)
                    .map(el => ({tag: el.tagName, id: el.id,
                                 right: Math.round(el.getBoundingClientRect().right),
                                 scroll: el.scrollWidth, client: el.clientWidth}))
            })""")
            assert overflow["scroll"] <= overflow["viewport"], f"400% text scaling: {overflow}"
            checks += 1
            assert not errors, errors
            checks += 1
            assert requests and all(url.startswith(origin + "/") for url in requests), requests
            checks += 1
        finally:
            browser.close()
    print(f"PASS: {checks} FT-10 {engine} HTTP/CSP duplicate reference checks")

if __name__ == "__main__":
    main()
