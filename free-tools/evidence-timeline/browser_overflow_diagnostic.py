"""Diagnose viewport overflow in Chromium, Firefox and WebKit without hiding it.

Run: python -m pip install playwright==1.57.0
     python -m playwright install chromium firefox webkit
     python free-tools/evidence-timeline/browser_overflow_diagnostic.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parent
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(root)))
Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_port}/index.html"
failures = []
try:
    with sync_playwright() as pw:
        for engine in ("chromium", "firefox", "webkit"):
            browser = getattr(pw, engine).launch(headless=True)
            try:
                for width in (320, 375, 1280):
                    page = browser.new_page(viewport={"width": width, "height": 720})
                    response = page.goto(url)
                    assert response and response.status == 200
                    report = page.evaluate("""() => ({
                      viewport: innerWidth,
                      documentWidth: document.documentElement.scrollWidth,
                      bodyWidth: document.body.scrollWidth,
                      offenders: [...document.querySelectorAll('*')].map(e => {
                        const r = e.getBoundingClientRect();
                        const s = getComputedStyle(e);
                        return {tag:e.tagName.toLowerCase(), id:e.id, className:typeof e.className==='string'?e.className:'',
                          left:r.left, right:r.right, clientWidth:e.clientWidth, scrollWidth:e.scrollWidth,
                          overflowX:s.overflowX, minWidth:s.minWidth, whiteSpace:s.whiteSpace};
                      }).filter(x => x.right > innerWidth + 0.5 || x.left < -0.5 || x.scrollWidth > x.clientWidth + 1)
                        .sort((a,b) => (b.scrollWidth-b.clientWidth)-(a.scrollWidth-a.clientWidth)).slice(0,20)
                    })""")
                    print(json.dumps({"engine":engine,"width":width,**report},ensure_ascii=False))
                    if report["documentWidth"] > width + 1:
                        failures.append(f"{engine} {width}px document={report['documentWidth']}px")
                    page.close()
            finally:
                browser.close()
finally:
    server.shutdown()
    server.server_close()
assert not failures, "Horizontal overflow: " + "; ".join(failures)
print("PASS: 3 engines x 3 viewports have no horizontal document overflow")
